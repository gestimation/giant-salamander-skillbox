"""Resolve conversational Phase 1 POWER inputs to an integer two-group design.

The statistical POWER adapters remain strict: they accept the actual integer
group sizes used for analysis.  This module is the boundary in front of those
adapters.  It may ask for clarification, but it never rounds an infeasible
fixed total or guesses which group is the numerator of an unequal ratio.
"""

from __future__ import annotations

from copy import deepcopy
from math import gcd, isfinite
from typing import Any, Mapping

from .power import PHASE1_POWER_ENGINE_IDS, calculate_power
from .rounding import allocation_block


# The resolver is deliberately narrower than Phase 1 POWER.  One-group,
# paired, and matched designs continue to use their existing explicit units.
INDEPENDENT_TWO_GROUP_POWER_DESIGNS: dict[str, dict[str, Any]] = {
    **{
        engine_id: {
            "roles": ("control", "treatment"),
            "count_keys": ("n_control", "n_treatment"),
            "existing_ratio_definition": "treatment/control",
        }
        for engine_id in {
            "TWO-001", "TWO-002", "TWO-004", "TWO-005", "TWO-006",
            "TWO-008", "TWO-009", "TWO-010", "TWO-011", "TWO-012",
            "TWO-031", "TWO-032", "TWO-033",
        }
    },
    **{
        engine_id: {
            "roles": ("standard", "treatment"),
            "count_keys": ("n_standard", "n_treatment"),
            "existing_ratio_definition": "treatment/standard",
        }
        for engine_id in {"TWO-007", "TWO-013", "TWO-014"}
    },
    "TWO-015": {
        "roles": ("control", "treatment"),
        "count_keys": ("n_control", "n_treatment"),
        "existing_ratio_definition": "control/treatment",
        "explicit_ratio_key": "control_to_treatment_ratio",
    },
    **{
        engine_id: {
            "roles": ("standard", "test"),
            "count_keys": ("n_standard", "n_test"),
            "existing_ratio_definition": "test/standard",
        }
        for engine_id in {"MARGIN-001", "MARGIN-004", "MARGIN-006"}
    },
}


_RESOLVER_ONLY_KEYS = {
    "n", "total_n", "per_group_n", "allocation_ratio",
    "allocation_ratio_direction", "control_to_treatment_ratio",
}


def _canonical_model_id(engine_id: str) -> str:
    canonical = str(engine_id).upper()
    for suffix in (".SAMPLE_SIZE", ".POWER", ".N"):
        if canonical.endswith(suffix):
            return canonical[:-len(suffix)]
    return canonical


def _question(code: str, prompt: str, expected_inputs: list[str], **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "code": code,
        "prompt": prompt,
        "expected_inputs": expected_inputs,
    }
    result.update(extra)
    return result


def _response(
    status: str,
    model: str,
    received: Mapping[str, Any],
    *,
    questions: list[dict[str, Any]] | None = None,
    issues: list[dict[str, str]] | None = None,
    power_inputs: dict[str, Any] | None = None,
    design_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "engine_id": model,
        "calculation_target": "power",
        "received_inputs": deepcopy(dict(received)),
        "questions": questions or [],
        "issues": issues or [],
        **({"power_inputs": power_inputs} if power_inputs is not None else {}),
        **({"design_resolution": design_resolution} if design_resolution is not None else {}),
    }


def _integer_issue(name: str, value: Any) -> dict[str, str] | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return {
            "code": "invalid_integer_size",
            "field": name,
            "message": f"{name} must be a positive integer",
        }
    return None


