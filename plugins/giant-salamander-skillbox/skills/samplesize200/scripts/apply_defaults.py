from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import default_policy, emit
from normalize_study_spec import normalize_spec


DIRECTIONAL_JA = (
    "超える", "高い", "上回る", "下回る", "低い",
    "改善する", "減少する", "少なくとも",
)
NONDIRECTIONAL_JA = ("異なるか", "差があるか", "等しくないか")
POLICY = default_policy()
EXCEPTION_TOKENS = tuple(POLICY["exceptions"]["objective_tokens"])
POWER_VALUES = list(POLICY["defaults"]["power_values"])
DEFAULT_ALPHA = float(POLICY["defaults"]["alpha"])
DEFAULT_ALLOCATION = float(POLICY["defaults"]["two_group_allocation_ratio"])
DEFAULT_FIELD_TARGETS = {
    "alpha": "alpha",
    "power": "target_power",
    "sides": "sidedness",
    "allocation_ratio": "allocation",
    "procedure": "requested_public_id",
    "confidence_interval_method": "confidence_interval_method",
    "width_definition": "width_definition",
}


def _record(spec: dict[str, Any], field: str, value: Any, rule: str) -> None:
    if field in spec.setdefault("defaulted_values", {}):
        return
    spec.setdefault("defaulted_values", {})[field] = value
    spec.setdefault("defaults_applied", []).append({"field": field, "value": value, "rule": rule})
    spec.setdefault("value_sources", {})[DEFAULT_FIELD_TARGETS.get(field, field)] = "default"


def _clear_previous_defaults(spec: dict[str, Any]) -> None:
    previous = spec.get("defaulted_values") if isinstance(spec.get("defaulted_values"), dict) else {}
    sources = spec.setdefault("value_sources", {})
    for field in previous:
        target = DEFAULT_FIELD_TARGETS.get(field, field)
        if sources.get(target) == "default":
            spec.pop(target, None)
            sources.pop(target, None)
        if field == "power" and sources.get("power_scenarios") != "explicit_current":
            spec.pop("power_scenarios", None)
            sources.pop("power_scenarios", None)
    spec["defaulted_values"] = {}
    spec["defaults_applied"] = []


def _direction(spec: dict[str, Any]) -> str | None:
    if spec.get("directionality") in {"directional", "nondirectional"}:
        return spec["directionality"]
    text = str(spec.get("input_summary") or "")
    if any(term in text for term in DIRECTIONAL_JA):
        return "directional"
    if any(term in text for term in NONDIRECTIONAL_JA):
        return "nondirectional"
    return None


def _exception(spec: dict[str, Any]) -> bool:
    objective = str(spec.get("hypothesis_objective") or "").lower()
    if any(token in objective for token in EXCEPTION_TOKENS):
        return True
    if spec.get("multi_hypothesis_structure") == "multiple_confirmatory_comparisons":
        return True
    return False


def _has_explicit_sidedness(spec: dict[str, Any]) -> bool:
    """Return whether the side count is traceable to a user instruction."""
    source = str((spec.get("value_sources") or {}).get("sidedness") or "")
    return source.startswith("explicit")


def _has_explicit_nondirectional_text(spec: dict[str, Any]) -> bool:
    text = str(spec.get("input_summary") or "")
    source = str((spec.get("value_sources") or {}).get("directionality") or "")
    return source.startswith("explicit") or any(term in text for term in NONDIRECTIONAL_JA)


