from __future__ import annotations

import argparse
import copy
import concurrent.futures
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import SkillContractError, default_policy, emit, procedure_input_contract, resolve_procedure
from assistant_input_adapter import adapt_assistant_contract
from canonical_input import canonical_input_error, validate_canonical_envelope
from naming_contract import naming_contract, solution_identifier_registry
from normalize_study_spec import engine_field_name
from run_composite import applicable as composite_applicable, run_three_group_pairwise
from run_engine import run_many
from resolution_state import build_resolution_state, make_issue, merge_resolution_state, normalize_issue
from select_procedure import select, select_prepared
from study_spec_v2 import (
    StudySpecContractError,
    build_calculation_result,
    compile_engine_inputs,
    compile_execution_spec,
    phase4_public_view,
    resolve_calculation_request,
    validate_contract_bundle,
)
from v2_native_planning import prepare_v2_native


POLICY = default_policy()
MAX_POWER_SCENARIOS = int(POLICY["scenario_limits"]["power_scenarios"])
MAX_TOTAL_SCENARIOS = int(POLICY["scenario_limits"]["total_calculations"])


def _values(spec: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for container in (
        "defaulted_values", "derived_values", "effect_assumptions", "nuisance_parameters",
        "attrition_assumptions", "user_provided_values",
    ):
        payload = spec.get(container)
        if isinstance(payload, dict):
            values.update(payload)
    values.pop("beta", None)
    values.pop("procedure", None)
    if spec.get("alpha") is not None:
        values["alpha"] = spec["alpha"]
    if spec.get("target_power") is not None and spec.get("calculation_target") != "power":
        values["power"] = spec["target_power"]
    if spec.get("sidedness") is not None:
        sides = spec["sidedness"]
        values["sides"] = 1 if sides == "one_sided" else 2 if sides == "two_sided" else sides
    allocation = spec.get("allocation")
    if isinstance(allocation, (int, float)):
        values["allocation_ratio"] = allocation
    elif isinstance(allocation, dict):
        values.update(allocation)
    if spec.get("requested_public_id") == "TWO-C-009" or (
        spec.get("repeated_measures") and spec.get("effect_measure") == "post_intervention_mean_difference"
    ):
        if values.get("standardized_effect") is not None:
            values.setdefault("planned_mean_difference", values["standardized_effect"])
            values.setdefault("planned_sd", 1.0)
        values.setdefault("pre_measurements", 0)
    return values


def _questions(missing: list[str]) -> list[str]:
    labels = {
        "planned_proportion": "想定割合を指定してください。",
        "analysis_time": "生存確率を評価する時点を指定してください。",
        "accrual_time": "登録期間を指定してください。",
        "followup_time": "最低追跡期間を指定してください。",
        "standard_event_probability": "総被験者数へ変換する場合は、対照群のイベント確率を指定してください。",
        "treatment_event_probability": "総被験者数へ変換する場合は、介入群のイベント確率を指定してください。",
        "planned_intercept_sd": "測定値の標準偏差を指定してください。",
        "direction": "効果の方向を指定してください。",
    }
    return [labels.get(name, f"{name}を指定してください。") for name in missing]


def _expand_grid(values: dict[str, Any], grid: dict[str, Any]) -> list[dict[str, Any]]:
    if not grid:
        return [values]
    keys = list(grid)
    return [
        {**values, **dict(zip(keys, combination))}
        for combination in itertools.product(*(grid[key] for key in keys))
    ]


def _scenario_errors(spec: dict[str, Any], allowed: set[str]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    powers = spec.get("power_scenarios")
    if powers is not None and not isinstance(powers, list):
        errors.append({"code": "INVALID_POWER_SCENARIOS", "message": "power_scenarios must be an array"})
        powers = []
    if isinstance(powers, list):
        if len(powers) > MAX_POWER_SCENARIOS:
            errors.append({
                "code": "SCENARIO_LIMIT_EXCEEDED",
                "message": f"at most {MAX_POWER_SCENARIOS} power scenarios are allowed",
            })
        if any(
            not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(float(value)) or not 0 < float(value) < 1
            for value in powers
        ):
            errors.append({"code": "INVALID_POWER_SCENARIOS", "message": "each power must be finite and strictly between 0 and 1"})
        if len(set(powers)) != len(powers):
            errors.append({"code": "DUPLICATE_POWER_SCENARIOS", "message": "power_scenarios must not contain duplicates"})

    grid = spec.get("calculation_grid") or {}
    grid_count = 1
    if not isinstance(grid, dict):
        errors.append({"code": "INVALID_CALCULATION_GRID", "message": "calculation_grid must be an object"})
        grid = {}
    for key, entries in grid.items():
        if key not in allowed:
            errors.append({"code": "UNKNOWN_GRID_INPUT", "message": f"{key} is not accepted by the selected procedure"})
        if not isinstance(entries, list) or not entries:
            errors.append({"code": "INVALID_CALCULATION_GRID", "message": f"{key} must contain a non-empty array"})
            continue
        if any(isinstance(value, float) and not math.isfinite(value) for value in entries):
            errors.append({"code": "INVALID_CALCULATION_GRID", "message": f"{key} contains a non-finite value"})
        grid_count *= len(entries)
    power_count = len(powers) if isinstance(powers, list) and powers and "power" in allowed else 1
    if grid_count * power_count > MAX_TOTAL_SCENARIOS:
        errors.append({
            "code": "SCENARIO_LIMIT_EXCEEDED",
            "message": f"at most {MAX_TOTAL_SCENARIOS} total calculation scenarios are allowed",
            "requested_scenarios": grid_count * power_count,
        })
    return errors


def _matches_contract_type(value: Any, data_type: str) -> bool:
    if data_type == "any":
        return True
    if data_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))
    if data_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if data_type == "boolean":
        return isinstance(value, bool)
    if data_type == "string":
        return isinstance(value, str)
    if data_type == "array":
        return isinstance(value, list)
    if data_type == "object":
        return isinstance(value, dict)
    return True


