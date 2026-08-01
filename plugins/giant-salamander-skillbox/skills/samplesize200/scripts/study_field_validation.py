from __future__ import annotations

import copy
import math
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


_SKILL_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _SKILL_ROOT / "vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))
import yaml

from study_contract import study_field_contract


CATALOG_PATH = _SKILL_ROOT / "references" / "procedure_catalog.yaml"


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _equivalent(left: Any, right: Any) -> bool:
    if (
        isinstance(left, (int, float)) and not isinstance(left, bool)
        and isinstance(right, (int, float)) and not isinstance(right, bool)
    ):
        return math.isclose(float(left), float(right), rel_tol=0, abs_tol=1e-12)
    return left == right


def _type_matches(value: Any, declared: list[str]) -> bool:
    checks = {
        "null": lambda item: item is None,
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "string": lambda item: isinstance(item, str),
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
    }
    return any(checks[name](value) for name in declared)


def _constraint_errors(value: Any, constraints: dict[str, Any]) -> list[str]:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return []
    result = []
    numeric = float(value)
    for name in ("minimum", "target_minimum"):
        if constraints.get(name) is not None and numeric < float(constraints[name]):
            result.append(name)
    for name in ("exclusive_minimum", "number_exclusive_minimum"):
        if constraints.get(name) is not None and numeric <= float(constraints[name]):
            result.append(name)
    if constraints.get("maximum") is not None and numeric > float(constraints["maximum"]):
        result.append("maximum")
    if constraints.get("exclusive_maximum") is not None and numeric >= float(constraints["exclusive_maximum"]):
        result.append("exclusive_maximum")
    return result


def _get(document: dict[str, Any], pointer: str) -> tuple[bool, Any]:
    current: Any = document
    for token in pointer.strip("/").split("/"):
        if not isinstance(current, dict) or token not in current:
            return False, None
        current = current[token]
    return True, current


def _set(document: dict[str, Any], pointer: str, value: Any) -> None:
    tokens = pointer.strip("/").split("/")
    current = document
    for token in tokens[:-1]:
        current = current.setdefault(token, {})
    current[tokens[-1]] = copy.deepcopy(value)


def _remove(document: dict[str, Any], pointer: str) -> None:
    tokens = pointer.strip("/").split("/")
    current: Any = document
    for token in tokens[:-1]:
        if not isinstance(current, dict) or token not in current:
            return
        current = current[token]
    if isinstance(current, dict):
        current.pop(tokens[-1], None)


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    return yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8-sig"))


@lru_cache(maxsize=1)
def _procedures() -> tuple[dict[str, Any], ...]:
    return tuple(_catalog()["procedures"])


def _bound_procedure(request: dict[str, Any] | None) -> dict[str, Any] | None:
    request = request or {}
    for item in _procedures():
        if (
            request.get("procedure_key") == item.get("procedure_key")
            or request.get("catalog_procedure_id") == item.get("public_id")
            or request.get("engine_procedure_id") == item.get("engine_id")
        ):
            return item
    return None


@lru_cache(maxsize=1)
def _design_projections() -> dict[str, dict[str, set[Any]]]:
    result: dict[str, dict[str, set[Any]]] = {}
    for item in _procedures():
        profile = item.get("selection_profile") or {}
        design = profile.get("design_type")
        if design is None:
            continue
        target = result.setdefault(str(design), {
            "clustered": set(), "repeated_measures": set(),
            "paired_or_independent": set(),
        })
        for field in target:
            if profile.get(field) is not None:
                target[field].add(profile[field])
    return result


