from __future__ import annotations

import copy
import math
from typing import Any

from naming_contract import normalize_naming_aliases


PAIRED_TERMS = ("paired", "matched", "same subjects", "same subject", "対応あり", "対応のある", "同一被験者", "同じ被験者")
INDEPENDENT_TERMS = (
    "independent", "unpaired", "different subjects", "separate subjects", "independent samples",
    "two independent groups", "独立した2群", "非対応デザイン", "対応なし", "対応のない", "別々の被験者", "異なる被験者", "独立",
)


GLOBAL_ALIASES = {
    "alpha": ("alpha",),
    "target_power": ("target_power", "power"),
    "sidedness": ("sidedness", "sides"),
    "allocation": ("allocation", "allocation_ratio"),
}
ENGINE_FIELD_NAMES = {
    "target_power": "power",
    "sidedness": "sides",
    "allocation": "allocation_ratio",
}
TRACKED_TOP_LEVEL_FIELDS = (
    "requested_public_id", "requested_engine_id", "requested_procedure_key",
    "calculator_id", "catalog_procedure_id", "engine_procedure_id", "procedure_key",
    "requested_output", "confidence_interval_method", "width_definition", "calculation_target",
)
OUTCOME_TYPE_ALIASES = {
    "survival": "time_to_event", "time-to-event": "time_to_event",
    "time_to_event": "time_to_event", "competing-risk": "competing_risk",
    "competing risk": "competing_risk", "competing_risk": "competing_risk",
}
ANALYSIS_METHOD_ALIASES = {
    "schoenfeld": "schoenfeld", "freedman": "freedman",
    "cause-specific hazard": "cause_specific_hazard",
    "cause_specific_hazard": "cause_specific_hazard",
    "fixed-censoring subdistribution": "subdistribution_fixed_censoring",
    "subdistribution_fixed_censoring": "subdistribution_fixed_censoring",
    "accrual-integrated subdistribution": "subdistribution_accrual_integration",
    "subdistribution_accrual_integration": "subdistribution_accrual_integration",
}
LOCKED_CONVERSATION_FIELDS = {
    "planned_ratio", "coefficient_of_variation", "within_subject_log_sd",
    "lower_boundary", "upper_boundary", "alpha", "target_power", "sidedness",
    "allocation", "number_of_groups", "design_type", "hypothesis_objective",
}


def _equivalent(left: Any, right: Any) -> bool:
    if isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(right, (int, float)) and not isinstance(right, bool):
        return math.isclose(float(left), float(right), rel_tol=0, abs_tol=1e-12)
    return left == right


def engine_field_name(name: str) -> str:
    for canonical, aliases in GLOBAL_ALIASES.items():
        if name == canonical or name in aliases:
            return ENGINE_FIELD_NAMES.get(canonical, canonical)
    return name


def _deep_merge(previous: Any, incoming: Any) -> Any:
    if isinstance(previous, dict) and isinstance(incoming, dict):
        merged = copy.deepcopy(previous)
        for key, value in incoming.items():
            merged[key] = _deep_merge(merged[key], value) if key in merged else copy.deepcopy(value)
        return merged
    return copy.deepcopy(incoming)


def _field_value(spec: dict[str, Any], key: str) -> Any:
    if spec.get(key) is not None:
        return spec[key]
    for container in ("user_provided_values", "effect_assumptions", "nuisance_parameters", "attrition_assumptions"):
        values = spec.get(container)
        if isinstance(values, dict) and values.get(key) is not None:
            return values[key]
    return None


def _set_field_value(spec: dict[str, Any], key: str, value: Any, source: dict[str, Any]) -> None:
    if key in source and source.get(key) is not None:
        spec[key] = copy.deepcopy(value)
        return
    for container in ("user_provided_values", "effect_assumptions", "nuisance_parameters", "attrition_assumptions"):
        values = source.get(container)
        if isinstance(values, dict) and key in values:
            spec.setdefault(container, {})[key] = copy.deepcopy(value)
            return
    spec[key] = copy.deepcopy(value)


def normalize_pairing(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"paired", "independent", "not_applicable_or_method_specific"}:
        return text
    if any(term in text for term in INDEPENDENT_TERMS):
        return "independent"
    if any(term in text for term in PAIRED_TERMS):
        return "paired"
    return None


def normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_naming_aliases(copy.deepcopy(spec))
    if normalized.get("outcome_type") is not None:
        text = str(normalized["outcome_type"]).strip().lower()
        normalized["outcome_type"] = OUTCOME_TYPE_ALIASES.get(text, normalized["outcome_type"])
    if normalized.get("analysis_method") is not None:
        text = str(normalized["analysis_method"]).strip().lower()
        normalized["analysis_method"] = ANALYSIS_METHOD_ALIASES.get(text, normalized["analysis_method"])
    raw = normalized.get("paired_or_independent") or normalized.get("design_description")
    pairing = normalize_pairing(raw)
    if pairing is not None:
        normalized["paired_or_independent"] = pairing

    user = normalized.get("user_provided_values")
    if not isinstance(user, dict):
        user = {}
    else:
        user = copy.deepcopy(user)
    sources = copy.deepcopy(normalized.get("value_sources") or {})
    conflicts = copy.deepcopy(normalized.get("input_conflicts") or [])
    old_defaults = normalized.get("defaulted_values") if isinstance(normalized.get("defaulted_values"), dict) else {}

    default_targets = {
        "procedure": "requested_public_id",
        "confidence_interval_method": "confidence_interval_method",
        "width_definition": "width_definition",
    }
    for key in TRACKED_TOP_LEVEL_FIELDS:
        was_defaulted = any(default_targets.get(name, name) == key for name in old_defaults)
        if normalized.get(key) is not None and key not in sources and not was_defaulted:
            sources[key] = "explicit_current"

    for canonical, aliases in GLOBAL_ALIASES.items():
        candidates = [(name, user[name]) for name in aliases if user.get(name) is not None]
        if len(candidates) > 1:
            first_name, first_value = candidates[0]
            for name, value in candidates[1:]:
                if not _equivalent(first_value, value):
                    conflicts.append({
                        "field": canonical,
                        "values": {first_name: first_value, name: value},
                    })
        nested_value = candidates[-1][1] if candidates else None
        top_value = normalized.get(canonical)
        default_name = ENGINE_FIELD_NAMES.get(canonical, canonical)
        top_is_default = sources.get(canonical) == "default" or default_name in old_defaults
        if nested_value is not None:
            if top_value is not None and not top_is_default and not _equivalent(top_value, nested_value):
                conflicts.append({
                    "field": canonical,
                    "values": {canonical: top_value, candidates[-1][0]: nested_value},
                })
            normalized[canonical] = nested_value
            sources[canonical] = "explicit_current"
        elif top_value is not None and canonical not in sources:
            # A top-level side count can be produced by the language parser.  It
            # is not evidence that the user explicitly requested that side.
            # Keep its provenance distinct so the default policy can safely
            # correct an unsupported inferred two-sided value for one-group work.
            sources[canonical] = "unattributed" if canonical == "sidedness" else "explicit_current"
        for name in aliases:
            user.pop(name, None)

    nested_scenarios = user.pop("power_scenarios", None)
    if nested_scenarios is not None:
        top_scenarios = normalized.get("power_scenarios")
        if top_scenarios is not None and top_scenarios != nested_scenarios:
            conflicts.append({
                "field": "power_scenarios",
                "values": {"power_scenarios": top_scenarios, "user_provided_values.power_scenarios": nested_scenarios},
            })
        normalized["power_scenarios"] = copy.deepcopy(nested_scenarios)
        sources["power_scenarios"] = "explicit_current"
    elif "power_scenarios" in normalized and "power_scenarios" not in sources:
        sources["power_scenarios"] = "explicit_current"

    normalized["user_provided_values"] = user
    inferred = normalized.get("inferred_values") if isinstance(normalized.get("inferred_values"), dict) else {}
    for key in user:
        sources.setdefault(key, "explicit_current")
    for container in ("effect_assumptions", "nuisance_parameters", "attrition_assumptions"):
        payload = normalized.get(container)
        if isinstance(payload, dict):
            for key in payload:
                sources.setdefault(key, "inferred" if key in inferred else "explicit_current")
    for key in inferred:
        sources.setdefault(key, "inferred")
    normalized["value_sources"] = sources
    normalized["input_conflicts"] = conflicts
    return normalized


def merge_specs(previous: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge conversation state while preserving nested explicit values and provenance."""
    prior = normalize_spec(previous)
    current = normalize_spec(incoming)
    merged = _deep_merge(prior, current)

    prior_sources = {
        key: ("explicit_previous" if str(value).startswith("explicit") else value)
        for key, value in (prior.get("value_sources") or {}).items()
    }
    sources = {**prior_sources, **(current.get("value_sources") or {})}
    for canonical in GLOBAL_ALIASES:
        if str((current.get("value_sources") or {}).get(canonical, "")).startswith("explicit"):
            merged[canonical] = current[canonical]
    if str((current.get("value_sources") or {}).get("power_scenarios", "")).startswith("explicit"):
        merged["power_scenarios"] = copy.deepcopy(current["power_scenarios"])

    merged["value_sources"] = sources
    current_conflicts = copy.deepcopy(current.get("input_conflicts") or [])
    explicitly_updated = {
        key for key, value in (current.get("value_sources") or {}).items()
        if str(value).startswith("explicit")
    }
    unresolved_prior_conflicts = [
        conflict for conflict in (prior.get("input_conflicts") or [])
        if conflict.get("field") not in explicitly_updated
    ]
    merged["input_conflicts"] = [*unresolved_prior_conflicts, *current_conflicts]

    # Values that were explicitly supplied in an earlier turn are locked.  A
    # language parser must mark a direct user revision in `explicit_updates`;
    # otherwise an inferred or template value may neither overwrite it nor be
    # silently used for calculation.
    explicit_updates = set(current.get("explicit_updates") or [])
    for field in LOCKED_CONVERSATION_FIELDS:
        prior_value = _field_value(prior, field)
        current_value = _field_value(current, field)
        prior_source = str((prior.get("value_sources") or {}).get(field) or "")
        if (
            prior_value is not None and current_value is not None
            and not _equivalent(prior_value, current_value)
            and prior_source.startswith("explicit")
            and field not in explicit_updates
        ):
            _set_field_value(merged, field, prior_value, prior)
            merged["value_sources"][field] = "explicit_previous"
            merged["input_conflicts"].append({
                "field": field,
                "code": "EXPLICIT_VALUE_REPLACEMENT_REQUIRES_CONFIRMATION",
                "previous_value": prior_value,
                "incoming_value": current_value,
            })
    return merged
