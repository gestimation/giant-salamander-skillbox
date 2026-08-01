"""Small, loss-aware projections for assistant-facing responses.

The audited planner and example retriever keep their complete output contracts.
These projections remove repeated QC material before JSON is returned to the
conversation model.  They never calculate, round, or alter an engine value.
"""

from __future__ import annotations

import math
from typing import Any


SCHEMA_VERSION = "0.2.0"
MATCH_RANK = {"EXACT": 3, "SAME_METHOD_DIFFERENT_OPERATION": 2, "RELATED": 1}
SIMILARITY_WEIGHTS = {
    "pre_measurements": 5,
    "post_measurements": 5,
    "correlation": 5,
    "allocation_ratio": 3,
    "control_to_treatment_ratio": 3,
    "alpha": 2,
    "sides": 2,
    "power": 2,
}


def _without_empty(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: cleaned
            for key, item in value.items()
            if (cleaned := _without_empty(item)) not in (None, [], {})
        }
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := _without_empty(item)) not in (None, [], {})]
    return value


def _unique(items: list[Any]) -> list[Any]:
    result: list[Any] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def _compact_selection(selection: dict[str, Any] | None) -> dict[str, Any] | None:
    if not selection:
        return None
    keys = (
        "status", "selected_procedure_key", "selected_public_id", "engine_id",
        "calculation_target", "missing_calculation_inputs", "multiplicity_applicability",
        "multiplicity_strategy", "warnings", "input_conflicts",
    )
    return _without_empty({key: selection.get(key) for key in keys})


def _compact_offer(offer: dict[str, Any] | None) -> dict[str, Any] | None:
    if not offer:
        return None
    keys = (
        "available", "public_id", "operation", "best_match_type", "candidate_count",
        "message", "detail_loaded", "formula_verified", "source_inconsistency_excluded",
    )
    return _without_empty({key: offer.get(key) for key in keys})


def _final_allocation(allocation: dict[str, Any] | None) -> dict[str, Any]:
    if not allocation:
        return {}
    return {
        key: value
        for key, value in allocation.items()
        if key.startswith("final_") or key in {
            "assessment_count_per_participant", "clusters", "cluster_size",
            "final_clusters", "final_cluster_size",
        }
    }