def normalize_study_spec_fields(
    study_spec: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize declared aliases and compatibility locations without selecting a procedure."""
    result = copy.deepcopy(study_spec)
    result.setdefault("study", {})
    result.setdefault("values", {})
    result.setdefault("provenance", {})
    normalizations: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if not isinstance(result["study"], dict) or not isinstance(result["values"], dict):
        return result, normalizations, [{
            "code": "STUDY_FIELD_CONTAINER_INVALID", "field": "study_spec",
            "message": "study and values must be objects",
        }]

    contract = study_field_contract()
    accept_compatibility_locations = bool(
        (contract.get("policy") or {}).get("reader_accepts_compatibility_locations")
    )
    for name, rule in contract["study_fields"].items():
        canonical = str(rule["canonical_location"])
        if accept_compatibility_locations and rule["status"] != "deprecated_umbrella":
            for compatibility in rule.get("compatibility_locations") or []:
                if compatibility == canonical:
                    continue
                old_present, old_value = _get(result, compatibility)
                if not old_present:
                    continue
                new_present, new_value = _get(result, canonical)
                if new_present and not _equivalent(old_value, new_value):
                    errors.append({
                        "code": "DUPLICATE_LOCATION_CONFLICT", "field": name,
                        "canonical_path": canonical, "compatibility_path": compatibility,
                        "canonical_value": copy.deepcopy(new_value),
                        "compatibility_value": copy.deepcopy(old_value),
                        "message": f"conflicting canonical and compatibility values for {name}",
                    })
                    continue
                if not new_present:
                    _set(result, canonical, old_value)
                _remove(result, compatibility)
                if canonical.startswith("/values/"):
                    pointer = f"/values/{_pointer_token(name)}"
                    result["provenance"].setdefault(pointer, {
                        "source": "imported_legacy", "compatibility_path": compatibility,
                    })
                normalizations.append({
                    "code": "COMPATIBILITY_LOCATION_NORMALIZED", "field": name,
                    "from": compatibility, "to": canonical,
                })

        present, value = _get(result, canonical)
        aliases = rule.get("normalization_aliases") or {}
        if present and isinstance(value, str) and value in aliases:
            normalized = aliases[value]
            _set(result, canonical, normalized)
            normalizations.append({
                "code": "STUDY_FIELD_ALIAS_NORMALIZED", "field": name,
                "from": value, "to": normalized,
            })

    factor_aliases = (
        result["values"].get("factor_a_levels"),
        result["values"].get("factor_b_levels"),
    )
    if accept_compatibility_locations and all(
        isinstance(value, int) and not isinstance(value, bool) for value in factor_aliases
    ):
        factor_levels = list(factor_aliases)
        existing = result["study"].get("factor_levels")
        if existing is not None and existing != factor_levels:
            errors.append({
                "code": "DUPLICATE_LOCATION_CONFLICT", "field": "factor_levels",
                "canonical_path": "/study/factor_levels",
                "compatibility_path": "/values/factor_a_levels+/values/factor_b_levels",
                "canonical_value": copy.deepcopy(existing),
                "compatibility_value": factor_levels,
                "message": "factor level aliases conflict with canonical factor_levels",
            })
        else:
            result["study"]["factor_levels"] = factor_levels
            result["values"].pop("factor_a_levels", None)
            result["values"].pop("factor_b_levels", None)
            result["provenance"].pop("/values/factor_a_levels", None)
            result["provenance"].pop("/values/factor_b_levels", None)
            normalizations.append({
                "code": "FACTOR_LEVEL_ALIASES_NORMALIZED",
                "from": ["/values/factor_a_levels", "/values/factor_b_levels"],
                "to": "/study/factor_levels",
            })
    return result, normalizations, errors


def _field_error(code: str, field: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "field": field, "message": message, **details}


def validate_study_spec_fields(
    study_spec: dict[str, Any], calculation_request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate StudySpec ownership and cross-field semantics before selection."""
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    contract = study_field_contract()
    study = study_spec.get("study")
    values = study_spec.get("values")
    if not isinstance(study, dict) or not isinstance(values, dict):
        return {
            "valid": False,
            "errors": [_field_error(
                "STUDY_FIELD_CONTAINER_INVALID", "study_spec",
                "study and values must be objects",
            )],
            "warnings": [],
        }

    declared_study = contract["study_fields"]
    for name in sorted(set(study) - set(declared_study)):
        errors.append(_field_error(
            "UNKNOWN_STUDY_FIELD", name, f"unknown StudySpec.study field: {name}",
            path=f"/study/{name}",
        ))

    for name, value in study.items():
        rule = declared_study.get(name)
        if rule is None:
            continue
        if not _type_matches(value, rule["data_type"]):
            errors.append(_field_error(
                "STUDY_FIELD_TYPE_INVALID", name, f"invalid type for {name}",
                path=f"/study/{name}", expected=rule["data_type"],
            ))
            continue
        allowed = rule.get("allowed_values")
        if allowed is not None and value not in allowed:
            target = warnings if rule["status"] == "canonical_transitional" else errors
            target.append(_field_error(
                "STUDY_FIELD_VALUE_NONCANONICAL" if target is warnings else "STUDY_FIELD_VALUE_INVALID",
                name, f"value is outside the declared vocabulary for {name}",
                path=f"/study/{name}", value=copy.deepcopy(value),
            ))
        failed = _constraint_errors(value, rule.get("constraints") or {})
        if failed:
            errors.append(_field_error(
                "STUDY_FIELD_RANGE_INVALID", name, f"value is outside the allowed range for {name}",
                path=f"/study/{name}", failed_constraints=failed,
            ))

    common = contract["values_namespace"]["common_fields"]
    for name, rule in common.items():
        if name not in values:
            continue
        value = values[name]
        if not _type_matches(value, rule["data_type"]):
            errors.append(_field_error(
                "STUDY_VALUE_TYPE_INVALID", name, f"invalid type for {name}",
                path=f"/values/{name}", expected=rule["data_type"],
            ))
            continue
        allowed = rule.get("allowed_values")
        if allowed is not None and value not in allowed:
            target = warnings if rule["status"] == "canonical_transitional" else errors
            target.append(_field_error(
                "STUDY_VALUE_NONCANONICAL" if target is warnings else "STUDY_VALUE_INVALID",
                name, f"value is outside the declared vocabulary for {name}",
                path=f"/values/{name}", value=copy.deepcopy(value),
            ))
        failed = _constraint_errors(value, rule.get("constraints") or {})
        if failed:
            errors.append(_field_error(
                "STUDY_VALUE_RANGE_INVALID", name, f"value is outside the allowed range for {name}",
                path=f"/values/{name}", failed_constraints=failed,
            ))

    design = study.get("design_type")
    projection = _design_projections().get(str(design), {}) if design is not None else {}
    for field, observed in projection.items():
        if field in study and len(observed) == 1 and study[field] not in observed:
            errors.append(_field_error(
                f"DESIGN_{field.upper()}_CONFLICT", field,
                f"{field} conflicts with design_type {design}",
                path=f"/study/{field}", design_type=design,
                expected=copy.deepcopy(next(iter(observed))), actual=copy.deepcopy(study[field]),
            ))

    procedure = _bound_procedure(calculation_request)
    if procedure is not None:
        profile = procedure.get("selection_profile") or {}
        if study.get("outcome_code") is not None and study["outcome_code"] != profile.get("outcome_code"):
            errors.append(_field_error(
                "OUTCOME_CODE_CONFLICT", "outcome_code",
                "outcome_code conflicts with the bound catalog procedure",
                path="/study/outcome_code", expected=profile.get("outcome_code"),
                actual=study.get("outcome_code"),
            ))
        requested_method = study.get("analysis_method")
        if requested_method and requested_method in {
            procedure.get("public_id"), procedure.get("engine_id"), procedure.get("procedure_key"),
        } and requested_method != profile.get("analysis_method"):
            errors.append(_field_error(
                "ANALYSIS_METHOD_BINDING_CONFLICT", "analysis_method",
                "analysis_method conflicts with the bound catalog procedure",
                path="/study/analysis_method",
            ))

    return {"valid": not errors, "errors": errors, "warnings": warnings}
