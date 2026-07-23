from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit


MODES = {"CALCULATE", "STATISTICIAN", "TEACHER", "REVIEWER"}
MODE_SYNONYMS = {
    "calc": "CALCULATE",
    "calculate": "CALCULATE",
    "calculation": "CALCULATE",
    "compute": "CALCULATE",
    "stat": "STATISTICIAN",
    "statistic": "STATISTICIAN",
    "statistician": "STATISTICIAN",
    "teacher": "TEACHER",
    "teach": "TEACHER",
    "explore": "TEACHER",
    "review": "REVIEWER",
    "reviewer": "REVIEWER",
    "guided": "CALCULATE",
    "explicit": "CALCULATE",
}
OPERATIONS = {"SAMPLE_SIZE", "POWER", "REQUIRED_CLUSTER_SIZE"}
CALCULATION_TARGETS = {
    "power", "required_events", "required_sample_size",
    "attrition_adjusted_sample_size", "detectable_effect",
}
REQUESTED_OUTPUTS = {
    "required_sample_size", "required_events", "required_cluster_size",
    "attrition_adjusted_sample_size", "achieved_power", "detectable_effect",
}
MULTI_STRUCTURES = {"single_omnibus_hypothesis", "multiple_confirmatory_comparisons", "exploratory_comparisons", "unknown"}
CRITICAL_TERMS = {
    "effect", "difference", "ratio", "odds_ratio", "hazard_ratio", "control_proportion",
    "standard_proportion", "reference_proportion", "standard_deviation", "variance", "margin",
    "boundary", "sidedness", "sides", "hypothesis_objective", "allocation", "allocation_ratio",
    "icc", "attrition", "multiplicity", "alpha", "power", "target_power",
}


def _normalized_mode(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token:
        return None
    upper = token.upper()
    if upper in MODES:
        return upper
    return MODE_SYNONYMS.get(token.lower())


def _critical(name: str) -> bool:
    lowered = name.lower()
    return any(term in lowered for term in CRITICAL_TERMS)


def validate_spec(spec: object) -> dict:
    errors = []
    if not isinstance(spec, dict):
        return {"valid": False, "structural_errors": ["StudySpec must be an object"], "unsafe_inferences": []}
    for key in ["requested_mode", "operation", "user_provided_values", "inferred_values", "missing_required_fields", "uncertain_fields"]:
        if key not in spec:
            errors.append(f"missing required StudySpec field: {key}")
    normalized_mode = _normalized_mode(spec.get("requested_mode"))
    if normalized_mode is None:
        errors.append("requested_mode must be CALCULATE, STATISTICIAN, TEACHER, or REVIEWER")
    else:
        spec["requested_mode"] = normalized_mode
    if spec.get("operation") not in OPERATIONS:
        errors.append("operation must be SAMPLE_SIZE, POWER, or REQUIRED_CLUSTER_SIZE")
    target = spec.get("calculation_target", "required_sample_size")
    if target not in CALCULATION_TARGETS:
        errors.append("calculation_target is invalid")
    if spec.get("requested_output") not in ({None} | REQUESTED_OUTPUTS):
        errors.append("requested_output is invalid")
    for key in ["user_provided_values", "inferred_values"]:
        if key in spec and not isinstance(spec[key], dict):
            errors.append(f"{key} must be an object")
    for key in ["missing_required_fields", "uncertain_fields"]:
        if key in spec and (not isinstance(spec[key], list) or not all(isinstance(x, str) for x in spec[key])):
            errors.append(f"{key} must be an array of strings")
    for key in ["alpha", "target_power"]:
        value = spec.get(key)
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value < 1):
            errors.append(f"{key} must be strictly between 0 and 1")
    for key in ["censoring_probability", "standard_censoring_probability", "treatment_censoring_probability"]:
        value = spec.get(key)
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value < 1):
            errors.append(f"{key} must be in [0, 1)")
    if spec.get("outcome_code") not in {None, "C", "B", "R", "S", "O", "N"}:
        errors.append("outcome_code is not one of C, B, R, S, O, N")
    if spec.get("multi_hypothesis_structure") not in ({None} | MULTI_STRUCTURES):
        errors.append("multi_hypothesis_structure is invalid")
    if spec.get("multiplicity_applicability") not in {None, "applicable", "not_applicable", "unknown"}:
        errors.append("multiplicity_applicability is invalid")
    inferred = spec.get("inferred_values") if isinstance(spec.get("inferred_values"), dict) else {}
    provided = spec.get("user_provided_values") if isinstance(spec.get("user_provided_values"), dict) else {}
    unsafe = sorted(key for key in inferred if _critical(key) and key not in provided)
    return {
        "valid": not errors,
        "structural_errors": errors,
        "unsafe_inferences": unsafe,
        "requires_user_confirmation": bool(unsafe),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-spec", required=True, type=Path)
    args = parser.parse_args()
    try:
        spec = json.loads(args.study_spec.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        emit({"valid": False, "structural_errors": [str(exc)], "unsafe_inferences": []})
        raise SystemExit(2)
    result = validate_spec(spec)
    emit(result)
    raise SystemExit(0 if result["valid"] else 2)


if __name__ == "__main__":
    main()
