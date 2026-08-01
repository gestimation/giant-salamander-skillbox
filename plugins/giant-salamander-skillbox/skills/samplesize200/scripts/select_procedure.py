from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import SkillContractError, catalog, emit, procedure_input_contract
from apply_defaults import apply_defaults
from normalize_study_spec import engine_field_name, normalize_spec
from validate_study_spec import validate_spec


OUTCOME_SYNONYMS = {
    "continuous": "C", "mean": "C", "correlation": "C", "reference_interval": "C",
    "binary": "B", "proportion": "B", "diagnostic_accuracy": "B",
    "count": "R", "rate": "R", "count_or_rate": "R",
    "survival": "S", "time_to_event": "S", "time-to-event": "S",
    "competing_risk": "S", "competing-risk": "S",
    "ordinal": "O", "nominal": "N", "multinomial": "N",
}
KAPPA_EFFECT_MEASURES = {"cohen_kappa", "cohens_kappa", "kappa", "κ"}


def _candidate_view(item: dict) -> dict:
    return {
        "procedure_key": item["procedure_key"], "public_id": item["public_id"],
        "engine_id": item["engine_id"], "title_ja": item["title_ja"],
        "design": item["design"], "effect_measure": item["effect_measure"],
    }


def _provided_keys(spec: dict) -> set[str]:
    keys = set(spec.get("user_provided_values", {}))
    keys.update(spec.get("defaulted_values", {}))
    keys.update(spec.get("derived_values", {}))
    for container in ["effect_assumptions", "nuisance_parameters", "attrition_assumptions"]:
        value = spec.get(container, {})
        if isinstance(value, dict):
            keys.update(value)
    if spec.get("alpha") is not None:
        keys.add("alpha")
    if spec.get("target_power") is not None and spec.get("calculation_target") != "power":
        keys.add("power")
    if spec.get("sidedness") is not None:
        keys.add("sides")
    allocation = spec.get("allocation")
    if isinstance(allocation, (int, float)):
        keys.add("allocation_ratio")
    elif isinstance(allocation, dict):
        keys.update(allocation)
    margin = spec.get("margin")
    if isinstance(margin, (int, float)):
        keys.add("margin")
    elif isinstance(margin, dict):
        keys.update(margin)
    if spec.get("multiplicity") is not None:
        keys.add("multiplicity")
    return keys


def _missing_inputs(item: dict, spec: dict) -> list[str]:
    provided = _provided_keys(spec)
    target = spec.get("calculation_target", "required_sample_size")
    try:
        contract = procedure_input_contract(item, target)
    except SkillContractError:
        return []
    required = set(contract.get("required_inputs", []))
    confirmations = set(item.get("explicit_confirmation_inputs", []))
    if target == "power":
        confirmations -= {"power", "allocation_ratio", "control_to_treatment_ratio"}
    required.update(confirmations & {
        row["name"] for row in contract.get("input_contracts", [])
    })
    unresolved = {
        engine_field_name(name)
        for key in ("missing_required_fields", "uncertain_fields")
        for name in (spec.get(key) or [])
    }
    return sorted((required - provided) | (required & unresolved))


def _matches_number(candidate: Any, requested: Any) -> bool:
    if requested is None:
        return True
    if candidate == "3_or_more":
        return isinstance(requested, int) and requested >= 3 or requested == "3_or_more"
    return candidate == requested


def _matches_profile(candidate: Any, requested: Any) -> bool:
    """Treat catalog placeholders as wildcards, never as user vocabulary."""
    if requested is None or candidate == "procedure-specific":
        return True
    return candidate == requested


def _normalized_effect(value: Any) -> str:
    return str(value or "").strip().lower().replace("'", "").replace("-", "_").replace(" ", "_")


def _is_kappa_request(spec: dict) -> bool:
    effect = _normalized_effect(spec.get("effect_measure"))
    values = spec.get("user_provided_values") or {}
    return effect in KAPPA_EFFECT_MEASURES or "planned_kappa" in values or "null_kappa" in values


def _matches_effect_profile(item: dict, requested: Any, objective: Any) -> bool:
    if (_normalized_effect(requested) in KAPPA_EFFECT_MEASURES
            and objective == "precision_estimation"):
        return item.get("public_id") == "AGREE-N-001"
    candidate = item["selection_profile"].get("effect_measure")
    if requested is None or candidate == "procedure-specific":
        return True
    return _normalized_effect(candidate) == _normalized_effect(requested)


def _is_factorial_interaction(spec: dict[str, Any]) -> bool:
    return (
        spec.get("design_type") == "factorial"
        and spec.get("hypothesis_objective") == "interaction_effect"
    )