def _compact_calculation_result(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not result:
        return None
    return _without_empty({
        key: value for key, value in result.items()
        if key != "scenario_results"
    } | {
        "scenario_results": [
            _without_empty({
                "scenario_index": row.get("scenario_index"),
                "status": row.get("status"),
                "final_result": row.get("final_result"),
                "validation": row.get("validation"),
                "final_allocation": _final_allocation(row.get("group_or_cluster_allocation")),
                "warnings": row.get("warnings", []),
            })
            for row in result.get("scenario_results", [])
        ]
    })


def _common_inputs(calculations: list[dict[str, Any]]) -> dict[str, Any]:
    if not calculations:
        return {}
    inputs = [row.get("structured_inputs") or {} for row in calculations]
    common = dict(inputs[0])
    for key in list(common):
        if key == "power" or any(row.get(key) != common[key] for row in inputs[1:]):
            common.pop(key, None)
    return common


def _effective_defaults(defaults: list[dict[str, Any]], calculations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hide a default trace entry when the effective engine input overrides it."""
    inputs = [row.get("structured_inputs") or {} for row in calculations]
    result = []
    for entry in defaults:
        field = entry.get("field")
        effective = _unique([row.get(field) for row in inputs if field in row])
        expected = entry.get("value")
        if effective:
            if isinstance(expected, list):
                if effective != expected:
                    continue
            elif len(effective) != 1 or effective[0] != expected:
                continue
        result.append(entry)
    return result


def _key_assumptions(defaults: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep user-facing default rationale short enough for routine replies."""
    fields = {"alpha", "sides", "allocation_ratio", "confidence_interval_method", "width_definition"}
    return [
        _without_empty({"field": item.get("field"), "value": item.get("value"), "reason": item.get("rule")})
        for item in defaults if item.get("field") in fields
    ]


def _adopted_inputs(result: dict[str, Any], calculations: list[dict[str, Any]]) -> dict[str, Any]:
    """Expose the actual calculation inputs for a one-line user confirmation."""
    study = result.get("study_spec") or {}
    values: dict[str, Any] = {}
    for key in ("number_of_groups", "design_type", "hypothesis_objective", "requested_public_id"):
        if study.get(key) is not None:
            values[key] = study[key]
    for container in ("user_provided_values", "effect_assumptions", "nuisance_parameters", "attrition_assumptions"):
        payload = study.get(container)
        if isinstance(payload, dict):
            values.update(payload)
    values.update(_common_inputs(calculations))
    powers = _unique([
        (row.get("structured_inputs") or {}).get("power")
        for row in calculations
        if (row.get("structured_inputs") or {}).get("power") is not None
    ])
    if powers:
        values["power_scenarios"] = powers
    return values


def compact_plan(result: dict[str, Any]) -> dict[str, Any]:
    """Project a complete planner result without changing any result value."""
    execution = result.get("execution_spec") or {}
    selection = result.get("selection") or result.get("procedure_selection") or {}
    compact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "view": "assistant_compact",
        "status": result.get("status"),
        "calculation_request": _without_empty({
            key: (result.get("calculation_request") or {}).get(key)
            for key in ("request_id", "requested_output")
        }),
        "resolved_calculation_request": _without_empty({
            key: (result.get("resolved_calculation_request") or {}).get(key)
            for key in (
                "request_id", "calculator_id", "catalog_procedure_id",
                "engine_procedure_id", "engine_model_id", "procedure_key", "available",
            )
        }),
        "resolution_state": (
            result.get("resolution_state")
            if (result.get("resolution_state") or {}).get("issues") else None
        ),
        "contract_validation": result.get("contract_validation"),
        "audit_recording": result.get("audit_recording"),
        "selection": _compact_selection(selection),
        "defaults_applied": result.get("defaults_applied", []),
        "key_assumptions": _key_assumptions(result.get("defaults_applied", [])),
        "questions": result.get("questions", []),
        "reason_codes": result.get("reason_codes") or selection.get("reason_codes", []),
        "scenario_errors": result.get("scenario_errors", []),
        "error": result.get("error"),
        "unsupported_reason": result.get("unsupported_reason") or selection.get("unsupported_reason"),
        "missing_capability": result.get("missing_capability") or selection.get("missing_capability", []),
        "closest_related_procedures": (
            result.get("closest_related_procedures")
            or selection.get("closest_related_procedures", [])
        ),
        "nonengine_context": result.get("nonengine_context"),
        "full_output_available": True,
    }
    canonical_result = result.get("calculation_result")
    if canonical_result:
        study_spec = result.get("study_spec") or result.get("study_spec_v2") or {}
        compact["study_spec_reference"] = _without_empty({
            "revision": study_spec.get("revision"),
        })
        compact["calculation_result"] = _compact_calculation_result(canonical_result)
        compact["execution_summary"] = _without_empty({
            "input_fingerprint": execution.get("input_fingerprint"),
            "scenario_count": len(execution.get("scenarios") or []),
        })
    calculations = result.get("calculations") or []
    if calculations:
        study_spec = result.get("study_spec_v2") or {}
        compact["study_spec_reference"] = _without_empty({
            "revision": study_spec.get("revision"),
        })
        compact["calculation_result"] = _compact_calculation_result(result.get("calculation_result"))
        compact["execution_summary"] = _without_empty({
            "input_fingerprint": execution.get("input_fingerprint"),
            "scenario_count": len(execution.get("scenarios") or []),
        })
        first = calculations[0]
        displays = [row.get("display") or {} for row in calculations]
        engine = first.get("engine_output") or {}
        compatibility = first.get("engine_compatibility") or {}
        result_table = result.get("result_table") or []
        scenarios = []
        for index, calculation in enumerate(calculations):
            inputs = calculation.get("structured_inputs") or {}
            table = result_table[index] if index < len(result_table) else {}
            scenarios.append(_without_empty({
                "power": inputs.get("power"),
                "beta": table.get("beta"),
                "input_grid": table.get("input_grid"),
                "final_result": calculation.get("final_result"),
                "final_allocation": _final_allocation(calculation.get("group_or_cluster_allocation")),
                "warnings": calculation.get("warnings", []),
            }))
        compact.update({
            "method": _without_empty({
                "procedure_key": first.get("procedure_key"),
                "public_id": first.get("public_id"),
                "engine_id": first.get("engine_id"),
                "calculation_target": first.get("calculation_target"),
                "formula_reference": engine.get("formula_reference"),
                "rounding_rule": engine.get("rounding_rule"),
                "engine_version": compatibility.get("version"),
            }),
            "common_inputs": _common_inputs(calculations),
            "adopted_inputs": _adopted_inputs(result, calculations),
            "scenarios": scenarios,
            "method_limitations": _unique([
                limitation
                for display in displays
                for limitation in display.get("method_limitations", [])
            ]),
            "warnings": _unique([
                warning for calculation in calculations for warning in calculation.get("warnings", [])
            ]),
            "research_example_offer": _compact_offer(displays[0].get("research_example_offer")),
        })
        compact["defaults_applied"] = _effective_defaults(
            result.get("defaults_applied", []), calculations
        )
        compact["key_assumptions"] = _key_assumptions(compact["defaults_applied"])
    elif result.get("calculation"):
        calculation = result["calculation"]
        compact["composition"] = _without_empty({
            key: calculation.get(key)
            for key in (
                "status", "composition_rule_id", "parent_public_id", "per_comparison_alpha",
                "final_group_sizes", "final_total", "warnings", "assumptions",
            )
        })
    projected = _without_empty(compact)
    if result.get("status") == "UNSUPPORTED":
        projected["questions"] = []
    return projected


def inputs_for_similarity(value: dict[str, Any] | None) -> dict[str, Any]:
    """Accept a StudySpec, full plan result, compact result, or engine input object."""
    value = value or {}
    if value.get("common_inputs"):
        return dict(value["common_inputs"])
    calculations = value.get("calculations") or []
    if calculations and calculations[0].get("structured_inputs"):
        return dict(calculations[0]["structured_inputs"])
    merged = dict(value.get("inferred_values") or {})
    merged.update(value.get("user_provided_values") or {})
    for key, item in value.items():
        if key not in {
            "user_provided_values", "inferred_values", "missing_required_fields",
            "uncertain_fields", "defaults_applied", "calculations",
        } and isinstance(item, (str, int, float, bool)):
            merged.setdefault(key, item)
    return merged or dict(value)


def _numeric_distance(left: float, right: float) -> float:
    scale = max(abs(left), abs(right), 1.0)
    return abs(left - right) / scale


def _case_score(case: dict[str, Any], current_inputs: dict[str, Any]) -> tuple[float, float]:
    candidate = case.get("structured_inputs") or {}
    exact_weight = 0.0
    distance = 0.0
    compared = 0
    for key, current in current_inputs.items():
        if key not in candidate or current is None or candidate[key] is None:
            continue
        other = candidate[key]
        weight = float(SIMILARITY_WEIGHTS.get(key, 1))
        compared += 1
        if isinstance(current, (int, float)) and not isinstance(current, bool) and isinstance(other, (int, float)) and not isinstance(other, bool):
            if math.isclose(float(current), float(other), rel_tol=1e-9, abs_tol=1e-12):
                exact_weight += weight
            distance += weight * _numeric_distance(float(current), float(other))
        elif str(current).casefold() == str(other).casefold():
            exact_weight += weight
        else:
            distance += weight
    match = MATCH_RANK.get(str(case.get("match_type")), 0)
    return (match * 1000 + exact_weight + compared / 1000, -distance)


def _compact_engine_result(result: dict[str, Any] | None) -> dict[str, Any]:
    result = result or {}
    excluded = {"quantities"}
    return _without_empty({
        key: value for key, value in result.items()
        if key not in excluded and isinstance(value, (str, int, float, bool, list, dict))
    })


def _compact_case(case: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "case_id", "research_example_id", "title", "match_type",
        "match_reasons", "public_id", "engine_id", "operation", "design", "outcome",
        "hypothesis", "effect_measure", "structured_inputs", "published_result",
        "discrepancy_status", "display_result_basis", "equation_references", "source",
        "explanation_points", "limitations", "values_are_defaults", "review_status",
    )
    compact = {key: case.get(key) for key in keys}
    compact["engine_result"] = _compact_engine_result(case.get("engine_result"))
    return _without_empty(compact)


def compact_example(result: dict[str, Any], current_inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return one best calculation case and counts for the remaining detail."""
    cases = [
        case
        for example in result.get("examples", [])
        for case in example.get("calculation_cases", [])
    ]
    current = inputs_for_similarity(current_inputs)
    selected = (
        max(enumerate(cases), key=lambda pair: (*_case_score(pair[1], current), -pair[0]))[1]
        if cases else None
    )
    studies = {case.get("research_example_id") for case in cases}
    compact = {
        "schema_version": SCHEMA_VERSION,
        "view": "assistant_compact",
        "available": result.get("available", False),
        "detail_loaded": result.get("detail_loaded", False),
        "procedure_key": result.get("procedure_key"),
        "public_id": result.get("public_id"),
        "operation": result.get("operation"),
        "best_match_type": result.get("best_match_type"),
        "candidate_count": result.get("candidate_count", 0),
        "formula_reference": result.get("formula_reference"),
        "formula_verified": result.get("formula_verified", False),
        "selected_case": _compact_case(selected) if selected else None,
        "remaining_calculation_case_count": max(0, len(cases) - (1 if selected else 0)),
        "remaining_research_example_count": max(0, len(studies) - (1 if selected else 0)),
        "warning": result.get("warning"),
        "full_output_available": True,
    }
    return _without_empty(compact)
