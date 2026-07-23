from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from naming_contract import requested_output_from_legacy, solution_identifier_registry
from resolution_state import (
    build_resolution_state, issues_from_legacy, legacy_unresolved_lists,
    make_issue, merge_resolution_state, normalize_issue,
)
from study_contract import (
    canonical_provenance_source, canonical_study_fields,
    canonical_study_output_fields, fingerprint_contract, study_contract,
)
from study_field_validation import normalize_study_spec_fields, validate_study_spec_fields


SCHEMA_VERSION = "2.0.0"
CONTRACT_BUNDLE_VERSION = "1.0.0"

STUDY_FIELDS = canonical_study_fields()
REQUEST_FIELDS = (
    "calculator_id", "catalog_procedure_id", "engine_procedure_id", "procedure_key",
    "alpha", "target_power", "power_scenarios", "sidedness", "allocation",
    "calculation_grid",
)
PHASE4_REQUEST_FIELDS = (
    "request_id", "power_scenarios", "calculation_grid",
)
PROVENANCE_FIELDS = (
    "user_provided_values", "inferred_values", "defaulted_values", "defaults_applied",
    "value_sources", "input_conflicts", "derived_input_mappings",
    "missing_required_fields", "uncertain_fields", "unsupported_method_request",
)
CONVERSATION_FIELDS = (
    "conversation_state_id", "input_summary", "accept_presented_defaults",
    "trial_mode", "explicit_updates", "reported_result",
)
VALUE_CONTAINERS = (
    ("defaulted_values", "default"),
    ("inferred_values", "inferred"),
    ("derived_values", "derived"),
    ("effect_assumptions", "assumption"),
    ("nuisance_parameters", "assumption"),
    ("attrition_assumptions", "assumption"),
    ("user_provided_values", "user"),
)
REQUESTED_OUTPUTS = {
    "required_sample_size", "required_events", "required_cluster_size",
    "attrition_adjusted_sample_size", "achieved_power", "detectable_effect",
}


class StudySpecContractError(ValueError):
    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.payload = {"code": code, "message": message, **details}


