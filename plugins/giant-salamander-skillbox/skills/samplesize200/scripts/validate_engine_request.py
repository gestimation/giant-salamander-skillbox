from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import SkillContractError, emit, procedure_input_contract, resolve_procedure


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check_type(value: Any, expected: str) -> bool:
    if expected == "number":
        return _is_number(value)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "string":
        return isinstance(value, str)
    return True


def _range_errors(name: str, value: Any, rule: dict[str, Any] | None) -> list[str]:
    if not rule:
        return []
    if isinstance(value, list):
        errors = []
        for index, element in enumerate(value):
            errors.extend(_range_errors(f"{name}[{index}]", element, rule))
        return errors
    if not _is_number(value):
        return []
    errors: list[str] = []
    minimum = rule.get("minimum", rule.get("minimum_inclusive"))
    maximum = rule.get("maximum", rule.get("maximum_inclusive"))
    if minimum is not None and value < minimum:
        errors.append(f"{name} must be >= {minimum}")
    if "minimum_exclusive" in rule and value <= rule["minimum_exclusive"]:
        errors.append(f"{name} must be > {rule['minimum_exclusive']}")
    if maximum is not None and value > maximum:
        errors.append(f"{name} must be <= {maximum}")
    if "maximum_exclusive" in rule and value >= rule["maximum_exclusive"]:
        errors.append(f"{name} must be < {rule['maximum_exclusive']}")
    return errors


def validate_request(identifier: str, inputs: object,
                     calculation_target: str = "required_sample_size") -> dict[str, Any]:
    try:
        item = resolve_procedure(identifier)
    except SkillContractError as exc:
        return {"valid": False, "errors": [exc.payload], "warnings": []}
    if item.get("status") != "VALIDATED_PUBLIC_PROCEDURE":
        return {
            "valid": False,
            "errors": [{"code": "PROCEDURE_NOT_VALIDATED", "message": "Only validated public procedures may be executed."}],
            "warnings": [],
        }
    if not isinstance(inputs, dict):
        return {"valid": False, "errors": [{"code": "INVALID_INPUT", "message": "inputs must be an object"}], "warnings": []}

    try:
        target_contract = procedure_input_contract(item, calculation_target)
    except SkillContractError as exc:
        return {"valid": False, "errors": [exc.payload], "warnings": []}
    contracts = {x["name"]: x for x in target_contract["input_contracts"]}
    normalized = dict(inputs)
    defaults_applied = []
    for optional in target_contract.get("optional_inputs", []):
        if optional.get("default") is not None and normalized.get(optional["name"]) is None:
            normalized[optional["name"]] = optional["default"]
            defaults_applied.append({
                "field": optional["name"], "value": optional["default"],
                "rule": f"{calculation_target} procedure default",
            })
    required = set(target_contract.get("required_inputs", []))
    missing = sorted(name for name in required if name not in normalized or normalized[name] is None)
    errors: list[dict[str, Any]] = [
        {"code": "MISSING_REQUIRED_INPUT", "field": name, "message": f"{name} must be explicitly supplied"}
        for name in missing
    ]
    unknown = sorted(set(normalized) - set(contracts))
    errors.extend(
        {"code": "UNKNOWN_INPUT", "field": name, "message": f"{name} is not in the procedure input contract"}
        for name in unknown
    )
    for name, value in normalized.items():
        contract = contracts.get(name)
        if not contract or value is None:
            continue
        expected = str(contract.get("data_type", "any"))
        if not _check_type(value, expected):
            errors.append({"code": "INVALID_INPUT_TYPE", "field": name, "message": f"{name} must be {expected}"})
            continue
        for message in _range_errors(name, value, contract.get("allowed_range")):
            errors.append({"code": "INVALID_INPUT_RANGE", "field": name, "message": message})

    warnings: list[dict[str, Any]] = []
    for contract in item.get("input_contracts", []):
        if contract.get("legacy_only") and contract["name"] in inputs:
            warnings.append({
                "code": "LEGACY_INPUT_NAME",
                "field": contract["name"],
                "message": "Legacy input is accepted by the frozen engine but is not the canonical skill input.",
            })
    return {
        "valid": not errors,
        "procedure_key": item["procedure_key"],
        "public_id": item["public_id"],
        "engine_id": item["engine_id"],
        "calculation_target": calculation_target,
        "normalized_inputs": normalized,
        "defaults_applied": defaults_applied,
        "field_contracts": [contracts[name] for name in normalized if name in contracts],
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--procedure", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--target", default="required_sample_size",
                        choices=["power", "detectable_effect", "required_events", "required_sample_size", "attrition_adjusted_sample_size"])
    args = parser.parse_args()
    inputs = json.loads(args.input.read_text(encoding="utf-8-sig"))
    result = validate_request(args.procedure, inputs, args.target)
    emit(result)
    raise SystemExit(0 if result["valid"] else 2)


if __name__ == "__main__":
    main()