def apply_defaults(spec: dict[str, Any]) -> dict[str, Any]:
    result = normalize_spec(copy.deepcopy(spec))
    _clear_previous_defaults(result)
    if result.get("operation") == "POWER":
        result["calculation_target"] = "power"
    elif result.get("calculation_target") is None:
        result["calculation_target"] = "required_sample_size"
    user = result.get("user_provided_values") if isinstance(result.get("user_provided_values"), dict) else {}

    # A standardized repeated-measures effect is only an input shorthand. The
    # selected procedure still tests the registered post-intervention mean contrast.
    if result.get("requested_public_id") == "TWO-C-009" and result.get("effect_measure") in {
        "standardized_effect", "standardized_mean_difference"
    }:
        result["effect_measure"] = "post_intervention_mean_difference"
        effects = result.get("effect_assumptions") if isinstance(result.get("effect_assumptions"), dict) else {}
        standardized = user.get("standardized_effect", effects.get("standardized_effect"))
        if standardized is not None:
            _record(result, "planned_mean_difference", standardized, "standardized effect numerator")
            _record(result, "planned_sd", 1.0, "standardized effect reference SD")
        _record(result, "pre_measurements", 0, "no pre-intervention measurements were requested")
        result.setdefault("derived_input_mappings", []).append({
            "source": "standardized_effect", "targets": ["planned_mean_difference", "planned_sd"],
            "rule": "planned_mean_difference = standardized_effect and planned_sd = 1",
        })

    # Confidence-interval precision is not a power design. Wilson and full width
    # are transparent method/definition defaults, not inferred study values.
    precision = result.get("hypothesis_objective") == "precision_estimation"
    one_binary = result.get("number_of_groups") == 1 and (
        result.get("outcome_type") in {"binary", "proportion", "proportion_or_mean"}
        or (
            result.get("outcome_code") == "B"
            and result.get("design_type") in {None, "one_group"}
        )
    )
    if precision and one_binary:
        method = str(result.get("confidence_interval_method") or "").lower()
        if not method or method == "wilson":
            result["requested_public_id"] = "CI-B-003"
            _record(result, "confidence_interval_method", "Wilson", "one-group proportion CI-width default")
        elif method in {"wald", "normal", "normal_approximation", "正規近似"}:
            result["requested_public_id"] = "CI-B-001"
        else:
            result["unsupported_method_request"] = result.get("confidence_interval_method")
        if not result.get("width_definition"):
            result["width_definition"] = "full_width"
            _record(result, "width_definition", "full_width", "CI width means upper minus lower")
        if result.get("confidence_level") is not None and result.get("alpha") is None:
            result["alpha"] = 1.0 - float(result["confidence_level"])
            _record(result, "alpha", result["alpha"], "alpha = 1 - confidence level")
        result["power_scenarios"] = []
        result.setdefault("value_sources", {})["power_scenarios"] = "not_applicable"
        return result

    if (
        one_binary
        and result.get("hypothesis_objective") in {None, "superiority_hypothesis_test"}
        and ("known_proportion" in user or result.get("effect_measure") in {None, "risk_difference"})
        and not any(result.get(key) for key in ("requested_public_id", "requested_engine_id", "requested_procedure_key"))
    ):
        result["requested_public_id"] = "ONE-B-001"
        _record(result, "procedure", "ONE-B-001", "one-group proportion comparison with a known reference")

    if (
        result.get("number_of_groups") == 1
        and result.get("outcome_type") in {"survival", "time_to_event"}
        and {"null_survival_probability", "alternative_survival_probability"}.issubset(user)
        and not any(result.get(key) for key in ("requested_public_id", "requested_engine_id", "requested_procedure_key"))
    ):
        result["requested_public_id"] = "ONE-S-001"
        result["effect_measure"] = "arcsine_square_root_survival_difference"
        result.setdefault("design_type", "one_sample_survival_probability")
        result.setdefault("repeated_measures", False)
        _record(result, "procedure", "ONE-S-001", "one-group fixed-time Kaplan-Meier survival probability")

    # Event count is a complete upstream target. The method is defaulted only for
    # a proportional-hazards request and never overrides an explicit method.
    if (
        result.get("calculation_target") == "required_events"
        and result.get("effect_measure") in {"hazard_ratio", None}
        and not any(result.get(key) for key in ("requested_public_id", "requested_engine_id", "requested_procedure_key"))
    ):
        result["requested_public_id"] = "TWO-S-001"
        _record(result, "procedure", "TWO-S-001", "default event-count method: Schoenfeld proportional hazards")

    # Conventional independent two-group mean comparison: use the catalogued
    # exact noncentral-t procedure. Effect and variance inputs remain mandatory.
    if (
        result.get("number_of_groups") == 2
        and result.get("outcome_type") in {"continuous", "mean"}
        and result.get("design_type") in {None, "independent", "independent_two_group"}
        and not result.get("repeated_measures")
        and result.get("hypothesis_objective") in {None, "superiority_hypothesis_test"}
        and not any(result.get(key) for key in ("requested_public_id", "requested_engine_id", "requested_procedure_key"))
    ):
        result["requested_public_id"] = "TWO-C-002"
        _record(result, "procedure", "TWO-C-002", "default exact two-sample noncentral-t procedure")

    groups = result.get("number_of_groups")
    if groups == 2 and result.get("allocation") is None and result.get("calculation_target") != "power":
        result["allocation"] = DEFAULT_ALLOCATION
        _record(result, "allocation_ratio", DEFAULT_ALLOCATION, "equal allocation default")

    achieved_power = result.get("calculation_target") == "power"
    if achieved_power:
        result["operation"] = "POWER"
        result["power_scenarios"] = []
        result.setdefault("value_sources", {})["power_scenarios"] = "not_applicable"

    if (
        result.get("hypothesis_objective") == "precision_estimation"
        or str(result.get("requested_public_id") or "").startswith("CI-")
    ):
        result["power_scenarios"] = []
        result.setdefault("value_sources", {})["power_scenarios"] = "not_applicable"
        return result

    if _exception(result):
        scenarios = result.get("power_scenarios")
        if result.get("value_sources", {}).get("power_scenarios") == "explicit_current" and isinstance(scenarios, list) and scenarios:
            if result.get("target_power") is None:
                result["target_power"] = scenarios[0]
                result.setdefault("value_sources", {})["target_power"] = "derived"
        elif result.get("target_power") is not None:
            result["power_scenarios"] = [float(result["target_power"])]
        else:
            result["power_scenarios"] = []
        return result

    direction = _direction(result)
    if result.get("alpha") is None:
        result["alpha"] = DEFAULT_ALPHA
        _record(result, "alpha", DEFAULT_ALPHA, "default significance level")
    # In the natural-language route, an unproven two-sided value may be an
    # inference made by the parser, rather than a user decision.  The benchmark
    # policy for a one-group superiority request with no stated direction is
    # one-sided.  Do not override an explicitly supplied side or an explicit
    # nondirectional phrase.
    inferred_two_sided_one_group = (
        groups == 1
        and result.get("hypothesis_objective") in {None, "superiority_hypothesis_test"}
        and result.get("sidedness") in {2, "two_sided"}
        and not _has_explicit_sidedness(result)
        and not _has_explicit_nondirectional_text(result)
    )
    if inferred_two_sided_one_group:
        result["sidedness"] = None
        result.setdefault("value_sources", {}).pop("sidedness", None)

    if result.get("sidedness") is None:
        if groups == 1 and direction == "directional":
            result["sidedness"] = 1
            _record(result, "sides", 1, "one-group directional hypothesis")
        elif groups == 1 and direction == "nondirectional" and _has_explicit_nondirectional_text(result):
            result["sidedness"] = 2
            _record(result, "sides", 2, "one-group nondirectional hypothesis")
        elif groups == 1 and result.get("hypothesis_objective") in {None, "superiority_hypothesis_test"}:
            result["sidedness"] = 1
            _record(result, "sides", 1, "one-group direction-unspecified benchmark default")
        elif groups == 2 and result.get("hypothesis_objective") in {None, "superiority_hypothesis_test"}:
            result["sidedness"] = 2
            _record(result, "sides", 2, "ordinary two-group superiority comparison")
    if achieved_power:
        return result
    beta = user.get("beta")
    if result.get("target_power") is None and beta is not None:
        result["target_power"] = 1.0 - float(beta)
        result.setdefault("value_sources", {})["target_power"] = "derived"
    scenarios = result.get("power_scenarios")
    if result.get("value_sources", {}).get("power_scenarios") == "explicit_current" and isinstance(scenarios, list) and scenarios:
        if result.get("target_power") is None:
            result["target_power"] = scenarios[0]
            result.setdefault("value_sources", {})["target_power"] = "derived"
    elif result.get("target_power") is None:
        result["power_scenarios"] = list(POWER_VALUES)
        result["target_power"] = POWER_VALUES[0]
        _record(result, "power", list(POWER_VALUES), "default sensitivity set")
    else:
        result["power_scenarios"] = [float(result["target_power"])]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-spec", required=True, type=Path)
    args = parser.parse_args()
    emit(apply_defaults(json.loads(args.study_spec.read_text(encoding="utf-8-sig"))))


if __name__ == "__main__":
    main()
