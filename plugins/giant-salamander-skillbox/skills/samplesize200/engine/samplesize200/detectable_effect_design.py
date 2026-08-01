"""Resolve conversational integer designs for analytic detectable effects."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .detectable_effect import (
    DETECTABLE_EFFECT_ENGINE_IDS,
    calculate_detectable_effect,
)
from .power_design import (
    INDEPENDENT_TWO_GROUP_POWER_DESIGNS,
    resolve_power_design,
)


INDEPENDENT_TWO_GROUP_DETECTABLE_EFFECT_DESIGNS = {
    engine_id: deepcopy(INDEPENDENT_TWO_GROUP_POWER_DESIGNS[engine_id])
    for engine_id in DETECTABLE_EFFECT_ENGINE_IDS
    if engine_id in INDEPENDENT_TWO_GROUP_POWER_DESIGNS
}


def _canonical_model_id(engine_id: str) -> str:
    canonical = str(engine_id).upper()
    for suffix in (".DETECTABLE_EFFECT", ".SAMPLE_SIZE", ".POWER", ".N"):
        if canonical.endswith(suffix):
            return canonical[:-len(suffix)]
    return canonical


def _invalid(model: str, inputs: Mapping[str, Any], message: str) -> dict[str, Any]:
    return {
        "status": "invalid",
        "engine_id": model,
        "calculation_target": "detectable_effect",
        "received_inputs": deepcopy(dict(inputs)),
        "questions": [],
        "issues": [{
            "code": "detectable_effect_not_supported",
            "field": "engine_id",
            "message": message,
        }],
    }


def resolve_detectable_effect_design(
    engine_id: str, inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Reuse POWER's exact integer allocation resolver for the supported subset."""
    model = _canonical_model_id(engine_id)
    if not isinstance(inputs, Mapping):
        return _invalid(model, {}, "detectable-effect inputs must be an object")
    if model not in DETECTABLE_EFFECT_ENGINE_IDS:
        return _invalid(model, inputs, f"detectable_effect is not supported for {engine_id}")
    if model not in INDEPENDENT_TWO_GROUP_DETECTABLE_EFFECT_DESIGNS:
        return _invalid(
            model, inputs,
            f"{model} does not use the independent two-group design resolver",
        )
    resolution = deepcopy(resolve_power_design(model, inputs))
    resolution["calculation_target"] = "detectable_effect"
    if "power_inputs" in resolution:
        resolution["detectable_effect_inputs"] = resolution.pop("power_inputs")
    return resolution


def calculate_detectable_effect_request(
    engine_id: str, inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve conversational sizes, then call the strict analytic runtime."""
    model = _canonical_model_id(engine_id)
    if not isinstance(inputs, Mapping):
        return _invalid(model, {}, "detectable-effect inputs must be an object")
    if model not in DETECTABLE_EFFECT_ENGINE_IDS:
        return _invalid(model, inputs, f"detectable_effect is not supported for {engine_id}")
    if model not in INDEPENDENT_TWO_GROUP_DETECTABLE_EFFECT_DESIGNS:
        return calculate_detectable_effect(model, inputs)
    resolution = resolve_detectable_effect_design(model, inputs)
    if resolution["status"] != "ready":
        return resolution
    result = calculate_detectable_effect(
        model, resolution["detectable_effect_inputs"],
    )
    result["design_resolution"] = resolution["design_resolution"]
    return result


__all__ = [
    "INDEPENDENT_TWO_GROUP_DETECTABLE_EFFECT_DESIGNS",
    "calculate_detectable_effect_request", "resolve_detectable_effect_design",
]
