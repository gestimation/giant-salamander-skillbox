from __future__ import annotations

import copy
from typing import Any

from _common import default_policy
from validate_study_spec import _normalized_mode
from naming_contract import naming_contract, solution_identifier_registry
from resolution_state import (
    build_resolution_state, issues_from_legacy, legacy_unresolved_lists,
    normalize_issue,
)
from study_contract import canonical_study_output_fields
from study_field_validation import normalize_study_spec_fields, validate_study_spec_fields
from study_spec_v2 import SCHEMA_VERSION, StudySpecContractError


SERVICE_ID = "StudySpec-v2.native-planning.6-4"
POLICY = default_policy()
POWER_VALUES = list(POLICY["defaults"]["power_values"])
DEFAULT_ALPHA = float(POLICY["defaults"]["alpha"])
DEFAULT_ALLOCATION = float(POLICY["defaults"]["two_group_allocation_ratio"])
EXCEPTION_TOKENS = tuple(POLICY["exceptions"]["objective_tokens"])
SPECIAL_VALUE_FIELDS = {"alpha", "target_power", "sidedness", "allocation"}
SELECTION_CONTEXT_VALUE_FIELDS = {
    "confidence_level", "margin", "censoring_probability",
    "standard_censoring_probability", "treatment_censoring_probability",
}
DEFAULT_TARGETS = {
    "alpha": "alpha", "power": "target_power", "sides": "sidedness",
    "allocation_ratio": "allocation", "procedure": "catalog_procedure_id",
    "confidence_interval_method": "confidence_interval_method",
    "width_definition": "width_definition",
}


def _token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _source(study_spec: dict[str, Any], name: str) -> str:
    pointer = f"/values/{_token(name)}"
    return str(((study_spec.get("provenance") or {}).get(pointer) or {}).get("source") or "imported_legacy")


def _record(state: dict[str, Any], field: str, value: Any, rule: str) -> None:
    if field in state.setdefault("defaulted_values", {}):
        return
    state["defaulted_values"][field] = copy.deepcopy(value)
    state.setdefault("defaults_applied", []).append({
        "field": field, "value": copy.deepcopy(value), "rule": rule,
    })
    state.setdefault("value_sources", {})[DEFAULT_TARGETS.get(field, field)] = "policy_default"


def _record_derived(state: dict[str, Any], field: str, value: Any, rule: str) -> None:
    if field in state.setdefault("derived_values", {}):
        return
    state["derived_values"][field] = copy.deepcopy(value)
    state.setdefault("value_sources", {})[field] = "derived"
    state.setdefault("defaults_applied", []).append({
        "field": field, "value": copy.deepcopy(value), "rule": rule,
        "source": "derived",
    })


def _record_study_default(state: dict[str, Any], field: str, value: Any, rule: str) -> None:
    if state.get(field) is not None:
        return
    state[field] = copy.deepcopy(value)
    state.setdefault("defaults_applied", []).append({
        "field": field, "value": copy.deepcopy(value), "rule": rule,
        "source": "policy_default",
    })


def _requested_output_policy(requested_output: str, calculator_id: str | None) -> tuple[str, str]:
    output = naming_contract().get("requested_outputs", {}).get(requested_output)
    if output is None:
        raise StudySpecContractError(
            "UNKNOWN_REQUESTED_OUTPUT", "requested_output is not registered",
            requested_output=requested_output,
        )
    operation = output.get("engine_operation")
    if operation == "procedure_specific":
        operation = output.get("default_engine_operation")
        if calculator_id:
            record = solution_identifier_registry().get("calculators_by_id", {}).get(calculator_id, {})
            operation = record.get("legacy_catalog_operation", operation)
    return str(operation), str(output["engine_calculation_target"])


