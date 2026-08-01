"""Preview public procedure layer.

A procedure accepts research-design conditions and returns the final study
size.  Legacy calculation specifications remain callable through ``cli.calculate``;
they are not automatically counted as public procedures.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from ._version import VERSION
from .binary import fisher_exact_correction, two_sample_odds_ratio, two_sample_proportions
from .confidence import (
    finite_population_correction, one_proportion_normal_absolute,
    one_proportion_normal_relative, one_proportion_wilson,
)
from .margin import MARGIN_PROCEDURES
from .multi_composition import MULTI_COMPOSITION_PROCEDURES
from .multi_cluster import MULTI_CLUSTER_PROCEDURES
from .one_survival import ONE_SURVIVAL_PROCEDURES
from .paired import discordant_count_conversion, matched_case_control_correction
from .survival import events_to_participants, freedman_events, schoenfeld_events


class ProcedureContractError(ValueError):
    """Machine-readable public procedure contract error."""

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        super().__init__(payload.get("message", payload.get("code", "procedure contract error")))


WRAPPER_IDS = {
    "TWO-003.SAMPLE_SIZE", "TWO-017.SAMPLE_SIZE", "TWO-018.SAMPLE_SIZE",
    "TWO-025.SAMPLE_SIZE", "CI-004.SAMPLE_SIZE",
}
INTERNAL_COMPONENT_IDS = {"TWO-019"}


def _procedure_envelope(result: dict[str, Any], procedure_id: str,
                        lineage: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    output = deepcopy(result)
    model_id = procedure_id.partition(".")[0]
    output.update({
        "product": "samplesize200 Alpha", "version": VERSION,
        "release_stage": "alpha", "model_id": model_id,
        "operation": "sample_size", "procedure_id": procedure_id,
        "schema_status": "preview", "final_public_api": False,
    })
    primary = next((record for record in output.get("quantities", [])
                    if record.get("key") == "final_total" and record.get("stage") == "final"), None)
    if primary is None:
        primary = {"key": "final_total", "value": output["final_total"],
                   "quantity": "participants", "unit": "person", "stage": "final"}
    else:
        primary = dict(primary)
        if primary.get("unit") == "participants":
            primary["unit"] = "person"
    output["primary_result"] = primary
    output["procedure_lineage"] = lineage or output.get("procedure_lineage") or [{
        "role": "calculation_specification", "method_id": result.get("method_id"),
        "consumed_keys": [], "produced_key": "final_total",
    }]
    return output


def fisher_end_to_end(*, control_proportion: float,
                      treatment_proportion: float | None = None,
                      odds_ratio: float | None = None,
                      allocation_ratio: float = 1.0, alpha: float = 0.05,
                      power: float = 0.80, sides: int = 2) -> dict[str, Any]:
    """Public TWO-003 wrapper from direct proportions/effect to Fisher N."""
    if (treatment_proportion is None) == (odds_ratio is None):
        raise ValueError("provide exactly one of treatment_proportion or odds_ratio")
    if treatment_proportion is not None:
        base = two_sample_proportions(
            control_proportion=control_proportion,
            treatment_proportion=treatment_proportion,
            allocation_ratio=allocation_ratio, alpha=alpha, power=power, sides=sides,
        )
    else:
        base = two_sample_odds_ratio(
            control_proportion=control_proportion, odds_ratio=float(odds_ratio),
            allocation_ratio=allocation_ratio, alpha=alpha, power=power, sides=sides,
        )
    corrected = fisher_exact_correction(base)
    return _procedure_envelope(corrected, "TWO-003.SAMPLE_SIZE", [
        {"role": "base_sample_size", "method_id": base["method_id"],
         "consumed_keys": list(base["inputs"]), "produced_key": "raw_total"},
        {"role": "correction", "method_id": "TWO-003", "consumed_key": "raw_total",
         "consumed_quantity": "participants", "consumed_stage": "raw",
         "produced_key": "final_total"},
    ])


def _survival_wrapper(event_function: Callable[..., dict[str, Any]], procedure_id: str,
                      *, hazard_ratio: float, standard_event_probability: float,
                      treatment_event_probability: float, allocation_ratio: float = 1.0,
                      alpha: float = 0.05, power: float = 0.80,
                      sides: int = 2) -> dict[str, Any]:
    events = event_function(hazard_ratio=hazard_ratio, allocation_ratio=allocation_ratio,
                            alpha=alpha, power=power, sides=sides)
    people = events_to_participants(
        parent_result=events, standard_event_probability=standard_event_probability,
        treatment_event_probability=treatment_event_probability,
        allocation_ratio=allocation_ratio,
    )
    people["method_id"] = procedure_id.partition(".")[0]
    return _procedure_envelope(people, procedure_id, [
        {"role": "required_events", "method_id": events["method_id"],
         "consumed_keys": ["hazard_ratio", "allocation_ratio", "alpha", "power", "sides"],
         "produced_key": "rounded_events", "quantity": "events", "stage": "rounded"},
        {"role": "events_to_participants", "component_id": "TWO-019",
         "consumed_key": "rounded_events", "consumed_quantity": "events",
         "consumed_stage": "rounded", "produced_key": "final_total"},
    ])


def schoenfeld_end_to_end(**kwargs: Any) -> dict[str, Any]:
    return _survival_wrapper(schoenfeld_events, "TWO-017.SAMPLE_SIZE", **kwargs)


def freedman_end_to_end(**kwargs: Any) -> dict[str, Any]:
    return _survival_wrapper(freedman_events, "TWO-018.SAMPLE_SIZE", **kwargs)


def _required_events_envelope(result: dict[str, Any], procedure_id: str) -> dict[str, Any]:
    """Expose an independently validated event kernel without participant conversion."""
    output = deepcopy(result)
    for quantity in output.get("quantities", []):
        if isinstance(quantity, dict) and quantity.get("quantity") == "events":
            quantity["unit"] = "event"
    output.update({
        "product": "samplesize200 Alpha", "version": VERSION,
        "release_stage": "alpha", "model_id": procedure_id.partition(".")[0],
        "operation": "required_events", "calculation_target": "required_events",
        "procedure_id": procedure_id, "schema_status": "preview", "final_public_api": False,
        "primary_result": {
            "key": "final_events", "value": output["final_events"],
            "quantity": "events", "unit": "event", "stage": "final",
        },
        "procedure_lineage": [{
            "role": "validated_event_kernel", "method_id": output.get("method_id"),
            "consumed_keys": ["hazard_ratio", "allocation_ratio", "alpha", "power", "sides"],
            "produced_key": "final_events",
        }],
    })
    return output


def calculate_target(procedure_id: str, calculation_target: str,
                     inputs: dict[str, Any]) -> dict[str, Any]:
    """Calculate only the requested planning stage.

    Participant conversion inputs are intentionally not accepted for
    ``required_events``. ``power`` and ``detectable_effect`` reuse the model ID
    but accept a realized integer design. The ordinary public procedure remains
    unchanged for ``required_sample_size``.
    """
    if calculation_target == "required_sample_size":
        return calculate_procedure(procedure_id, inputs)
    if calculation_target == "power":
        from .power_design import calculate_power_request
        return calculate_power_request(procedure_id, inputs)
    if calculation_target == "detectable_effect":
        from .detectable_effect_design import calculate_detectable_effect_request
        return calculate_detectable_effect_request(procedure_id, inputs)
    canonical = procedure_id
    if canonical.endswith(".N"):
        canonical = canonical[:-2] + ".SAMPLE_SIZE"
    if "." not in canonical:
        canonical += ".SAMPLE_SIZE"
    if calculation_target == "required_events":
        kernels = {
            "TWO-017.SAMPLE_SIZE": schoenfeld_events,
            "TWO-018.SAMPLE_SIZE": freedman_events,
        }
        if canonical not in kernels:
            raise ValueError(f"required_events is not supported for {procedure_id}")
        allowed = {"hazard_ratio", "allocation_ratio", "alpha", "power", "sides"}
        unknown = sorted(set(inputs) - allowed)
        if unknown:
            raise ValueError(
                "required_events accepts only event-kernel inputs; participant-conversion "
                f"inputs belong to required_sample_size: {', '.join(unknown)}"
            )
        return _required_events_envelope(kernels[canonical](**inputs), canonical)
    if calculation_target == "attrition_adjusted_sample_size":
        result = calculate_procedure(procedure_id, inputs)
        attrition_keys = {key for key in inputs if "attrition" in key}
        if not attrition_keys:
            raise ValueError(
                "attrition_adjusted_sample_size requires an attrition input supported by the selected procedure"
            )
        result["calculation_target"] = calculation_target
        return result
    raise ValueError(
        "calculation_target must be detectable_effect, power, required_events, "
        "required_sample_size, or attrition_adjusted_sample_size"
    )


def matched_case_control_end_to_end(*, discordant_odds_ratio: float,
                                    discordant_fraction: float,
                                    controls_per_case: int,
                                    alpha: float = 0.05, power: float = 0.80,
                                    sides: int = 2) -> dict[str, Any]:
    pairs = discordant_count_conversion(
        discordant_odds_ratio=discordant_odds_ratio,
        discordant_fraction=discordant_fraction,
        alpha=alpha, power=power, sides=sides,
    )
    result = matched_case_control_correction(
        parent_result=pairs, controls_per_case=controls_per_case,
    )
    return _procedure_envelope(result, "TWO-025.SAMPLE_SIZE", [
        {"role": "equal_matched_pairs", "method_id": "TWO-024",
         "consumed_keys": ["discordant_odds_ratio", "discordant_fraction", "alpha", "power", "sides"],
         "produced_key": "final_pairs", "quantity": "pairs", "stage": "final"},
        {"role": "matching_correction", "method_id": "TWO-025",
         "consumed_key": "final_pairs", "consumed_quantity": "pairs", "consumed_stage": "final",
         "produced_key": "final_total"},
    ])


_PRECISION_MODELS: dict[str, Callable[..., dict[str, Any]]] = {
    "one_proportion_normal_absolute": one_proportion_normal_absolute,
    "one_proportion_normal_relative": one_proportion_normal_relative,
    "one_proportion_wilson": one_proportion_wilson,
}


def finite_population_end_to_end(*, population_size: int, precision_model: str,
                                 precision_inputs: dict[str, Any]) -> dict[str, Any]:
    """Public CI-004 wrapper from a precision design to finite-population N."""
    if precision_model not in _PRECISION_MODELS:
        raise ValueError(f"unsupported precision_model: {precision_model!r}")
    if not isinstance(precision_inputs, dict):
        raise ValueError("precision_inputs must be an object of direct study conditions")
    base = _PRECISION_MODELS[precision_model](**precision_inputs)
    result = finite_population_correction(parent_result=base, population_size=population_size)
    return _procedure_envelope(result, "CI-004.SAMPLE_SIZE", [
        {"role": "infinite_population_precision", "precision_model": precision_model,
         "method_id": base["method_id"], "consumed_keys": list(precision_inputs),
         "produced_key": "raw_total", "quantity": "participants", "stage": "raw"},
        {"role": "finite_population_correction", "method_id": "CI-004",
         "consumed_key": "raw_total", "consumed_quantity": "participants",
         "consumed_stage": "raw", "produced_key": "final_total"},
    ])


WRAPPER_PROCEDURES: dict[str, Callable[..., dict[str, Any]]] = {
    "TWO-003.SAMPLE_SIZE": fisher_end_to_end,
    "TWO-017.SAMPLE_SIZE": schoenfeld_end_to_end,
    "TWO-018.SAMPLE_SIZE": freedman_end_to_end,
    "TWO-025.SAMPLE_SIZE": matched_case_control_end_to_end,
    "CI-004.SAMPLE_SIZE": finite_population_end_to_end,
}


def procedure_aliases(procedure_id: str) -> list[str]:
    model = procedure_id.partition(".")[0]
    return [model, f"{model}.N"]


def calculate_procedure(procedure_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Run a canonical public procedure or a compatibility alias."""
    if str(procedure_id).upper().endswith(".DETECTABLE_EFFECT"):
        from .detectable_effect_design import calculate_detectable_effect_request
        return calculate_detectable_effect_request(procedure_id, inputs)
    if str(procedure_id).upper().endswith(".POWER"):
        from .power_design import calculate_power_request
        return calculate_power_request(procedure_id, inputs)
    if procedure_id == "TWO-048":
        candidates = [
            "CLUSTER-FIXED-CONTINUOUS.REQUIRED_CLUSTER_SIZE",
            "CLUSTER-FIXED-BINARY.REQUIRED_CLUSTER_SIZE",
        ]
        outcome = inputs.get("outcome")
        if outcome not in {"continuous", "binary"}:
            raise ProcedureContractError({
                "code": "LEGACY_MAPPING_AMBIGUOUS",
                "legacy_id": "TWO-048",
                "message": "TWO-048 requires an explicit outcome selector",
                "candidates": candidates,
                "required_disambiguation": ["outcome"],
                "accepted_outcomes": ["continuous", "binary"],
            })
        canonical = candidates[0] if outcome == "continuous" else candidates[1]
        resolved_inputs = dict(inputs)
        resolved_inputs.pop("outcome")
        result = calculate_procedure(canonical, resolved_inputs)
        result["legacy_resolution"] = {
            "legacy_id": "TWO-048",
            "resolved_procedure_id": canonical,
            "disambiguating_input": {"outcome": outcome},
        }
        result.setdefault("procedure_lineage", []).insert(0, {
            "role": "legacy_mapping_resolution",
            "legacy_id": "TWO-048",
            "resolved_procedure_id": canonical,
            "disambiguating_input": {"outcome": outcome},
        })
        return result
    canonical = procedure_id
    required_cluster_aliases = {
        "CLUSTER-FIXED-CONTINUOUS": "CLUSTER-FIXED-CONTINUOUS.REQUIRED_CLUSTER_SIZE",
        "CLUSTER-FIXED-CONTINUOUS.M": "CLUSTER-FIXED-CONTINUOUS.REQUIRED_CLUSTER_SIZE",
        "CLUSTER-FIXED-BINARY": "CLUSTER-FIXED-BINARY.REQUIRED_CLUSTER_SIZE",
        "CLUSTER-FIXED-BINARY.M": "CLUSTER-FIXED-BINARY.REQUIRED_CLUSTER_SIZE",
    }
    if canonical in required_cluster_aliases:
        canonical = required_cluster_aliases[canonical]
    if canonical.endswith(".N"):
        canonical = canonical[:-2] + ".SAMPLE_SIZE"
    if "." not in canonical:
        canonical += ".SAMPLE_SIZE"
    if canonical in WRAPPER_PROCEDURES:
        return WRAPPER_PROCEDURES[canonical](**inputs)
    if canonical in ONE_SURVIVAL_PROCEDURES:
        return _procedure_envelope(ONE_SURVIVAL_PROCEDURES[canonical](**inputs), canonical)
    if canonical in MARGIN_PROCEDURES:
        return MARGIN_PROCEDURES[canonical](**inputs)
    if canonical in MULTI_COMPOSITION_PROCEDURES:
        return _procedure_envelope(MULTI_COMPOSITION_PROCEDURES[canonical](**inputs), canonical)
    if canonical in MULTI_CLUSTER_PROCEDURES:
        return MULTI_CLUSTER_PROCEDURES[canonical](**inputs)
    # Import lazily to avoid a circular import with the legacy CLI registry.
    from .cli import METHODS
    model = canonical.partition(".")[0]
    if canonical.endswith(".SAMPLE_SIZE") and model in METHODS and model not in {
        "TWO-003", "TWO-017", "TWO-018", "TWO-019", "TWO-025", "CI-004"
    }:
        return _procedure_envelope(METHODS[model](**inputs), canonical)
    raise ValueError(f"unsupported public procedure: {procedure_id}")