def _parse_ratio(value: Any) -> tuple[float | None, dict[str, str] | None]:
    original = value
    if isinstance(value, str):
        text = value.strip()
        if ":" in text:
            pieces = text.split(":")
            if len(pieces) != 2:
                return None, {
                    "code": "invalid_allocation_ratio", "field": "allocation_ratio",
                    "message": "allocation_ratio must be a positive number or a:b",
                }
            try:
                numerator, denominator = (float(piece.strip()) for piece in pieces)
                value = numerator / denominator
            except (TypeError, ValueError, ZeroDivisionError):
                return None, {
                    "code": "invalid_allocation_ratio", "field": "allocation_ratio",
                    "message": "allocation_ratio must be a positive number or a:b",
                }
        else:
            try:
                value = float(text)
            except ValueError:
                value = None
    if isinstance(value, bool):
        value = None
    try:
        ratio = float(value) if value is not None else float("nan")
    except (TypeError, ValueError):
        ratio = float("nan")
    if not isfinite(ratio) or ratio <= 0:
        return None, {
            "code": "invalid_allocation_ratio", "field": "allocation_ratio",
            "message": f"allocation_ratio must be positive; received {original!r}",
        }
    return ratio, None


def _normalize_direction(value: Any, first_role: str, second_role: str) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower().replace("_to_", ":").replace("/", ":")
    normalized = normalized.replace("→", ":").replace(" ", "")
    pieces = normalized.split(":")
    if len(pieces) != 2:
        return None
    left, right = pieces
    if (left, right) == (first_role, second_role):
        return f"{first_role}:{second_role}"
    if (left, right) == (second_role, first_role):
        return f"{second_role}:{first_role}"
    return None


def _ratio_to_second_over_first(
    ratio: float, direction: str, first_role: str, second_role: str
) -> float:
    if direction == f"{second_role}:{first_role}":
        return ratio
    if direction == f"{first_role}:{second_role}":
        return 1.0 / ratio
    raise ValueError("unrecognized allocation ratio direction")