def _validate_calculator_constraint(constraints: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(constraints) - {"schema_version", "calculator_id"})
    if unknown:
        raise StudySpecContractError(
            "CALCULATOR_SELECTION_CONSTRAINT_FIELD_UNKNOWN",
            "only calculator_id may constrain selection",
            fields=unknown,
        )
    result = {"calculator_id": constraints.get("calculator_id")}
    calculator_id = result.get("calculator_id")
    if not calculator_id:
        return result
    record = solution_identifier_registry().get("calculators_by_id", {}).get(str(calculator_id))
    if record is None:
        raise StudySpecContractError(
            "UNKNOWN_CALCULATOR_ID", "calculator_id is not registered",
            calculator_id=calculator_id,
        )
    conflicts = []
    for field in ("requested_output", "catalog_procedure_id", "engine_procedure_id", "procedure_key"):
        registered = record.get(field)
        supplied = result.get(field)
        if supplied is not None and supplied != registered:
            conflicts.append({"field": field, "supplied": supplied, "registered": registered})
        elif supplied is None and registered is not None:
            result[field] = copy.deepcopy(registered)
    if conflicts:
        raise StudySpecContractError(
            "CALCULATOR_ID_CONFLICT", "calculator_id conflicts with request identity",
            conflicts=conflicts,
        )
    return result