def _input_contract_errors(values: dict[str, Any], contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for contract in contracts:
        name = str(contract["name"])
        if name not in values or values[name] is None:
            continue
        value = values[name]
        data_type = str(contract.get("data_type") or "any")
        if not _matches_contract_type(value, data_type):
            errors.append({
                "code": "INPUT_TYPE_INVALID", "path": f"/values/{name}",
                "reason": f"{name} must be {data_type}.", "expected_type": data_type,
                "candidate_values": [],
            })
            continue
        allowed_range = contract.get("allowed_range") or {}
        if "enum" in allowed_range and value not in allowed_range["enum"]:
            errors.append({
                "code": "INPUT_VALUE_NOT_ALLOWED", "path": f"/values/{name}",
                "reason": f"{name} is outside the allowed values.", "expected_type": data_type,
                "candidate_values": copy.deepcopy(allowed_range["enum"]),
            })
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            checks = (
                ("minimum_exclusive", lambda bound: value > bound),
                ("minimum_inclusive", lambda bound: value >= bound),
                ("maximum_exclusive", lambda bound: value < bound),
                ("maximum_inclusive", lambda bound: value <= bound),
            )
            failed = [key for key, check in checks if key in allowed_range and not check(allowed_range[key])]
            if failed:
                errors.append({
                    "code": "INPUT_RANGE_INVALID", "path": f"/values/{name}",
                    "reason": f"{name} is outside the allowed range.", "expected_type": data_type,
                    "candidate_values": [], "allowed_range": copy.deepcopy(allowed_range),
                })
    return errors


def _plan_normalized(normalized: dict[str, Any], *, execute: bool = False,
                     output_mode: str = "concise", recompute_hash: bool = True,
                     contract_bundle: dict[str, Any] | None = None,
                     selection_prepared: bool = False) -> dict[str, Any]:
    defaults = copy.deepcopy(normalized.get("defaults_applied", []))
    if composite_applicable(normalized):
        values = _values(normalized)
        required = ["standardized_effect", "post_measurements", "correlation", "allocation_ratio"]
        missing = [name for name in required if values.get(name) is None]
        if normalized.get("alpha") is None:
            missing.append("familywise_alpha")
        if normalized.get("target_power") is None:
            missing.append("power")
        if missing or not execute:
            return {
                "status": "READY" if not missing else "NEEDS_CLARIFICATION",
                "composition_rule_id": "THREE_GROUP_ALL_PAIRWISE_REPEATED_BONFERRONI",
                "missing_calculation_inputs": missing,
                "questions": _questions(missing),
                "defaults_applied": defaults,
            }
        result = run_three_group_pairwise(
            values, familywise_alpha=normalized["alpha"], power=normalized["target_power"],
            output_mode=output_mode, recompute_hash=recompute_hash,
        )
        return {
            "status": result["status"], "study_spec": normalized,
            "calculation": result, "defaults_applied": defaults,
        }

    selection = select_prepared(normalized) if selection_prepared else select(normalized)
    if selection["status"] != "SELECTED":
        result = {
            "status": selection["status"], "study_spec": normalized,
            "selection": selection, "questions": selection.get("clarification_questions", []),
            "missing_calculation_inputs": selection.get("common_missing_calculation_inputs", []),
            "reason_codes": selection.get("reason_codes", []),
            "defaults_applied": defaults,
        }
        if selection["status"] == "UNSUPPORTED":
            reason_codes = selection.get("reason_codes") or ["NO_VALIDATED_PROCEDURE"]
            unsupported_reason = selection.get("unsupported_reason") or "No validated public procedure is available."
            result.update({
                "reason_codes": reason_codes,
                "questions": [],
                "error": {
                    "code": reason_codes[0],
                    "message": unsupported_reason,
                },
                "unsupported_reason": unsupported_reason,
                "missing_capability": selection.get("missing_capability", []),
                "closest_related_procedures": selection.get("closest_related_procedures", []),
            })
        return result
    target = normalized.get("calculation_target", "required_sample_size")
    item = resolve_procedure(selection["selected_procedure_key"])
    calculator_id = normalized.get("calculator_id")
    calculator = (
        solution_identifier_registry().get("calculators_by_id", {}).get(str(calculator_id))
        if calculator_id else None
    )
    if calculator is not None and not calculator.get("bundled_skill_available"):
        output = naming_contract().get("requested_outputs", {}).get(
            str(calculator.get("requested_output") or normalized.get("requested_output")), {}
        )
        error = {
            "code": "CALCULATOR_UNAVAILABLE",
            "message": "calculator is registered but unavailable in the bundled engine",
            "calculator_id": calculator_id,
            "requested_output": calculator.get("requested_output"),
            "required_engine_version": output.get("available_engine_version"),
        }
        return {
            "status": "UNSUPPORTED", "study_spec": normalized, "selection": selection,
            "error": {key: value for key, value in error.items() if value is not None},
            "reason_codes": ["CALCULATOR_UNAVAILABLE"], "questions": [],
            "defaults_applied": defaults,
        }
    try:
        contract = procedure_input_contract(item, target)
    except SkillContractError as exc:
        return {
            "status": "UNSUPPORTED", "study_spec": normalized, "selection": selection,
            "error": exc.payload, "questions": [], "defaults_applied": defaults,
        }
    allowed = {x["name"] for x in contract["input_contracts"]}
    bound_request = None
    if contract_bundle is not None:
        bound_request = resolve_calculation_request(
            contract_bundle["calculation_request"], selection,
            contract_bundle.get("_selection_constraints"),
        )
        all_values = compile_engine_inputs(contract_bundle["study_spec"], bound_request)
    else:
        all_values = _values(normalized)
    values = {key: value for key, value in all_values.items() if key in allowed}
    # A two-sided longitudinal detectable-effect result is a magnitude, so the
    # sign is immaterial. Keep the validated engine interface unchanged by
    # supplying a positive direction only at execution time.
    if (
        target == "detectable_effect"
        and str(selection.get("engine_id") or "").split(".", 1)[0]
        in {"TWO-031", "TWO-032", "TWO-033"}
        and values.get("sides") == 2
        and values.get("direction") is None
    ):
        values["direction"] = "higher"
        defaults.append({
            "field": "direction",
            "value": "higher",
            "rule": "two-sided detectable effect is reported as a positive magnitude",
            "scope": "execution_only",
        })
    value_validation_errors = _input_contract_errors(values, contract["input_contracts"])
    if value_validation_errors:
        return {
            "status": "NEEDS_CLARIFICATION", "study_spec": normalized, "selection": selection,
            "value_validation_errors": value_validation_errors,
            "reason_codes": list(dict.fromkeys(error["code"] for error in value_validation_errors)),
            "questions": [error["reason"] for error in value_validation_errors],
            "defaults_applied": defaults,
        }
    derived_sources = {
        mapping.get("source") for mapping in normalized.get("derived_input_mappings", [])
        if isinstance(mapping, dict)
    }
    nonengine_context = {
        key: value for key, value in all_values.items()
        if key not in allowed and key not in derived_sources
    }
    if nonengine_context:
        selection["nonengine_context"] = {
            "values": nonengine_context,
            "reason": "retained for study context but not consumed by the selected validated engine contract",
        }
    confirmations = set(item.get("explicit_confirmation_inputs", [])) & allowed
    if target in {"power", "detectable_effect"}:
        confirmations -= {"power", "allocation_ratio", "control_to_treatment_ratio"}
    required = set(contract["required_inputs"]) | confirmations
    missing = sorted(name for name in required if values.get(name) is None)
    unresolved = {
        engine_field_name(name)
        for key in ("missing_required_fields", "uncertain_fields")
        for name in (normalized.get(key) or [])
    } & required
    unresolved_inputs = sorted(unresolved)
    selection["missing_calculation_inputs"] = missing
    if missing or unresolved_inputs:
        questions = _questions(list(dict.fromkeys([*missing, *unresolved_inputs])))
        return {
            "status": "NEEDS_CLARIFICATION", "study_spec": normalized, "selection": selection,
            "missing_calculation_inputs": missing,
            "unresolved_calculation_inputs": unresolved_inputs,
            "questions": questions,
            "defaults_applied": defaults,
        }
    scenario_errors = _scenario_errors(normalized, allowed)
    if scenario_errors:
        return {
            "status": "NEEDS_CLARIFICATION", "study_spec": normalized, "selection": selection,
            "reason_codes": list(dict.fromkeys(error["code"] for error in scenario_errors)),
            "scenario_errors": scenario_errors,
            "questions": [error["message"] for error in scenario_errors],
            "defaults_applied": defaults,
        }
    if not execute:
        return {
            "status": "READY", "study_spec": normalized, "selection": selection,
            "engine_inputs": values, "defaults_applied": defaults,
        }

    powers = [None] if target in {"power", "detectable_effect"} else (
        normalized.get("power_scenarios") or ([values["power"]] if "power" in values else [None])
    )
    scenarios = []
    for grid_values in _expand_grid(values, normalized.get("calculation_grid") or {}):
        for power in powers:
            scenario = dict(grid_values)
            if power is not None and "power" in allowed:
                scenario["power"] = power
            scenarios.append(scenario)
    execution_spec = None
    execution_procedure_key = item["procedure_key"]
    execution_target = target
    execution_scenarios = scenarios
    if contract_bundle is not None:
        bound_request = bound_request or resolve_calculation_request(
            contract_bundle["calculation_request"], selection,
            contract_bundle.get("_selection_constraints"),
        )
        execution_spec = compile_execution_spec(
            contract_bundle["study_spec"], bound_request,
            engine_inputs=scenarios[0], scenarios=scenarios,
        )
        execution_procedure_key = execution_spec["procedure_key"]
        execution_target = execution_spec["engine_calculation_target"]
        execution_scenarios = execution_spec["scenarios"]
    calculations = run_many(
        execution_procedure_key, execution_scenarios, calculation_target=execution_target,
        output_mode=output_mode, recompute_hash=recompute_hash,
        defaults_applied=defaults,
    )
    statuses = {x.get("status") for x in calculations}
    overall_status = (
        "CALCULATED" if statuses == {"CALCULATED"}
        else "NEEDS_CLARIFICATION" if "NEEDS_CLARIFICATION" in statuses and statuses <= {"CALCULATED", "NEEDS_CLARIFICATION"}
        else "ERROR"
    )
    return {
        "status": overall_status,
        "study_spec": normalized, "selection": selection, "defaults_applied": defaults,
        "calculations": calculations,
        "questions": [
            question for calculation in calculations
            for question in calculation.get("questions", [])
        ],
        "nonengine_context": selection.get("nonengine_context"),
        "_execution_spec": execution_spec,
        "result_table": [
            {
                "power": (x.get("structured_inputs") or {}).get("power"),
                "beta": None if (x.get("structured_inputs") or {}).get("power") is None else 1 - x["structured_inputs"]["power"],
                "input_grid": {
                    key: x["structured_inputs"].get(key)
                    for key in (normalized.get("calculation_grid") or {})
                },
                "final_value": (x.get("final_result") or {}).get("value"),
                "quantity": (x.get("final_result") or {}).get("quantity"),
            }
            for x in calculations
        ],
    }


def _phase4_output(
    legacy_result: dict[str, Any], bundle: dict[str, Any],
) -> dict[str, Any]:
    """Attach the canonical Phase 4 contract without changing legacy calculation values."""
    result = dict(legacy_result)
    execution_spec = result.pop("_execution_spec", None)
    resolved_request = resolve_calculation_request(
        bundle["calculation_request"], result.get("selection"),
        bundle.get("_selection_constraints"),
    )
    resolved_bundle = dict(bundle)
    if resolved_request:
        resolved_bundle["resolved_calculation_request"] = resolved_request
    issues = list((bundle.get("resolution_state") or {}).get("issues") or [])
    for name in result.get("missing_calculation_inputs") or []:
        issues.append(make_issue(
            code="REQUIRED_INPUT_MISSING", path=f"/values/{name}",
            reason=f"The selected calculator requires {name}.", blocking=True,
            expected_type=None, candidate_values=[], category="missing",
        ))
    for name in result.get("unresolved_calculation_inputs") or []:
        issues.append(make_issue(
            code="INPUT_UNCERTAIN", path=f"/values/{name}",
            reason=f"{name} must be resolved before execution.", blocking=True,
            expected_type=None, candidate_values=[], category="uncertain",
        ))
    for error in result.get("scenario_errors") or []:
        issues.append(make_issue(
            code=str(error.get("code") or "SCENARIO_INVALID"),
            path="/calculation_request/calculation_grid",
            reason=str(error.get("message") or "Scenario request is invalid."),
            blocking=True, expected_type="object", candidate_values=[],
            category="conflict", details=error,
        ))
    for error in result.get("value_validation_errors") or []:
        issues.append(make_issue(
            code=str(error.get("code") or "INPUT_VALUE_INVALID"),
            path=str(error.get("path") or "/values/unknown"),
            reason=str(error.get("reason") or "Study value is invalid."),
            blocking=True, expected_type=error.get("expected_type"),
            candidate_values=error.get("candidate_values") or [],
            category="conflict", details={
                key: copy.deepcopy(value) for key, value in error.items()
                if key not in {"code", "path", "reason", "expected_type", "candidate_values"}
            },
        ))
    selection = result.get("selection") or {}
    if (
        result.get("status") == "NEEDS_CLARIFICATION"
        and selection.get("status") != "SELECTED"
        and "INPUT_CONFLICT" not in (selection.get("reason_codes") or [])
    ):
        questions = result.get("questions") or selection.get("clarification_questions") or []
        differing = selection.get("differing_fields") or []
        issue_path = f"/study/{differing[0]}" if differing else "/study"
        issues.append(make_issue(
            code=str((result.get("reason_codes") or selection.get("reason_codes") or ["STUDY_INTENT_AMBIGUOUS"])[0]),
            path=issue_path,
            reason=str(questions[0] if questions else "Study intent requires clarification."),
            blocking=True, expected_type="unambiguous research design",
            candidate_values=selection.get("candidate_procedures") or [],
            category="uncertain",
        ))
    if result.get("status") == "UNSUPPORTED":
        error = result.get("error") or {}
        issues.append(make_issue(
            code=str(error.get("code") or "NO_VALIDATED_PROCEDURE"),
            path="/calculation_request/requested_output",
            reason=str(result.get("unsupported_reason") or error.get("message") or "No supported calculator is available."),
            blocking=True, expected_type="supported calculation intent",
            candidate_values=result.get("closest_related_procedures") or [],
            category="unsupported",
        ))
    resolved_bundle["resolution_state"] = build_resolution_state(
        issues, unsupported=result.get("status") == "UNSUPPORTED",
    )
    public_contract = phase4_public_view(resolved_bundle)
    calculations = result.get("calculations") or []
    scenarios = [
        dict(row.get("structured_inputs") or {}) for row in calculations
        if row.get("structured_inputs") is not None
    ]
    engine_inputs = result.get("engine_inputs")
    if not scenarios and isinstance(engine_inputs, dict):
        scenarios = [dict(engine_inputs)]
    if execution_spec is None and scenarios and resolved_request.get("procedure_key") and resolved_request.get("engine_procedure_id"):
        try:
            execution_spec = compile_execution_spec(
                bundle["study_spec"], resolved_request,
                engine_inputs=scenarios[0], scenarios=scenarios,
            )
        except StudySpecContractError as exc:
            result.setdefault("contract_errors", []).append(exc.payload)

    contract_validation = validate_contract_bundle(resolved_bundle, execution_spec)
    canonical: dict[str, Any] = {
        "contract_version": bundle["contract_version"],
        "study_spec_v2": public_contract["study_spec"],
        "calculation_request": public_contract["calculation_request"],
        "resolution_state": public_contract["resolution_state"],
        "interaction_context": public_contract["interaction_context"],
        "contract_validation": contract_validation,
    }
    if public_contract.get("resolved_calculation_request"):
        canonical["resolved_calculation_request"] = public_contract["resolved_calculation_request"]
    if execution_spec is not None:
        canonical["execution_spec"] = execution_spec
    if execution_spec is not None and calculations:
        canonical["calculation_result"] = build_calculation_result(
            execution_spec, calculations, status=str(result.get("status")),
        )
    canonical["study_spec"] = canonical.pop("study_spec_v2")
    canonical.update({
        "status": result.get("status"),
        "questions": result.get("questions", []),
        "reason_codes": result.get("reason_codes", []),
        "error": result.get("error"),
        "unsupported_reason": result.get("unsupported_reason"),
        "missing_capability": result.get("missing_capability", []),
        "closest_related_procedures": result.get("closest_related_procedures", []),
        "defaults_applied": result.get("defaults_applied", []),
        "nonengine_context": result.get("nonengine_context"),
        "result_table": result.get("result_table", []),
    })
    if result.get("calculation") is not None:
        canonical["composition_calculation"] = result["calculation"]
    return {key: value for key, value in canonical.items() if value is not None}


def plan(spec: dict[str, Any], *, execute: bool = False,
         output_mode: str = "concise", recompute_hash: bool = True) -> dict[str, Any]:
    """Plan one canonical StudySpec v2 request and emit canonical output only."""
    input_issues = validate_canonical_envelope(spec)
    if input_issues:
        return canonical_input_error(input_issues)
    if "calculation_requests" in spec:
        return plan_calculation_requests(
            spec, execute=execute, output_mode=output_mode,
            recompute_hash=recompute_hash,
        )
    request = spec["calculation_request"]
    selection_constraints = copy.deepcopy(spec.get("calculator_selection_constraint") or {})
    native_study, native_request, native_resolution, native_interaction, normalized_input, native_trace = prepare_v2_native(
        spec["study_spec"], request, spec.get("interaction_context"),
        spec.get("resolution_state"), selection_constraints,
    )
    bundle = {
        "contract_version": "1.0.0",
        "study_spec": native_study,
        "calculation_request": native_request,
        "resolution_state": native_resolution,
        "interaction_context": native_interaction,
        "_selection_constraints": selection_constraints,
        "_planning_view": normalized_input,
        "_native_planning_trace": native_trace,
    }
    bundle["interaction_context"].setdefault("presentation", {})["output_detail"] = output_mode
    bundle["interaction_context"].setdefault("conversation", {})
    bundle["interaction_context"].setdefault("compatibility", {
        "source_schema": "StudySpec-v2",
    })
    legacy_result = _plan_normalized(
        normalized_input, execute=execute, output_mode=output_mode,
        recompute_hash=recompute_hash, contract_bundle=bundle,
        selection_prepared=True,
    )
    return _phase4_output(legacy_result, bundle)


def plan_calculation_requests(
    spec: dict[str, Any], *, execute: bool = False,
    output_mode: str = "concise", recompute_hash: bool = True,
) -> dict[str, Any]:
    """Execute ordered independent requests against one reusable StudySpec."""
    study = spec.get("study_spec")
    requests = spec.get("calculation_requests")
    if not isinstance(study, dict) or not isinstance(requests, list) or not requests:
        return {
            "schema_version": "2.0.0", "status": "INVALID_REQUESTS",
            "errors": [{"code": "BATCH_CONTRACT_INVALID"}],
        }
    prepared_requests = []
    identifiers = []
    for index, request in enumerate(requests, start=1):
        if not isinstance(request, dict):
            return {
                "schema_version": "2.0.0", "status": "INVALID_REQUESTS",
                "errors": [{"code": "CALCULATION_REQUEST_NOT_OBJECT", "index": index - 1}],
            }
        prepared = copy.deepcopy(request)
        prepared.setdefault("schema_version", "2.0.0")
        prepared.setdefault("request_id", f"request-{index:03d}")
        prepared_requests.append(prepared)
        identifiers.append(str(prepared["request_id"]))
    if len(set(identifiers)) != len(identifiers):
        return {
            "schema_version": "2.0.0", "status": "INVALID_REQUESTS",
            "errors": [{"code": "DUPLICATE_REQUEST_ID"}],
        }

    execution_policy = spec.get("execution_policy") or {}
    parallelism = execution_policy.get("parallelism", 1) if isinstance(execution_policy, dict) else None
    if not isinstance(parallelism, int) or isinstance(parallelism, bool) or not 1 <= parallelism <= 8:
        return {
            "schema_version": "2.0.0", "status": "INVALID_REQUESTS",
            "errors": [{"code": "INVALID_PARALLELISM", "allowed_range": [1, 8]}],
        }

    request_results = []
    canonical_study = None
    interaction = spec.get("interaction_context") or {
        "schema_version": "2.0.0", "presentation": {}, "conversation": {},
        "compatibility": {"source_schema": "StudySpec-v2"},
    }
    def plan_one(request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        single = plan(
            {
                "study_spec": study,
                "calculation_request": request,
                "interaction_context": interaction,
            },
            execute=execute, output_mode=output_mode,
            recompute_hash=recompute_hash,
        )
        entry = {
            "request_id": request["request_id"],
            "status": single.get("status"),
            "calculation_request": single.get("calculation_request"),
            "resolved_calculation_request": single.get("resolved_calculation_request"),
            "resolution_state": single.get("resolution_state"),
            "procedure_selection": single.get("procedure_selection") or single.get("selection"),
            "execution_spec": single.get("execution_spec"),
            "calculation_result": single.get("calculation_result"),
            "questions": single.get("questions", []),
            "reason_codes": single.get("reason_codes", []),
            "error": single.get("error"),
            "unsupported_reason": single.get("unsupported_reason"),
            "missing_capability": single.get("missing_capability", []),
            "closest_related_procedures": single.get("closest_related_procedures", []),
        }
        return ({key: value for key, value in entry.items() if value is not None},
                single.get("study_spec"))

    if parallelism == 1 or len(prepared_requests) == 1:
        planned = [plan_one(request) for request in prepared_requests]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(parallelism, len(prepared_requests))) as executor:
            planned = list(executor.map(plan_one, prepared_requests))
    for entry, planned_study in planned:
        canonical_study = canonical_study or planned_study
        request_results.append(entry)
    statuses = {entry["status"] for entry in request_results}
    overall = (
        "CALCULATED" if statuses == {"CALCULATED"}
        else "READY" if statuses == {"READY"}
        else "PARTIAL"
    )
    result = {
        "schema_version": "2.0.0",
        "status": overall,
        "study_spec": canonical_study,
        "interaction_context": interaction,
        "request_results": request_results,
        "request_count": len(request_results),
        "engine_call_count": len(request_results) if execute else 0,
        "execution_policy": {"parallelism": parallelism, "result_order": "request_order"},
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-spec", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-mode", default="concise", choices=["concise", "detailed", "qc"])
    parser.add_argument("--skip-hash-recompute", action="store_true")
    args = parser.parse_args()
    spec = adapt_assistant_contract(json.loads(args.study_spec.read_text(encoding="utf-8-sig")))
    emit(plan(spec, execute=args.execute, output_mode=args.output_mode,
              recompute_hash=not args.skip_hash_recompute))


if __name__ == "__main__":
    main()