def _common_missing_inputs(candidates: list[dict], spec: dict) -> list[str]:
    missing_sets = [set(_missing_inputs(item, spec)) for item in candidates]
    if not missing_sets:
        return []
    return sorted(set.intersection(*missing_sets))


def _direct(spec: dict, data: dict) -> list[dict] | None:
    for field, catalog_field in [
        ("requested_procedure_key", "procedure_key"), ("requested_public_id", "public_id"),
        ("requested_engine_id", "engine_id"),
    ]:
        value = spec.get(field)
        if value:
            return [x for x in data["procedures"] if x[catalog_field] == value]
    return None


def select_prepared(spec: dict) -> dict:
    """Select from a normalized/defaulted internal view.

    This is the shared selection core.  v1 callers use :func:`select`; v2
    callers prepare the view from the canonical contracts without invoking the
    legacy normalizer/defaulting pipeline.
    """
    if spec.get("input_conflicts"):
        return {
            "status": "NEEDS_CLARIFICATION",
            "candidate_procedures": [],
            "differing_fields": [x["field"] for x in spec["input_conflicts"]],
            "clarification_questions": [
                (
                    f"{x['field']} was previously confirmed as {x['previous_value']}, "
                    f"but the current turn contains {x['incoming_value']}. Which value should be used?"
                    if x.get("code") == "EXPLICIT_VALUE_REPLACEMENT_REQUIRES_CONFIRMATION"
                    else f"Conflicting values were provided for {x['field']}; please specify one value."
                )
                for x in spec["input_conflicts"]
            ],
            "reason_codes": ["INPUT_CONFLICT"],
            "input_conflicts": spec["input_conflicts"],
        }
    validation = validate_spec(spec)
    if not validation["valid"]:
        return {
            "status": "NEEDS_CLARIFICATION", "candidate_procedures": [],
            "differing_fields": [], "clarification_questions": validation["structural_errors"],
            "reason_codes": ["INVALID_STUDY_SPEC"],
        }
    if spec.get("design_description") and spec.get("paired_or_independent") is None:
        return {"status": "NEEDS_CLARIFICATION", "candidate_procedures": [], "differing_fields": ["paired_or_independent"], "clarification_questions": ["同じ被験者・対応ありの比較ですか、それとも別々の被験者・独立した比較ですか？"], "reason_codes": ["DESIGN_PAIRING_UNKNOWN"]}
    data = catalog()
    if spec.get("unsupported_method_request"):
        return {
            "status": "UNSUPPORTED",
            "unsupported_reason": f"The requested confidence-interval method is not a validated catalog procedure: {spec['unsupported_method_request']}",
            "closest_related_procedures": [],
            "missing_capability": ["requested confidence-interval method"],
            "reason_codes": ["NO_VALIDATED_PROCEDURE"],
        }

    if _is_factorial_interaction(spec):
        related = [
            _candidate_view(item) for item in data["procedures"]
            if (item.get("selection_profile") or {}).get("design_type") == "factorial_2x2"
        ][:5]
        return {
            "status": "UNSUPPORTED",
            "unsupported_reason": (
                "Factorial interaction-effect sample-size planning is not a validated public procedure; "
                "the available factorial calculators cover main effects only."
            ),
            "closest_related_procedures": related,
            "missing_capability": ["factorial interaction effect"],
            "reason_codes": ["FACTORIAL_INTERACTION_UNSUPPORTED"],
        }

    # MULTI routing is hypothesis-structure first. Missing structure must never
    # become an implicit multiplicity strategy of "none".
    is_multi = spec.get("number_of_groups") == "3_or_more" or (isinstance(spec.get("number_of_groups"), int) and spec.get("number_of_groups") >= 3) or str(spec.get("requested_public_id", "")).startswith("MULTI-") or str(spec.get("requested_engine_id", "")).startswith("MULTI-")
    multi_structure = spec.get("multi_hypothesis_structure")
    user_values = spec.get("user_provided_values") if isinstance(spec.get("user_provided_values"), dict) else {}
    strategy = spec.get("multiplicity_strategy") or user_values.get("multiplicity_strategy") or user_values.get("multiplicity")
    if str(strategy).lower() == "none" and not ({"multiplicity", "multiplicity_strategy"} & set(user_values)):
        strategy = None
    if is_multi and multi_structure in {None, "unknown"}:
        return {"status": "NEEDS_CLARIFICATION", "candidate_procedures": [], "differing_fields": ["multi_hypothesis_structure"], "clarification_questions": ["全群差の単一omnibus仮説だけが目的ですか、それとも複数の比較も主要な検証対象ですか？"], "reason_codes": ["MULTIPLICITY_STRUCTURE_UNKNOWN"]}
    if is_multi and multi_structure == "multiple_confirmatory_comparisons" and strategy is None:
        return {"status": "NEEDS_CLARIFICATION", "candidate_procedures": [], "differing_fields": ["multiplicity_strategy"], "clarification_questions": ["確証的な複数比較に用いる多重性調整法を指定してください。"], "reason_codes": ["MULTIPLICITY_STRATEGY_REQUIRED"]}
    routing_warnings = []
    if is_multi and multi_structure == "multiple_confirmatory_comparisons" and str(strategy).lower() == "none":
        routing_warnings.append("MULTIPLE_CONFIRMATORY_COMPARISONS_WITHOUT_MULTIPLICITY_CONTROL")
    legacy_id = spec.get("legacy_id")
    if legacy_id in data.get("legacy_ambiguities", {}):
        ambiguity = data["legacy_ambiguities"][legacy_id]
        by_key = {x["procedure_key"]: x for x in data["procedures"]}
        return {
            "status": "LEGACY_MAPPING_AMBIGUOUS", "legacy_id": legacy_id,
            "candidates": [_candidate_view(by_key[key]) for key in ambiguity["candidates"]],
            "disambiguating_fields": ambiguity["disambiguating_fields"],
        }
    if legacy_id:
        matches = [x for x in data["procedures"] if legacy_id in x.get("legacy_ids", [])]
        if len(matches) > 1:
            return {"status": "LEGACY_MAPPING_AMBIGUOUS", "legacy_id": legacy_id,
                    "candidates": [_candidate_view(x) for x in matches],
                    "disambiguating_fields": ["outcome_type", "analysis_method"]}
        candidates = matches
    else:
        direct = _direct(spec, data)
        candidates = direct if direct is not None else list(data["procedures"])
    direct_candidate_was_resolved = bool(direct) if not legacy_id else False

    if _is_kappa_request(spec) and not direct_candidate_was_resolved and not legacy_id:
        objective = spec.get("hypothesis_objective")
        precision = next(
            (item for item in data["procedures"] if item.get("public_id") == "AGREE-N-001"),
            None,
        )
        closest = [_candidate_view(precision)] if precision is not None else []
        if objective is None:
            return {
                "status": "NEEDS_CLARIFICATION",
                "candidate_procedures": closest,
                "differing_fields": ["hypothesis_objective"],
                "clarification_questions": [
                    "Is this a Cohen kappa hypothesis test or a confidence-interval precision design?"
                ],
                "reason_codes": ["CALCULATION_OBJECTIVE_REQUIRED"],
            }
        if objective != "precision_estimation":
            return {
                "status": "UNSUPPORTED",
                "unsupported_reason": (
                    "Cohen kappa hypothesis-test sample-size planning is not a validated public procedure."
                ),
                "closest_related_procedures": closest,
                "missing_capability": ["cohen_kappa hypothesis test"],
                "reason_codes": ["NO_VALIDATED_PROCEDURE"],
            }

    requested_code = spec.get("outcome_code") or OUTCOME_SYNONYMS.get(str(spec.get("outcome_type", "")).lower())
    canonical_outcome_type = spec.get("outcome_type")
    event_process_filter = canonical_outcome_type if canonical_outcome_type in {"time_to_event", "competing_risk"} else None
    target = spec.get("calculation_target", "required_sample_size")
    selection_operation = (
        "SAMPLE_SIZE" if target == "power"
        else "REQUIRED_CLUSTER_SIZE" if spec.get("requested_output") == "required_cluster_size"
        else spec.get("operation")
    )
    reasons = []
    if target in {"power", "detectable_effect"}:
        compatible = []
        for item in candidates:
            try:
                procedure_input_contract(item, target)
            except SkillContractError:
                continue
            compatible.append(item)
        candidates = compatible
        reasons.append(f"hard constraint calculation_target={target} and registered support")
    filters = [
        ("operation", selection_operation),
        ("outcome_code", requested_code),
        ("outcome_type", event_process_filter),
        ("design_type", spec.get("design_type")),
        ("paired_or_independent", spec.get("paired_or_independent")),
        ("clustered", spec.get("clustered")),
        ("repeated_measures", spec.get("repeated_measures")),
        ("hypothesis_objective", spec.get("hypothesis_objective")),
        ("effect_measure", spec.get("effect_measure")),
        ("analysis_method", spec.get("analysis_method")),
    ]
    for field, value in filters:
        if value is None:
            continue
        profile_field = "design_type" if field == "design_type" else field
        candidates = [
            x for x in candidates
            if (
                _matches_effect_profile(x, value, spec.get("hypothesis_objective"))
                if field == "effect_measure"
                else _matches_profile(x["selection_profile"].get(profile_field), value)
            )
        ]
        reasons.append(f"hard constraint {field}={value}")
    number = spec.get("number_of_groups")
    if number is not None:
        candidates = [x for x in candidates if _matches_number(x["selection_profile"].get("number_of_groups"), number)]
        reasons.append(f"hard constraint number_of_groups={number}")

    if not candidates:
        if direct_candidate_was_resolved:
            conflicting = [
                field for field, value in filters
                if value is not None
            ]
            return {
                "status": "NEEDS_CLARIFICATION",
                "candidate_procedures": [],
                "differing_fields": conflicting,
                "clarification_questions": [
                    "The selected calculator conflicts with the supplied study design; "
                    "confirm the calculator or revise the conflicting design fields."
                ],
                "reason_codes": ["CALCULATOR_STUDY_CONFLICT"],
            }
        all_items = data["procedures"]
        scored = []
        for item in all_items:
            score = int(item["operation"] == selection_operation) + int(requested_code is not None and item["outcome_code"] == requested_code)
            scored.append((score, item))
        closest = [_candidate_view(x) for _, x in sorted(scored, key=lambda pair: (-pair[0], pair[1]["public_id"]))[:5]]
        return {
            "status": "UNSUPPORTED",
            "unsupported_reason": "No validated public procedure satisfies all hard constraints.",
            "closest_related_procedures": closest,
            "missing_capability": [f"{field}={value}" for field, value in filters if value is not None],
            "reason_codes": ["NO_VALIDATED_PROCEDURE"],
        }

    if len(candidates) == 1 and not validation["unsafe_inferences"]:
        item = candidates[0]
        selected = {
            "status": "SELECTED", "selected_procedure_key": item["procedure_key"],
            "selected_public_id": item["public_id"], "engine_id": item["engine_id"],
            "selection_reasons": reasons or ["explicit identifier resolved uniquely"],
            "missing_calculation_inputs": _missing_inputs(item, spec),
            "calculation_target": spec.get("calculation_target", "required_sample_size"),
            "defaults_applied": spec.get("defaults_applied", []),
        }
        selected["multiplicity_applicability"] = "not_applicable" if multi_structure == "single_omnibus_hypothesis" else ("applicable" if multi_structure == "multiple_confirmatory_comparisons" else "exploratory" if multi_structure == "exploratory_comparisons" else None)
        selected["multiplicity_strategy"] = None if multi_structure == "single_omnibus_hypothesis" else strategy
        selected["warnings"] = routing_warnings
        return selected

    reason_codes = []
    questions = []
    differing = []
    if validation["unsafe_inferences"]:
        reason_codes.append("CRITICAL_VALUE_INFERRED")
        differing.extend(validation["unsafe_inferences"])
        questions.extend([f"Please explicitly provide or confirm {field}; it cannot be inferred." for field in validation["unsafe_inferences"]])
    if len(candidates) > 1:
        reason_codes.append("MULTIPLE_PROCEDURES_REMAIN")
        for field in ["design_type", "hypothesis_objective", "effect_measure", "analysis_method", "paired_or_independent"]:
            values = {x["selection_profile"].get(field) for x in candidates}
            if len(values) > 1:
                differing.append(field)
        if differing:
            field = next((x for x in differing if x not in validation["unsafe_inferences"]), differing[0])
            values = sorted({str(x["selection_profile"].get(field)) for x in candidates})
            questions.append(f"Which {field} applies: {', '.join(values)}?")
    common_missing = _common_missing_inputs(candidates, spec) if len(candidates) > 1 else []
    questions.extend(f"Please provide {name}." for name in common_missing)
    return {
        "status": "NEEDS_CLARIFICATION",
        "candidate_procedures": [_candidate_view(x) for x in candidates],
        "differing_fields": list(dict.fromkeys(differing)),
        "clarification_questions": questions[:max(1, min(3, len(questions)))],
        "common_missing_calculation_inputs": common_missing,
        "reason_codes": reason_codes or ["INSUFFICIENT_SELECTION_INFORMATION"],
    }


def select(spec: dict) -> dict:
    """Compatibility entry point for StudySpec v1 inputs."""
    return select_prepared(apply_defaults(normalize_spec(spec)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-spec", required=True, type=Path)
    args = parser.parse_args()
    spec = json.loads(args.study_spec.read_text(encoding="utf-8-sig"))
    emit(select(spec))


if __name__ == "__main__":
    main()