def _initial_state(
    study_spec: dict[str, Any], request: dict[str, Any], interaction: dict[str, Any],
    resolution_state: dict[str, Any], selection_constraints: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(study_spec.get("study"), dict) or not isinstance(study_spec.get("values"), dict):
        raise StudySpecContractError("INVALID_STUDY_SPEC_V2", "study and values must be objects")
    constraints = _validate_calculator_constraint(selection_constraints)
    requested_output = str(request.get("requested_output") or "required_sample_size")
    operation, target = _requested_output_policy(requested_output, constraints.get("calculator_id"))
    state = copy.deepcopy(study_spec["study"])
    requested_mode = _normalized_mode((interaction.get("presentation") or {}).get("requested_mode") or "CALCULATE") or "CALCULATE"
    state.update({
        "requested_mode": requested_mode,
        "requested_output": requested_output,
        "operation": operation,
        "calculation_target": target,
        "requested_public_id": constraints.get("catalog_procedure_id"),
        "requested_engine_id": constraints.get("engine_procedure_id"),
        "requested_procedure_key": constraints.get("procedure_key"),
        "calculator_id": constraints.get("calculator_id"),
        "power_scenarios": copy.deepcopy(request.get("power_scenarios")),
        "calculation_grid": copy.deepcopy(request.get("calculation_grid") or {}),
        "user_provided_values": {}, "inferred_values": {}, "defaulted_values": {},
        "derived_values": {},
        "defaults_applied": [], "value_sources": {}, "derived_input_mappings": [],
    })
    state.update(copy.deepcopy(interaction.get("conversation") or {}))
    missing, uncertain, conflicts = legacy_unresolved_lists(resolution_state)
    state["missing_required_fields"] = missing
    state["uncertain_fields"] = uncertain
    state["input_conflicts"] = conflicts
    for name, value in study_spec["values"].items():
        source = _source(study_spec, str(name))
        state["value_sources"][name] = source
        # Policy defaults are recomputed from current canonical intent.
        if source == "policy_default":
            continue
        if name in SPECIAL_VALUE_FIELDS:
            state[name] = copy.deepcopy(value)
        elif source == "derived":
            state["derived_values"][name] = copy.deepcopy(value)
        elif source == "inferred":
            state["inferred_values"][name] = copy.deepcopy(value)
        else:
            state["user_provided_values"][name] = copy.deepcopy(value)
            if name in SELECTION_CONTEXT_VALUE_FIELDS:
                state[name] = copy.deepcopy(value)
    return state


def _has_explicit(state: dict[str, Any], name: str) -> bool:
    return str((state.get("value_sources") or {}).get(name) or "").startswith("user_")


def _apply_native_defaults(state: dict[str, Any]) -> None:
    user = state["user_provided_values"]
    fixed_cluster_size = (
        state.get("requested_output") == "required_cluster_size"
        and state.get("design_type") == "parallel_cluster_fixed_analyzable_cluster_count"
    )
    if fixed_cluster_size:
        _record(state, "cluster_attrition_rate", 0.0, "no cluster attrition was requested")
        _record(state, "individual_attrition_rate", 0.0, "no individual attrition was requested")
        if state.get("sidedness") is None:
            state["sidedness"] = 2
            _record(state, "sides", 2, "fixed-cluster comparison default is two-sided")
    repeated_standardized = (
        state.get("requested_public_id") == "TWO-C-009"
        or state.get("repeated_measures") is True
        or state.get("design_type") == "repeated_measures_two_group"
    ) and state.get("effect_measure") in {
        "standardized_effect", "standardized_mean_difference",
    }
    if repeated_standardized:
        state["effect_measure"] = "post_intervention_mean_difference"
        standardized = user.get("standardized_effect")
        if standardized is not None:
            _record_derived(state, "planned_mean_difference", standardized, "standardized effect numerator")
            _record_derived(state, "planned_sd", 1.0, "standardized effect reference SD")
        _record(state, "pre_measurements", 0, "no pre-intervention measurements were requested")
        state["derived_input_mappings"].append({
            "source": "standardized_effect", "targets": ["planned_mean_difference", "planned_sd"],
            "rule": "planned_mean_difference = standardized_effect and planned_sd = 1",
        })

    precision = state.get("hypothesis_objective") == "precision_estimation"
    one_binary = state.get("number_of_groups") == 1 and (
        state.get("outcome_type") in {"binary", "proportion", "proportion_or_mean"}
        or (state.get("outcome_code") == "B" and state.get("design_type") in {None, "one_group"})
    )
    if precision and one_binary:
        method = str(state.get("confidence_interval_method") or "").lower()
        if not method or method == "wilson":
            state["requested_public_id"] = "CI-B-003"
            _record_study_default(state, "confidence_interval_method", "Wilson", "one-group proportion CI-width default")
        elif method in {"wald", "normal", "normal_approximation"}:
            state["requested_public_id"] = "CI-B-001"
        else:
            state["unsupported_method_request"] = state.get("confidence_interval_method")
        if not state.get("width_definition"):
            _record_study_default(state, "width_definition", "full_width", "CI width means upper minus lower")
        if state.get("confidence_level") is not None and state.get("alpha") is None:
            state["alpha"] = 1.0 - float(state["confidence_level"])
            _record_derived(state, "alpha", state["alpha"], "alpha = 1 - confidence level")
        state["power_scenarios"] = []
        return

    identity_missing = not any(state.get(key) for key in (
        "requested_public_id", "requested_engine_id", "requested_procedure_key",
    ))
    if (one_binary and state.get("hypothesis_objective") in {None, "superiority_hypothesis_test"}
            and ("known_proportion" in user or state.get("effect_measure") in {None, "risk_difference"})
            and identity_missing):
        state["requested_public_id"] = "ONE-B-001"
        _record(state, "procedure", "ONE-B-001", "one-group proportion comparison with a known reference")
        identity_missing = False
    if (state.get("number_of_groups") == 1
            and state.get("outcome_type") in {"survival", "time_to_event"}
            and {"null_survival_probability", "alternative_survival_probability"}.issubset(user)
            and identity_missing):
        state["requested_public_id"] = "ONE-S-001"
        state["effect_measure"] = "arcsine_square_root_survival_difference"
        state.setdefault("design_type", "one_sample_survival_probability")
        state.setdefault("repeated_measures", False)
        _record(state, "procedure", "ONE-S-001", "one-group fixed-time Kaplan-Meier survival probability")
        identity_missing = False
    if (state.get("calculation_target") == "required_events"
            and state.get("effect_measure") in {"hazard_ratio", None} and identity_missing):
        state["requested_public_id"] = "TWO-S-001"
        _record(state, "procedure", "TWO-S-001", "default event-count method: Schoenfeld proportional hazards")
        identity_missing = False
    if (state.get("number_of_groups") == 2
            and state.get("outcome_type") in {"continuous", "mean"}
            and state.get("design_type") in {None, "independent", "independent_two_group"}
            and not state.get("repeated_measures")
            and state.get("hypothesis_objective") in {None, "superiority_hypothesis_test"}
            and state.get("analysis_method") is None
            and identity_missing):
        if (
            state.get("calculation_target") == "detectable_effect"
            and state.get("effect_measure") == "standardized_mean_difference"
        ):
            state["requested_public_id"] = "TWO-C-003"
            _record(
                state, "procedure", "TWO-C-003",
                "default registered two-group standardized detectable-effect procedure",
            )
        elif state.get("calculation_target") != "detectable_effect":
            state["requested_public_id"] = "TWO-C-002"
            _record(state, "procedure", "TWO-C-002", "default exact two-sample noncentral-t procedure")

    groups = state.get("number_of_groups")
    if groups == 2 and state.get("allocation") is None and state.get("calculation_target") != "power":
        state["allocation"] = DEFAULT_ALLOCATION
        _record(state, "allocation_ratio", DEFAULT_ALLOCATION, "equal allocation default")
    achieved_power = state.get("calculation_target") == "power"
    if achieved_power:
        state["operation"] = "POWER"
        state["power_scenarios"] = []
    if precision or str(state.get("requested_public_id") or "").startswith("CI-"):
        state["power_scenarios"] = []
        return
    objective = str(state.get("hypothesis_objective") or "").lower()
    exception = any(token in objective for token in EXCEPTION_TOKENS) or (
        state.get("multi_hypothesis_structure") == "multiple_confirmatory_comparisons"
    )
    if exception:
        scenarios = state.get("power_scenarios")
        if isinstance(scenarios, list) and scenarios and state.get("target_power") is None:
            state["target_power"] = scenarios[0]
        elif state.get("target_power") is not None:
            state["power_scenarios"] = [float(state["target_power"])]
        else:
            state["power_scenarios"] = []
        return
    if state.get("alpha") is None:
        state["alpha"] = DEFAULT_ALPHA
        _record(state, "alpha", DEFAULT_ALPHA, "default significance level")
    if (groups == 1 and state.get("hypothesis_objective") in {None, "superiority_hypothesis_test"}
            and state.get("sidedness") in {2, "two_sided"} and not _has_explicit(state, "sidedness")
            and state.get("directionality") != "nondirectional"):
        state["sidedness"] = None
    if state.get("sidedness") is None:
        direction = state.get("directionality")
        if groups == 1 and direction == "directional":
            state["sidedness"] = 1
            _record(state, "sides", 1, "one-group directional hypothesis")
        elif groups == 1 and direction == "nondirectional":
            state["sidedness"] = 2
            _record(state, "sides", 2, "one-group nondirectional hypothesis")
        elif groups == 1 and state.get("hypothesis_objective") in {None, "superiority_hypothesis_test"}:
            state["sidedness"] = 1
            _record(state, "sides", 1, "one-group direction-unspecified benchmark default")
        elif groups == 2 and state.get("hypothesis_objective") in {None, "superiority_hypothesis_test"}:
            state["sidedness"] = 2
            _record(state, "sides", 2, "ordinary two-group superiority comparison")
    if achieved_power:
        return
    beta = user.get("beta")
    if state.get("target_power") is None and beta is not None:
        state["target_power"] = 1.0 - float(beta)
        _record_derived(state, "target_power", state["target_power"], "target power = 1 - beta")
    scenarios = state.get("power_scenarios")
    if isinstance(scenarios, list) and scenarios:
        if state.get("target_power") is None:
            state["target_power"] = scenarios[0]
    elif state.get("target_power") is None:
        state["power_scenarios"] = list(POWER_VALUES)
        state["target_power"] = POWER_VALUES[0]
        _record(state, "power", list(POWER_VALUES), "default sensitivity set")
    else:
        state["power_scenarios"] = [float(state["target_power"])]


def _sync_contracts(
    study_spec: dict[str, Any], request: dict[str, Any], resolution_state: dict[str, Any],
    interaction: dict[str, Any], state: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    updated_study = copy.deepcopy(study_spec)
    updated_request = copy.deepcopy(request)
    updated_interaction = copy.deepcopy(interaction)
    updated_study.setdefault("schema_version", SCHEMA_VERSION)
    updated_study.setdefault("revision", 1)
    updated_study["study"] = {
        field: copy.deepcopy(state[field]) for field in canonical_study_output_fields()
        if state.get(field) is not None
    }
    values: dict[str, Any] = {}
    for container in ("user_provided_values", "inferred_values", "derived_values", "defaulted_values"):
        values.update(copy.deepcopy(state.get(container) or {}))
    for field in SPECIAL_VALUE_FIELDS:
        if state.get(field) is not None:
            values[field] = copy.deepcopy(state[field])
    updated_study["values"] = values
    provenance = {
        pointer: copy.deepcopy(meta) for pointer, meta in (study_spec.get("provenance") or {}).items()
        if not str((meta or {}).get("source")) == "policy_default"
    }
    for name in values:
        pointer = f"/values/{_token(str(name))}"
        source = str((state.get("value_sources") or {}).get(name) or "")
        if name in state.get("defaulted_values", {}) or source == "policy_default":
            provenance[pointer] = {"source": "policy_default", "service_id": SERVICE_ID}
        elif source == "derived":
            provenance[pointer] = {"source": "derived", "service_id": SERVICE_ID}
        elif source == "inferred" or name in state.get("inferred_values", {}):
            provenance[pointer] = {"source": "inferred", "service_id": SERVICE_ID}
        else:
            provenance.setdefault(pointer, {"source": "user_explicit"})
    updated_study["provenance"] = provenance
    updated_study.pop("unresolved", None)
    updated_request.update({
        "schema_version": SCHEMA_VERSION,
        "requested_output": state["requested_output"],
        "power_scenarios": copy.deepcopy(state.get("power_scenarios")),
        "calculation_grid": copy.deepcopy(state.get("calculation_grid") or {}),
    })
    for field in (
        "calculator_id", "catalog_procedure_id", "engine_procedure_id",
        "engine_model_id", "procedure_key", "available",
    ):
        updated_request.pop(field, None)
    updated_request = {key: value for key, value in updated_request.items() if value is not None}
    compatibility = updated_interaction.setdefault("compatibility", {})
    compatibility.pop("selector_defaults_adapter", None)
    compatibility.pop("v2_native_planning", None)
    issues = issues_from_legacy({
        "missing_required_fields": state.get("missing_required_fields") or [],
        "uncertain_fields": state.get("uncertain_fields") or [],
        "input_conflicts": state.get("input_conflicts") or [],
    })
    existing_nonblocking = [
        copy.deepcopy(issue) for issue in (resolution_state.get("issues") or [])
        if not issue.get("blocking")
    ]
    updated_resolution = build_resolution_state([*existing_nonblocking, *issues])
    return updated_study, updated_request, updated_resolution, updated_interaction


def prepare_v2_native(
    study_spec: dict[str, Any], calculation_request: dict[str, Any],
    interaction_context: dict[str, Any] | None = None,
    resolution_state: dict[str, Any] | None = None,
    selection_constraints: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Normalize/default canonical contracts and create an internal selection view."""
    interaction = copy.deepcopy(interaction_context or {
        "schema_version": SCHEMA_VERSION, "presentation": {}, "conversation": {}, "compatibility": {},
    })
    current_resolution = build_resolution_state([
        *((resolution_state or {}).get("issues") or []),
        *issues_from_legacy(study_spec),
    ])
    constraints = copy.deepcopy(selection_constraints or {})
    normalized_study, field_normalizations, location_errors = normalize_study_spec_fields(study_spec)
    normalized_study.pop("unresolved", None)
    canonical_request = {
        key: copy.deepcopy(value) for key, value in calculation_request.items()
        if key not in {"calculator_id", "catalog_procedure_id", "engine_procedure_id", "engine_model_id", "procedure_key", "available"}
    }
    _validate_calculator_constraint(constraints)
    field_validation = validate_study_spec_fields(normalized_study)
    semantic_errors = [*location_errors, *field_validation["errors"]]
    semantic_issues = [normalize_issue(error, category="conflict") for error in semantic_errors]
    warning_issues = [normalize_issue(warning, category="warning") for warning in field_validation["warnings"]]
    current_resolution = build_resolution_state([
        *(current_resolution.get("issues") or []), *semantic_issues, *warning_issues,
    ])
    state = _initial_state(
        normalized_study, canonical_request, interaction, current_resolution, constraints,
    )
    if not semantic_errors:
        _apply_native_defaults(state)
    updated_study, updated_request, updated_resolution, updated_interaction = _sync_contracts(
        normalized_study, canonical_request, current_resolution, interaction, state,
    )
    trace = {
        "service_id": SERVICE_ID,
        "defaults_applied": copy.deepcopy(state["defaults_applied"]),
        "legacy_projection_used": False,
        "study_field_normalizations": copy.deepcopy(field_normalizations),
        "study_field_warnings": copy.deepcopy(field_validation["warnings"]),
        "study_field_error_count": len(semantic_errors),
    }
    return updated_study, updated_request, updated_resolution, updated_interaction, state, trace