def resolve_power_design(engine_id: str, inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve fixed-size inputs for one of the 20 independent two-group engines."""
    model = _canonical_model_id(engine_id)
    if not isinstance(inputs, Mapping):
        return _response("invalid", model, {}, issues=[{
            "code": "invalid_power_inputs", "field": "inputs",
            "message": "power inputs must be an object",
        }])
    if model not in PHASE1_POWER_ENGINE_IDS:
        return _response("invalid", model, inputs, issues=[{
            "code": "power_not_supported", "field": "engine_id",
            "message": f"Phase 1 power is not supported for {engine_id}",
        }])
    if model not in INDEPENDENT_TWO_GROUP_POWER_DESIGNS:
        return _response("invalid", model, inputs, issues=[{
            "code": "not_independent_two_group", "field": "engine_id",
            "message": (
                f"{model} does not use the independent two-group design resolver; "
                "provide its existing realized design unit directly"
            ),
        }])

    spec = INDEPENDENT_TWO_GROUP_POWER_DESIGNS[model]
    first_role, second_role = spec["roles"]
    first_key, second_key = spec["count_keys"]
    data = dict(inputs)
    issues: list[dict[str, str]] = []
    questions: list[dict[str, Any]] = []

    size_fields = ["n", "total_n", "per_group_n", first_key, second_key]
    for key in size_fields:
        if key in data:
            issue = _integer_issue(key, data[key])
            if issue:
                issues.append(issue)
    if issues:
        return _response("invalid", model, inputs, issues=issues)

    if "n" in data:
        questions.append(_question(
            "sample_size_scope",
            f"{data['n']}人は総数ですか、それとも各群{data['n']}人ですか？",
            ["total_n", "per_group_n"],
            roles=[first_role, second_role],
        ))

    generic_ratio_present = "allocation_ratio" in data
    explicit_ratio_key = spec.get("explicit_ratio_key")
    explicit_ratio_present = bool(explicit_ratio_key and explicit_ratio_key in data)
    if generic_ratio_present and explicit_ratio_present:
        questions.append(_question(
            "duplicate_allocation_ratio",
            "割付比が2通り指定されています。使用する比と向きを1つにしてください。",
            ["allocation_ratio", "allocation_ratio_direction"],
        ))

    ratio_value: float | None = None
    ratio_input: Any = None
    ratio_direction: str | None = None
    if explicit_ratio_present and not generic_ratio_present:
        ratio_input = data[explicit_ratio_key]
        ratio_value, issue = _parse_ratio(ratio_input)
        if issue:
            issues.append({**issue, "field": explicit_ratio_key})
        ratio_direction = f"{first_role}:{second_role}"
    elif generic_ratio_present and not explicit_ratio_present:
        ratio_input = data["allocation_ratio"]
        ratio_value, issue = _parse_ratio(ratio_input)
        if issue:
            issues.append(issue)
        supplied_direction = data.get("allocation_ratio_direction")
        if ratio_value is not None and ratio_value != 1.0:
            ratio_direction = _normalize_direction(
                supplied_direction, first_role, second_role
            )
            if ratio_direction is None:
                questions.append(_question(
                    "allocation_ratio_direction",
                    (
                        f"割付比{ratio_input}は{first_role}:{second_role}ですか、"
                        f"{second_role}:{first_role}ですか？"
                    ),
                    ["allocation_ratio_direction"],
                    options=[f"{first_role}:{second_role}", f"{second_role}:{first_role}"],
                ))
        elif ratio_value == 1.0:
            ratio_direction = f"{second_role}:{first_role}"
    elif "allocation_ratio_direction" in data:
        questions.append(_question(
            "allocation_ratio_missing",
            "割付比の向きは指定されていますが、割付比そのものがありません。",
            ["allocation_ratio"],
        ))

    if issues:
        return _response("invalid", model, inputs, issues=issues)

    # Ambiguous fields and ratio direction must be resolved before using any
    # apparently sufficient design information.
    if questions:
        return _response("needs_clarification", model, inputs, questions=questions)

    first = data.get(first_key)
    second = data.get(second_key)
    total = data.get("total_n")
    per_group = data.get("per_group_n")

    if first is not None and second is None and total is not None:
        second = total - first
        issue = _integer_issue(second_key, second)
        if issue:
            return _response("invalid", model, inputs, issues=[issue])
    elif second is not None and first is None and total is not None:
        first = total - second
        issue = _integer_issue(first_key, first)
        if issue:
            return _response("invalid", model, inputs, issues=[issue])

    resolution_method: str | None = None
    if first is not None and second is not None:
        resolution_method = "explicit_group_sizes"
    elif per_group is not None:
        first = second = per_group
        resolution_method = "explicit_per_group_size"
    elif total is not None and ratio_value is None:
        if total % 2:
            return _response("needs_clarification", model, inputs, questions=[_question(
                "group_sizes_required",
                (
                    f"総数{total}人はデフォルト1:1に分割できません。"
                    f"{first_role}群と{second_role}群の人数を指定してください。"
                ),
                [first_key, second_key],
                total_n=total,
            )])
        first = second = total // 2
        ratio_value = 1.0
        ratio_direction = f"{second_role}:{first_role}"
        resolution_method = "total_with_default_1_to_1"
    elif total is not None and ratio_value is not None and ratio_direction is not None:
        canonical_ratio = _ratio_to_second_over_first(
            ratio_value, ratio_direction, first_role, second_role
        )
        first_block, second_block = allocation_block(canonical_ratio)
        block_total = first_block + second_block
        if total % block_total:
            return _response("needs_clarification", model, inputs, questions=[_question(
                "group_sizes_required",
                (
                    f"総数{total}人は指定された割付ブロック"
                    f"{first_role}:{second_role}={first_block}:{second_block}で割り切れません。"
                    "実際の各群人数を指定してください。"
                ),
                [first_key, second_key],
                total_n=total,
                normalized_allocation_block={first_role: first_block, second_role: second_block},
            )])
        blocks = total // block_total
        first, second = blocks * first_block, blocks * second_block
        resolution_method = "total_with_ratio"
    elif first is not None or second is not None:
        missing = second_key if second is None else first_key
        return _response("needs_clarification", model, inputs, questions=[_question(
            "group_size_missing",
            f"実現デザインを確定するため、{missing}またはtotal_nを指定してください。",
            [missing, "total_n"],
        )])
    elif ratio_value is not None:
        return _response("needs_clarification", model, inputs, questions=[_question(
            "sample_size_missing",
            "achieved powerには総人数または各群の人数が必要です。",
            ["total_n", first_key, second_key],
        )])
    else:
        return _response("needs_clarification", model, inputs, questions=[_question(
            "sample_size_missing",
            "achieved powerには総人数、各群同数、または各群の人数が必要です。",
            ["total_n", "per_group_n", first_key, second_key],
        )])

    assert first is not None and second is not None
    actual_total = first + second
    conflicts: list[dict[str, Any]] = []
    if total is not None and total != actual_total:
        conflicts.append(_question(
            "total_group_size_conflict",
            f"総数{total}人と群別人数{first}+{second}={actual_total}人が一致しません。",
            ["total_n", first_key, second_key],
        ))
    if per_group is not None and (first != per_group or second != per_group):
        conflicts.append(_question(
            "per_group_size_conflict",
            f"各群{per_group}人という指定と群別人数が一致しません。",
            ["per_group_n", first_key, second_key],
        ))

    actual_divisor = gcd(first, second)
    actual_divisor_first = first // actual_divisor
    actual_divisor_second = second // actual_divisor
    if ratio_value is not None and ratio_direction is not None:
        canonical_ratio = _ratio_to_second_over_first(
            ratio_value, ratio_direction, first_role, second_role
        )
        requested_first_block, requested_second_block = allocation_block(canonical_ratio)
        if first * requested_second_block != second * requested_first_block:
            conflicts.append(_question(
                "allocation_group_size_conflict",
                (
                    f"指定割付{first_role}:{second_role}="
                    f"{requested_first_block}:{requested_second_block}と群別人数"
                    f"{first}:{second}が一致しません。"
                ),
                ["allocation_ratio", "allocation_ratio_direction", first_key, second_key],
            ))
    if conflicts:
        return _response("needs_clarification", model, inputs, questions=conflicts)

    power_inputs = {
        key: deepcopy(value) for key, value in data.items()
        if key not in _RESOLVER_ONLY_KEYS and key not in {first_key, second_key}
    }
    power_inputs[first_key] = first
    power_inputs[second_key] = second
    design_resolution = {
        "resolution_method": resolution_method,
        "roles": [first_role, second_role],
        "group_sizes": {first_role: first, second_role: second},
        "total_n": actual_total,
        "input_total_n": total,
        "input_per_group_n": per_group,
        "input_allocation_ratio": ratio_input,
        "input_allocation_ratio_direction": data.get("allocation_ratio_direction"),
        "normalized_allocation_ratio_direction": ratio_direction,
        "normalized_allocation_block": {
            first_role: actual_divisor_first,
            second_role: actual_divisor_second,
        },
        "normalized_allocation_ratio": second / first,
        "normalized_allocation_ratio_definition": f"{second_role}/{first_role}",
        "existing_engine_ratio_definition": spec["existing_ratio_definition"],
        "user_confirmation_required": False,
    }
    return _response(
        "ready", model, inputs, power_inputs=power_inputs,
        design_resolution=design_resolution,
    )


def calculate_power_request(engine_id: str, inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve conversational design inputs, then call the existing POWER runtime.

    Non-independent Phase 1 designs retain their existing strict realized-unit
    inputs.  Unsupported models return a structured invalid response; direct
    ``calculate_power`` remains the strict exception-raising API.
    """
    model = _canonical_model_id(engine_id)
    if model not in PHASE1_POWER_ENGINE_IDS:
        return _response("invalid", model, inputs if isinstance(inputs, Mapping) else {}, issues=[{
            "code": "power_not_supported", "field": "engine_id",
            "message": f"Phase 1 power is not supported for {engine_id}",
        }])
    if model not in INDEPENDENT_TWO_GROUP_POWER_DESIGNS:
        return calculate_power(engine_id, inputs)
    resolution = resolve_power_design(engine_id, inputs)
    if resolution["status"] != "ready":
        return resolution
    result = calculate_power(model, resolution["power_inputs"])
    result["design_resolution"] = resolution["design_resolution"]
    return result


__all__ = [
    "INDEPENDENT_TWO_GROUP_POWER_DESIGNS", "calculate_power_request",
    "resolve_power_design",
]