def _projection(spec: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    result = {
        field: copy.deepcopy(spec[field])
        for field in fields
        if field in spec and spec[field] is not None
    }
    return result


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    """Return a deterministic content fingerprint without changing any value."""
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _canonical_values(
    legacy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    values: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    declared_sources = legacy.get("value_sources") or {}
    for container, source in VALUE_CONTAINERS:
        payload = legacy.get(container)
        if not isinstance(payload, dict):
            continue
        for name, value in payload.items():
            values[name] = copy.deepcopy(value)
            provenance[f"/values/{_pointer_token(str(name))}"] = {
                "source": canonical_provenance_source(declared_sources.get(name, source)),
                "legacy_container": container,
            }
    for name, value, source_field in (
        ("alpha", legacy.get("alpha"), "alpha"),
        ("target_power", legacy.get("target_power"), "target_power"),
        ("sidedness", legacy.get("sidedness"), "sidedness"),
        ("allocation", legacy.get("allocation"), "allocation"),
    ):
        if value is not None:
            values[name] = copy.deepcopy(value)
            provenance.setdefault(
                f"/values/{name}",
                {
                    "source": canonical_provenance_source(declared_sources.get(name, "normalized")),
                    "legacy_field": source_field,
                },
            )
    conflicts: list[dict[str, Any]] = []
    for alias, canonical in {
        "sides": "sidedness", "allocation_ratio": "allocation",
    }.items():
        if alias not in values:
            continue
        alias_value = values.pop(alias)
        alias_provenance = provenance.pop(f"/values/{alias}", {"source": "imported_legacy"})
        if canonical in values and values[canonical] != alias_value:
            conflicts.append({
                "code": "DEPRECATED_ALIAS_CONFLICT", "path": f"/values/{canonical}",
                "message": f"{alias} conflicts with canonical {canonical}",
                "candidate_values": [copy.deepcopy(values[canonical]), copy.deepcopy(alias_value)],
                "expected_type": "one canonical value",
            })
            continue
        if canonical not in values:
            values[canonical] = copy.deepcopy(alias_value)
            provenance[f"/values/{canonical}"] = {
                **copy.deepcopy(alias_provenance), "compatibility_alias": alias,
            }
    # Legacy `power` may be a sensitivity-scenario array.  Scenario intent
    # belongs to CalculationRequest.power_scenarios, not StudySpec.values.
    if "power" in values:
        legacy_power = values.pop("power")
        legacy_power_provenance = provenance.pop("/values/power", {"source": "imported_legacy"})
        if "target_power" not in values and isinstance(legacy_power, (int, float)) and not isinstance(legacy_power, bool):
            values["target_power"] = copy.deepcopy(legacy_power)
            provenance["/values/target_power"] = {
                **copy.deepcopy(legacy_power_provenance), "compatibility_alias": "power",
            }
    values.pop("procedure", None)
    provenance.pop("/values/procedure", None)
    return values, provenance, conflicts


def _build_core_and_resolution(
    normalized_v1: dict[str, Any], *, revision: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    values, provenance, alias_conflicts = _canonical_values(normalized_v1)
    result = {
        "schema_version": SCHEMA_VERSION,
        "revision": revision,
        "study": _projection(normalized_v1, STUDY_FIELDS),
        "values": values,
        "provenance": provenance,
    }
    result, _normalizations, location_errors = normalize_study_spec_fields(result)
    result.pop("unresolved", None)
    semantic = validate_study_spec_fields(result)
    semantic_errors = [*location_errors, *semantic["errors"]]
    issues = [*issues_from_legacy(normalized_v1), *(
        normalize_issue(error, category="conflict") for error in alias_conflicts
    )]
    issues.extend(normalize_issue(error, category="conflict") for error in semantic_errors)
    issues.extend(normalize_issue(warning, category="warning") for warning in semantic["warnings"])
    return result, build_resolution_state(issues)


def build_core_study_spec(normalized_v1: dict[str, Any], *, revision: int = 1) -> dict[str, Any]:
    """Build only known research facts; resolution state is a separate contract."""
    study_spec, _resolution_state = _build_core_and_resolution(normalized_v1, revision=revision)
    return study_spec


def build_calculation_request(normalized_v1: dict[str, Any]) -> dict[str, Any]:
    request = _projection(normalized_v1, PHASE4_REQUEST_FIELDS)
    request["schema_version"] = SCHEMA_VERSION
    request["requested_output"] = requested_output_from_legacy(normalized_v1)
    return {key: value for key, value in request.items() if value is not None}


def _selection_constraints(normalized_v1: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "calculator_id": normalized_v1.get("calculator_id"),
        "catalog_procedure_id": normalized_v1.get("requested_public_id") or normalized_v1.get("catalog_procedure_id"),
        "engine_procedure_id": normalized_v1.get("requested_engine_id") or normalized_v1.get("engine_procedure_id"),
        "procedure_key": normalized_v1.get("requested_procedure_key") or normalized_v1.get("procedure_key"),
    }
    return {key: copy.deepcopy(value) for key, value in mapping.items() if value is not None}


def build_interaction_context(normalized_v1: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "requested_public_id": normalized_v1.get("requested_public_id"),
        "requested_engine_id": normalized_v1.get("requested_engine_id"),
        "requested_procedure_key": normalized_v1.get("requested_procedure_key"),
        "operation": normalized_v1.get("operation"),
        "calculation_target": normalized_v1.get("calculation_target"),
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "presentation": {
            "requested_mode": normalized_v1.get("requested_mode"),
            "output_detail": normalized_v1.get("output_mode", "concise"),
        },
        "conversation": _projection(normalized_v1, CONVERSATION_FIELDS),
        "compatibility": {
            "source_schema": "StudySpec-v1",
            "deprecated_aliases_read": {
                key: True for key, value in aliases.items() if value is not None
            },
        },
    }
    return result


def build_contract_bundle(normalized_v1: dict[str, Any]) -> dict[str, Any]:
    """Create the Phase 4 five-object boundary from one normalized legacy input."""
    legacy = copy.deepcopy(normalized_v1)
    study_spec, resolution_state = _build_core_and_resolution(legacy)
    return {
        "contract_version": CONTRACT_BUNDLE_VERSION,
        "study_spec": study_spec,
        "calculation_request": build_calculation_request(legacy),
        "resolution_state": resolution_state,
        "interaction_context": build_interaction_context(legacy),
        "_selection_constraints": _selection_constraints(legacy),
        # Private bridge data is never emitted by phase4_public_view().
        "_legacy_execution_spec": legacy,
    }


def legacy_input_from_contracts(
    study_spec: dict[str, Any], calculation_request: dict[str, Any],
    interaction_context: dict[str, Any] | None = None,
    resolution_state: dict[str, Any] | None = None,
    selection_constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt canonical contracts to the frozen selector/defaulting boundary."""
    interaction_context = interaction_context or {}
    presentation = interaction_context.get("presentation") or {}
    conversation = interaction_context.get("conversation") or {}
    legacy: dict[str, Any] = copy.deepcopy(study_spec.get("study") or {})
    legacy.update({
        key: copy.deepcopy(value) for key, value in calculation_request.items()
        if key != "schema_version"
    })
    constraints = selection_constraints or {}
    legacy["calculator_id"] = constraints.get("calculator_id")
    legacy["requested_public_id"] = constraints.get("catalog_procedure_id")
    legacy["requested_engine_id"] = constraints.get("engine_procedure_id")
    legacy["requested_procedure_key"] = constraints.get("procedure_key")
    legacy["requested_mode"] = presentation.get("requested_mode") or "CALCULATE"
    legacy.update(copy.deepcopy(conversation))
    legacy.setdefault("user_provided_values", {})
    legacy.setdefault("inferred_values", {})
    legacy.setdefault("derived_values", {})
    legacy.setdefault("defaulted_values", {})
    provenance = study_spec.get("provenance") or {}
    for name, value in (study_spec.get("values") or {}).items():
        pointer = f"/values/{_pointer_token(str(name))}"
        source = str((provenance.get(pointer) or {}).get("source") or "canonical")
        if name in {"alpha", "target_power", "sidedness", "allocation"}:
            legacy[name] = copy.deepcopy(value)
        elif "default" in source:
            legacy["defaulted_values"][name] = copy.deepcopy(value)
        elif source == "derived":
            legacy["derived_values"][name] = copy.deepcopy(value)
        elif "infer" in source:
            legacy["inferred_values"][name] = copy.deepcopy(value)
        else:
            legacy["user_provided_values"][name] = copy.deepcopy(value)
    missing, uncertain, conflicts = legacy_unresolved_lists(resolution_state)
    legacy["missing_required_fields"] = missing
    legacy["uncertain_fields"] = uncertain
    legacy["input_conflicts"] = conflicts
    return legacy


def _calculator_for(catalog_id: str | None, requested_output: str) -> dict[str, Any] | None:
    if not catalog_id:
        return None
    records = solution_identifier_registry().get("calculators_by_id", {}).values()
    matches = [
        record for record in records
        if record.get("catalog_procedure_id") == catalog_id
        and record.get("requested_output") == requested_output
    ]
    return copy.deepcopy(matches[0]) if len(matches) == 1 else None


def resolve_calculation_request(
    request: dict[str, Any], selection: dict[str, Any] | None,
    selection_constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a separate resolved request; never add identity to CalculationRequest."""
    constraints = copy.deepcopy(selection_constraints or {})
    selection = selection or {}
    if selection.get("status") != "SELECTED":
        return {}
    result = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request.get("request_id"),
        "requested_output": request.get("requested_output"),
        "catalog_procedure_id": selection.get("selected_public_id"),
        "engine_procedure_id": selection.get("engine_id"),
        "procedure_key": selection.get("selected_procedure_key"),
    }
    record = None
    if constraints.get("calculator_id"):
        record = solution_identifier_registry().get("calculators_by_id", {}).get(
            str(constraints["calculator_id"])
        )
    if record is None:
        record = _calculator_for(result.get("catalog_procedure_id"), result["requested_output"])
    if record:
        result["calculator_id"] = record["calculator_id"]
        result["engine_model_id"] = record.get("engine_model_id")
        result["available"] = bool(record.get("bundled_skill_available"))
        conflicts = []
        if constraints.get("calculator_id") and constraints["calculator_id"] != result["calculator_id"]:
            conflicts.append({
                "field": "calculator_id", "supplied": constraints["calculator_id"],
                "selected": result["calculator_id"],
            })
        if conflicts:
            raise StudySpecContractError(
                "CALCULATOR_SELECTION_CONFLICT",
                "requested calculator constraint conflicts with selected procedure",
                conflicts=conflicts,
            )
    return {key: value for key, value in result.items() if value is not None}


def compile_engine_inputs(
    study_spec: dict[str, Any], resolved_request: dict[str, Any],
) -> dict[str, Any]:
    """Compile normalized engine-facing values from the canonical StudySpec only."""
    values = copy.deepcopy(study_spec.get("values") or {})
    values.pop("beta", None)
    values.pop("procedure", None)
    requested_output = resolved_request.get("requested_output")
    if values.get("target_power") is not None and requested_output == "detectable_effect":
        pass
    elif values.get("target_power") is not None and requested_output != "achieved_power":
        values["power"] = values["target_power"]
    if requested_output != "detectable_effect":
        values.pop("target_power", None)
    if values.get("sidedness") is not None:
        sides = values.pop("sidedness")
        values["sides"] = 1 if sides == "one_sided" else 2 if sides == "two_sided" else sides
    allocation = values.pop("allocation", None)
    if isinstance(allocation, (int, float)) and not isinstance(allocation, bool):
        values["allocation_ratio"] = allocation
    elif isinstance(allocation, dict):
        values.update(allocation)
    # Repeated-measures defaults and standardized-effect derivations are
    # completed before this boundary; compilation never invents missing values.
    return values


def compile_execution_spec(
    study_spec: dict[str, Any], resolved_request: dict[str, Any],
    *, engine_inputs: dict[str, Any], scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compile the minimal, deterministic payload consumed by the engine boundary."""
    required = ("requested_output", "procedure_key", "engine_procedure_id")
    missing = [name for name in required if not resolved_request.get(name)]
    if missing:
        raise StudySpecContractError(
            "EXECUTION_REQUEST_INCOMPLETE",
            "calculation request is not bound to an executable procedure",
            missing=missing,
        )
    requested_output = str(resolved_request["requested_output"])
    registry_record = None
    calculator_id = resolved_request.get("calculator_id")
    if calculator_id:
        registry_record = solution_identifier_registry().get("calculators_by_id", {}).get(
            str(calculator_id)
        )
    if registry_record and not registry_record.get("bundled_skill_available"):
        raise StudySpecContractError(
            "CALCULATOR_UNAVAILABLE",
            "calculator is registered but unavailable in the bundled engine",
            calculator_id=calculator_id,
        )
    target = (
        registry_record.get("engine_calculation_target") if registry_record
        else "power" if requested_output == "achieved_power"
        else "required_sample_size"
    )
    actual_scenarios = copy.deepcopy(scenarios) if scenarios is not None else [copy.deepcopy(engine_inputs)]
    identity = {
        "calculator_id": calculator_id,
        "procedure_key": resolved_request["procedure_key"],
        "engine_procedure_id": resolved_request["engine_procedure_id"],
        "requested_output": requested_output,
        "engine_calculation_target": target,
        "scenarios": actual_scenarios,
    }
    fingerprint_policy = fingerprint_contract()
    result = {
        "schema_version": SCHEMA_VERSION,
        "study_spec_revision": study_spec.get("revision"),
        "request_id": resolved_request.get("request_id"),
        **identity,
        "fingerprint_version": fingerprint_policy["version"],
        "input_fingerprint": fingerprint(identity),
    }
    if result["request_id"] is None:
        result.pop("request_id")
    return result


def build_calculation_result(
    execution_spec: dict[str, Any], calculations: list[dict[str, Any]], *, status: str,
) -> dict[str, Any]:
    """Project engine results into a canonical result object without recalculation."""
    scenario_results = []
    for index, calculation in enumerate(calculations):
        scenario = {
            "scenario_index": index,
            "status": calculation.get("status"),
            "final_result": copy.deepcopy(calculation.get("final_result")),
            "group_or_cluster_allocation": copy.deepcopy(
                calculation.get("group_or_cluster_allocation") or {}
            ),
            "warnings": copy.deepcopy(calculation.get("warnings") or []),
        }
        engine_output = calculation.get("engine_output") or {}
        if execution_spec.get("requested_output") == "detectable_effect" and engine_output:
            trace = engine_output.get("calculation_trace") or {}
            scenario["validation"] = {
                "target_power": engine_output.get("target_power"),
                "achieved_power": engine_output.get("achieved_power"),
                "power_validation_residual": trace.get("power_validation_residual"),
                "calculation_mode": engine_output.get("calculation_mode"),
                "effect_measure": engine_output.get("effect_measure"),
                "alternative_direction": engine_output.get("alternative_direction"),
            }
        scenario_results.append(scenario)
    compatibility = calculations[0].get("engine_compatibility") if calculations else {}
    first_engine = calculations[0].get("engine_output") if calculations else {}
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "calculator_id": execution_spec.get("calculator_id"),
        "request_id": execution_spec.get("request_id"),
        "requested_output": execution_spec["requested_output"],
        "study_spec_revision": execution_spec.get("study_spec_revision"),
        "input_fingerprint": execution_spec["input_fingerprint"],
        "fingerprint_version": execution_spec["fingerprint_version"],
        "engine_version": (compatibility or {}).get("version"),
        "trace": {
            "formula_reference": (first_engine or {}).get("formula_reference"),
            "rounding_rule": (first_engine or {}).get("rounding_rule"),
        },
        "scenario_results": scenario_results,
    }
    if result["request_id"] is None:
        result.pop("request_id")
    return result


def phase4_public_view(bundle: dict[str, Any]) -> dict[str, Any]:
    """Return only durable/new-name objects; private legacy bridge data is excluded."""
    result = {
        "study_spec": copy.deepcopy(bundle["study_spec"]),
        "calculation_request": copy.deepcopy(bundle["calculation_request"]),
        "resolution_state": copy.deepcopy(bundle["resolution_state"]),
        "interaction_context": copy.deepcopy(bundle["interaction_context"]),
    }
    if bundle.get("resolved_calculation_request"):
        result["resolved_calculation_request"] = copy.deepcopy(bundle["resolved_calculation_request"])
    return result


def validate_contract_bundle(
    bundle: dict[str, Any], execution_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate structural, semantic, then executable concerns separately."""
    stages: dict[str, list[dict[str, Any]]] = {
        "structural": [], "semantic": [], "executable": [],
    }
    study = bundle.get("study_spec")
    request = bundle.get("calculation_request")
    resolved = bundle.get("resolved_calculation_request")
    resolution = bundle.get("resolution_state")
    interaction = bundle.get("interaction_context")
    if not isinstance(study, dict):
        stages["structural"].append({"code": "MISSING_STUDY_SPEC"})
    if not isinstance(request, dict):
        stages["structural"].append({"code": "MISSING_CALCULATION_REQUEST"})
    if not isinstance(resolution, dict):
        stages["structural"].append({"code": "MISSING_RESOLUTION_STATE"})
    if not isinstance(interaction, dict):
        stages["structural"].append({"code": "MISSING_INTERACTION_CONTEXT"})
    if isinstance(study, dict):
        for field in sorted(set(study) - {"schema_version", "revision", "study", "values", "provenance"}):
            stages["semantic"].append({"code": "STUDY_TOP_LEVEL_FIELD_UNKNOWN", "field": field})
        forbidden = {
            "calculation_request", "requested_output", "calculator_id",
            "interaction_context", "conversation", "compatibility", "results", "unresolved",
        } & set(study)
        for field in sorted(forbidden):
            stages["semantic"].append({"code": "STUDY_OWNERSHIP_VIOLATION", "field": field})
        canonical_sources = set(study_contract()["provenance"]["canonical_sources"])
        for path, provenance in (study.get("provenance") or {}).items():
            if not isinstance(provenance, dict) or provenance.get("source") not in canonical_sources:
                stages["semantic"].append({
                    "code": "NONCANONICAL_PROVENANCE", "path": path,
                })
        field_validation = validate_study_spec_fields(
            study, request if isinstance(request, dict) else None,
        )
        stages["semantic"].extend(copy.deepcopy(field_validation["errors"]))
    if isinstance(request, dict):
        forbidden_request = {
            "alpha", "target_power", "sidedness", "allocation", "calculator_id",
            "catalog_procedure_id", "engine_procedure_id", "engine_model_id", "procedure_key", "available",
        }
        for field in sorted(forbidden_request & set(request)):
            stages["semantic"].append({"code": "CALCULATION_REQUEST_OWNERSHIP_VIOLATION", "field": field})
        output = request.get("requested_output")
        if output not in REQUESTED_OUTPUTS:
            stages["semantic"].append({
                "code": "UNKNOWN_REQUESTED_OUTPUT", "requested_output": output,
            })
    if isinstance(resolved, dict):
        for name in (
            "schema_version", "requested_output", "calculator_id", "catalog_procedure_id",
            "procedure_key", "engine_procedure_id", "available",
        ):
            if resolved.get(name) is None:
                stages["semantic"].append({"code": "RESOLVED_REQUEST_FIELD_MISSING", "field": name})
        if isinstance(request, dict) and resolved.get("requested_output") != request.get("requested_output"):
            stages["semantic"].append({"code": "RESOLVED_REQUEST_INTENT_CONFLICT", "field": "requested_output"})
        calculator_id = resolved.get("calculator_id")
        if calculator_id:
            record = solution_identifier_registry().get("calculators_by_id", {}).get(str(calculator_id))
            if record is None:
                stages["semantic"].append({
                    "code": "UNKNOWN_CALCULATOR_ID", "calculator_id": calculator_id,
                })
            else:
                for name in ("requested_output", "catalog_procedure_id", "engine_procedure_id", "procedure_key"):
                    if resolved.get(name) is not None and resolved[name] != record.get(name):
                        stages["semantic"].append({
                            "code": "CALCULATOR_BINDING_CONFLICT", "field": name,
                        })
    if isinstance(resolution, dict):
        for issue in resolution.get("issues") or []:
            required_issue_fields = {
                "code", "path", "reason", "blocking", "expected_type", "candidate_values",
            }
            if not isinstance(issue, dict) or not required_issue_fields <= set(issue):
                stages["semantic"].append({"code": "RESOLUTION_ISSUE_INVALID"})
        blocking = any(
            isinstance(issue, dict) and issue.get("blocking") is True
            for issue in resolution.get("issues") or []
        )
        if blocking and resolution.get("status") == "RESOLVED":
            stages["semantic"].append({"code": "RESOLUTION_STATUS_CONFLICT"})
        if not blocking and resolution.get("status") == "NEEDS_CLARIFICATION":
            stages["semantic"].append({"code": "RESOLUTION_STATUS_CONFLICT"})
    if isinstance(interaction, dict):
        for field in sorted(set(interaction) - {"schema_version", "presentation", "conversation", "compatibility"}):
            stages["semantic"].append({"code": "INTERACTION_CONTEXT_OWNERSHIP_VIOLATION", "field": field})
        compatibility = interaction.get("compatibility") or {}
        if "v2_native_planning" in compatibility:
            stages["semantic"].append({"code": "INTERACTION_CONTEXT_OWNS_PLANNING_STATE"})
    if execution_spec is not None:
        for name in (
            "procedure_key", "engine_procedure_id", "requested_output",
            "fingerprint_version", "input_fingerprint",
        ):
            if not execution_spec.get(name):
                stages["executable"].append({"code": "EXECUTION_FIELD_MISSING", "field": name})
        if execution_spec.get("fingerprint_version") not in {None, fingerprint_contract()["version"]}:
            stages["executable"].append({"code": "FINGERPRINT_VERSION_UNSUPPORTED"})
    errors = [error for stage in stages.values() for error in stage]
    field_warnings = field_validation["warnings"] if isinstance(study, dict) else []
    return {
        "valid": not errors, "stages": stages, "error_count": len(errors),
        "warnings": copy.deepcopy(field_warnings),
    }


def _decode_pointer_token(value: str) -> str:
    return value.replace("~1", "/").replace("~0", "~")


def _patch_operations(updates: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(updates, dict):
        return [
            {"op": "upsert", "path": str(path), "value": copy.deepcopy(value)}
            for path, value in updates.items()
        ]
    if not isinstance(updates, list) or not updates:
        raise StudySpecContractError("INVALID_PATCH", "patch must contain at least one operation")
    return copy.deepcopy(updates)


def _patch_parts(path: Any) -> list[str]:
    value = str(path)
    parts = [_decode_pointer_token(part) for part in value.split("/")[1:]]
    if not value.startswith("/") or len(parts) < 2 or parts[0] not in {"study", "values"}:
        raise StudySpecContractError(
            "PATCH_PATH_NOT_ALLOWED",
            "patch paths must be below /study or /values",
            path=path,
        )
    if any(part == "" for part in parts):
        raise StudySpecContractError(
            "PATCH_PATH_NOT_ALLOWED", "empty path tokens are not supported", path=path,
        )
    return parts


def _list_index(token: str, length: int, path: str, *, allow_end: bool = False) -> int:
    if token == "-" and allow_end:
        return length
    if not token.isdigit():
        raise StudySpecContractError("PATCH_ARRAY_INDEX_INVALID", "array index must be a non-negative integer", path=path)
    index = int(token)
    limit = length if allow_end else length - 1
    if index < 0 or index > limit:
        raise StudySpecContractError("PATCH_ARRAY_INDEX_OUT_OF_RANGE", "array index is out of range", path=path)
    return index


def _patch_parent(document: dict[str, Any], parts: list[str], path: str) -> tuple[Any, str]:
    parent: Any = document
    for part in parts[:-1]:
        if isinstance(parent, dict):
            if part not in parent or not isinstance(parent[part], (dict, list)):
                raise StudySpecContractError(
                    "PATCH_PARENT_MISSING", "patch parent must already exist", path=path,
                )
            parent = parent[part]
        elif isinstance(parent, list):
            parent = parent[_list_index(part, len(parent), path)]
            if not isinstance(parent, (dict, list)):
                raise StudySpecContractError(
                    "PATCH_PARENT_MISSING", "patch parent must be an object or array", path=path,
                )
        else:
            raise StudySpecContractError(
                "PATCH_PARENT_MISSING", "patch parent must already exist", path=path,
            )
    return parent, parts[-1]


def apply_study_patch(
    study_spec: dict[str, Any], updates: dict[str, Any] | list[dict[str, Any]], *, base_revision: int,
) -> dict[str, Any]:
    """Atomically apply add/replace/remove operations with revision checking."""
    current_revision = study_spec.get("revision")
    if current_revision != base_revision:
        raise StudySpecContractError(
            "REVISION_CONFLICT", "study specification revision has changed",
            expected=base_revision, actual=current_revision,
        )
    operations = _patch_operations(updates)
    result = copy.deepcopy(study_spec)
    for operation in operations:
        op = str(operation.get("op") or "")
        pointer = str(operation.get("path") or "")
        if op not in {"add", "replace", "remove", "upsert"}:
            raise StudySpecContractError(
                "PATCH_OPERATION_NOT_ALLOWED", "supported operations are add, replace, and remove", op=op,
            )
        parts = _patch_parts(pointer)
        parent, key = _patch_parent(result, parts, pointer)
        if isinstance(parent, list):
            if op == "add":
                index = _list_index(key, len(parent), pointer, allow_end=True)
                exists = index < len(parent)
            else:
                index = _list_index(key, len(parent), pointer)
                exists = True
        elif isinstance(parent, dict):
            index = None
            exists = key in parent
        else:
            raise StudySpecContractError("PATCH_PARENT_INVALID", "patch parent must be an object or array", path=pointer)
        if op == "add" and exists:
            if not isinstance(parent, list):
                raise StudySpecContractError("PATCH_TARGET_EXISTS", "add target already exists", path=pointer)
        if op in {"replace", "remove"} and not exists:
            raise StudySpecContractError("PATCH_TARGET_MISSING", "patch target does not exist", path=pointer)
        if op == "remove":
            if isinstance(parent, list):
                parent.pop(index)
            else:
                del parent[key]
            if parts[0] == "values":
                provenance = result.setdefault("provenance", {})
                for path in list(provenance):
                    if path == pointer or path.startswith(pointer + "/"):
                        provenance.pop(path, None)
            continue
        if "value" not in operation:
            raise StudySpecContractError("PATCH_VALUE_MISSING", "add and replace require value", path=pointer)
        if isinstance(parent, list):
            if op == "add":
                parent.insert(index, copy.deepcopy(operation["value"]))
            else:
                parent[index] = copy.deepcopy(operation["value"])
        else:
            parent[key] = copy.deepcopy(operation["value"])
        if parts[0] == "values":
            result.setdefault("provenance", {})[pointer] = {"source": "user_patch"}
    result["revision"] = int(current_revision) + 1
    normalized, _normalizations, location_errors = normalize_study_spec_fields(result)
    semantic = validate_study_spec_fields(normalized)
    errors = [*location_errors, *semantic["errors"]]
    if errors:
        raise StudySpecContractError(
            "STUDY_PATCH_SEMANTIC_INVALID",
            "patch would create an invalid StudySpec",
            errors=errors,
        )
    return normalized


# Phase 3 compatibility API. New Phase 4 code uses build_contract_bundle().
def build_study_spec_v2(normalized_v1: dict[str, Any]) -> dict[str, Any]:
    """Return the deprecated Phase 3 envelope for callers pinned to 0.1.13."""
    legacy = copy.deepcopy(normalized_v1)
    request = _projection(legacy, REQUEST_FIELDS)
    request["requested_output"] = requested_output_from_legacy(legacy)
    request.setdefault("catalog_procedure_id", legacy.get("requested_public_id"))
    request.setdefault("engine_procedure_id", legacy.get("requested_engine_id"))
    request.setdefault("procedure_key", legacy.get("requested_procedure_key"))
    request = {key: value for key, value in request.items() if value is not None}
    return {
        "schema_version": SCHEMA_VERSION,
        "study": _projection(legacy, STUDY_FIELDS),
        "calculation_request": request,
        "value_provenance": _projection(legacy, PROVENANCE_FIELDS),
        "presentation_request": {"requested_mode": legacy.get("requested_mode")},
        "conversation_state": _projection(legacy, CONVERSATION_FIELDS),
        "compatibility": {
            "source_schema": "StudySpec-v1",
            "legacy_operation": legacy.get("operation"),
            "legacy_calculation_target": legacy.get("calculation_target"),
            "legacy_execution_spec": legacy,
        },
    }


def legacy_execution_spec(internal: dict[str, Any]) -> dict[str, Any]:
    """Return the frozen v1 execution view from either Phase 3 or Phase 4 data."""
    if "_legacy_execution_spec" in internal:
        return copy.deepcopy(internal["_legacy_execution_spec"])
    return copy.deepcopy(internal["compatibility"]["legacy_execution_spec"])
