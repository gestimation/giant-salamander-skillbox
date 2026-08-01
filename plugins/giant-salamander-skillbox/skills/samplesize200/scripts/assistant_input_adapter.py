from __future__ import annotations

import copy
from typing import Any


_NON_USER_METHOD_SOURCES = {"inferred", "policy_default"}
_REPEATED_DESIGN_ALIASES = {"repeated_measures", "longitudinal", "longitudinal_repeated_measures"}
_PAIRED_DESIGN_ALIASES = {"paired", "matched", "paired_or_matched", "matched_pairs"}


def _is_multi_group(value: Any) -> bool:
    return value == "3_or_more" or (
        isinstance(value, int) and not isinstance(value, bool) and value >= 3
    )


def _record(provenance: dict[str, Any], path: str, source: str, reason: str) -> None:
    provenance[path] = {"source": source, "reason": reason}


def adapt_assistant_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize semantic facts produced by the natural-language boundary.

    This adapter is intentionally narrower than the authoritative planner.  It
    never chooses a CalculatorID and never supplies statistical defaults.  It
    only makes deterministic semantic implications explicit and removes a
    non-user method guess when the requested output changes operation.
    """
    result = copy.deepcopy(payload)
    study_spec = result.get("study_spec")
    if not isinstance(study_spec, dict):
        return result
    study = study_spec.get("study")
    values = study_spec.get("values")
    provenance = study_spec.get("provenance")
    if not isinstance(study, dict) or not isinstance(values, dict):
        return result
    if not isinstance(provenance, dict):
        provenance = {}
        study_spec["provenance"] = provenance

    # The language boundary may describe the repeated-measures property as a
    # design type.  StudySpec keeps the boolean property and the two-group
    # canonical design vocabulary separate.
    if (
        study.get("number_of_groups") == 2
        and study.get("design_type") in _REPEATED_DESIGN_ALIASES
    ):
        study["design_type"] = "repeated_measures_two_group"
        study["repeated_measures"] = True
        if study.get("outcome_type") in {"continuous", "mean"}:
            study["outcome_type"] = "repeated_continuous"
        _record(
            provenance, "/study/design_type", "inferred",
            "two-group repeated-measures language normalized to canonical design vocabulary",
        )
        _record(
            provenance, "/study/repeated_measures", "inferred",
            "derived from repeated-measures design language",
        )

    # Paired binary wording identifies the design but not necessarily a valid
    # engine effect parameter.  Normalize the design and remove only the
    # language adapter's non-canonical placeholder so the selector can expose
    # the registered discordant-pair contract and ask for its required facts.
    if (
        study.get("number_of_groups") == 2
        and study.get("paired_or_independent") == "paired"
        and study.get("outcome_type") in {"binary", "paired_binary"}
        and study.get("design_type") in _PAIRED_DESIGN_ALIASES
    ):
        study["design_type"] = "paired_two_group"
        study["outcome_type"] = "paired_binary_ordinal_or_continuous"
        _record(
            provenance, "/study/design_type", "inferred",
            "paired binary language normalized to canonical design vocabulary",
        )
        _record(
            provenance, "/study/outcome_type", "inferred",
            "paired binary language normalized to the registered paired outcome family",
        )
        if study.get("effect_measure") == "matched_binary_difference":
            study.pop("effect_measure")
            provenance.pop("/study/effect_measure", None)

    if _is_multi_group(study.get("number_of_groups")) and study.get("comparison_scope") == "shared_control":
        inferred = {
            "multi_hypothesis_structure": "multiple_confirmatory_comparisons",
            "multiplicity_applicability": "applicable",
        }
        for name, value in inferred.items():
            if study.get(name) is None:
                study[name] = value
                _record(
                    provenance, f"/study/{name}", "inferred",
                    "shared_control implies multiple confirmatory treatment-reference comparisons",
                )
        treatment = values.get("treatment_proportions")
        if isinstance(treatment, list) and treatment and all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in treatment
        ):
            derived = {
                "minimum_treatment_proportion": min(treatment),
                "number_of_treatment_arms": len(treatment),
            }
            for name, value in derived.items():
                if values.get(name) is None:
                    values[name] = value
                    _record(
                        provenance, f"/values/{name}", "derived",
                        "derived from /values/treatment_proportions",
                    )

    requests = result.get("calculation_requests")
    if not isinstance(requests, list):
        single = result.get("calculation_request")
        requests = [single] if isinstance(single, dict) else []
    if any(request.get("requested_output") == "achieved_power" for request in requests):
        method_source = (provenance.get("/study/analysis_method") or {}).get("source")
        if study.get("analysis_method") is not None and method_source in _NON_USER_METHOD_SOURCES:
            study.pop("analysis_method", None)
            provenance.pop("/study/analysis_method", None)

    return result
