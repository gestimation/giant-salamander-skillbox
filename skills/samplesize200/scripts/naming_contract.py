from __future__ import annotations

import copy
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

_SKILL_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _SKILL_ROOT / "vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))
import yaml


REFERENCES = _SKILL_ROOT / "references"


@lru_cache(maxsize=1)
def naming_contract() -> dict[str, Any]:
    return yaml.safe_load((REFERENCES / "naming_contract.yaml").read_text(encoding="utf-8-sig"))


@lru_cache(maxsize=1)
def solution_identifier_registry() -> dict[str, Any]:
    return json.loads(
        (REFERENCES / "solution_identifier_registry.json").read_text(encoding="utf-8-sig")
    )


def _conflict(
    result: dict[str, Any], *, canonical_name: str, legacy_name: str,
    canonical_value: Any, legacy_value: Any,
) -> None:
    result.setdefault("input_conflicts", []).append({
        "field": canonical_name,
        "code": "ALIAS_CONFLICT",
        "canonical_name": canonical_name,
        "legacy_name": legacy_name,
        "canonical_value": copy.deepcopy(canonical_value),
        "legacy_value": copy.deepcopy(legacy_value),
        "values": {
            canonical_name: copy.deepcopy(canonical_value),
            legacy_name: copy.deepcopy(legacy_value),
        },
    })


def _bridge_field(result: dict[str, Any], canonical_name: str, legacy_name: str) -> None:
    canonical = result.get(canonical_name)
    legacy = result.get(legacy_name)
    if canonical is not None and legacy is not None and canonical != legacy:
        _conflict(
            result, canonical_name=canonical_name, legacy_name=legacy_name,
            canonical_value=canonical, legacy_value=legacy,
        )
    elif canonical is not None and legacy is None:
        result[legacy_name] = copy.deepcopy(canonical)


def _apply_calculator(result: dict[str, Any]) -> None:
    calculator_id = result.get("calculator_id")
    if not calculator_id:
        return
    registry = solution_identifier_registry()
    record = registry.get("calculators_by_id", {}).get(str(calculator_id))
    if record is None:
        result.setdefault("input_conflicts", []).append({
            "field": "calculator_id",
            "code": "UNKNOWN_CALCULATOR_ID",
            "values": {"calculator_id": calculator_id},
        })
        return
    for field in (
        "requested_output", "catalog_procedure_id", "engine_procedure_id", "procedure_key"
    ):
        mapped = record.get(field)
        current = result.get(field)
        if current is not None and current != mapped:
            _conflict(
                result, canonical_name=field, legacy_name="calculator_id",
                canonical_value=current, legacy_value=mapped,
            )
        elif current is None:
            result[field] = copy.deepcopy(mapped)


def _bridge_requested_output(result: dict[str, Any]) -> None:
    requested_output = result.get("requested_output")
    if requested_output is None:
        return
    output = naming_contract().get("requested_outputs", {}).get(str(requested_output))
    if output is None:
        result.setdefault("input_conflicts", []).append({
            "field": "requested_output",
            "code": "UNKNOWN_REQUESTED_OUTPUT",
            "values": {"requested_output": requested_output},
        })
        return
    target = output["engine_calculation_target"]
    old_target = result.get("calculation_target")
    if old_target is not None and old_target != target:
        _conflict(
            result, canonical_name="requested_output", legacy_name="calculation_target",
            canonical_value=requested_output, legacy_value=old_target,
        )
    elif old_target is None:
        result["calculation_target"] = target

    operation = output.get("legacy_operation")
    if operation == "procedure_specific":
        operation = output.get("default_legacy_operation")
        calculator_id = result.get("calculator_id")
        if calculator_id:
            record = solution_identifier_registry().get("calculators_by_id", {}).get(str(calculator_id), {})
            operation = record.get("legacy_catalog_operation", operation)
    old_operation = result.get("operation")
    if operation is not None and old_operation is not None and old_operation != operation:
        _conflict(
            result, canonical_name="requested_output", legacy_name="operation",
            canonical_value=requested_output, legacy_value=old_operation,
        )
    elif operation is not None and old_operation is None:
        result["operation"] = operation


def normalize_naming_aliases(spec: dict[str, Any]) -> dict[str, Any]:
    """Accept Phase 2 names while preserving the frozen v1 execution fields."""
    result = copy.deepcopy(spec)
    _apply_calculator(result)
    for canonical_name, legacy_name in (
        ("catalog_procedure_id", "requested_public_id"),
        ("engine_procedure_id", "requested_engine_id"),
        ("procedure_key", "requested_procedure_key"),
    ):
        _bridge_field(result, canonical_name, legacy_name)
    _bridge_requested_output(result)
    return result


def requested_output_from_legacy(spec: dict[str, Any]) -> str:
    if spec.get("requested_output"):
        return str(spec["requested_output"])
    target = str(spec.get("calculation_target") or "required_sample_size")
    operation = str(spec.get("operation") or "SAMPLE_SIZE")
    if target == "power":
        return "achieved_power"
    if target == "required_sample_size" and operation == "REQUIRED_CLUSTER_SIZE":
        return "required_cluster_size"
    return target
