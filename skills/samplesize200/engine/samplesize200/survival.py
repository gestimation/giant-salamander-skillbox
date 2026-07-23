"""Chapter 7 proportional-hazards event and participant calculations."""

from __future__ import annotations

from math import ceil, isfinite, log
from typing import Any

from .distributions import critical_values
from .rounding import allocation_rounding
from .schema_contract import contracted, consume_quantity


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")
    return value


def _probability(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 < value <= 1:
        raise ValueError(f"{name} must be a finite probability in (0, 1]")
    return value


def _event_result(method_id: str, reference: str, inputs: dict[str, Any], raw: float) -> dict[str, Any]:
    if not isfinite(raw) or raw <= 0:
        raise ValueError("inputs do not produce a positive finite event count")
    final = ceil(raw)
    return {
        "method_id": method_id, "formula_reference": reference, "inputs": inputs,
        "raw_events": raw, "rounded_events": final, "final_events": final,
        "raw_total": raw, "rounded_total": final, "final_total": final,
        "rounding_rule": "ceil the unrounded required event count",
        "warnings": [], "provenance": None,
    }


def schoenfeld_events(*, hazard_ratio: float, allocation_ratio: float = 1.0,
                      alpha: float = 0.05, power: float = 0.80,
                      sides: int = 2) -> dict[str, Any]:
    """TWO-017: Schoenfeld required events, equation 7.6."""
    ratio = _positive("hazard_ratio", hazard_ratio)
    if ratio == 1:
        raise ValueError("hazard_ratio must differ from 1 for a finite event count")
    phi = _positive("allocation_ratio", allocation_ratio)
    z_alpha, z_power = critical_values(alpha, power, sides)
    raw = (1 + phi) ** 2 / phi * (z_alpha + z_power) ** 2 / log(ratio) ** 2
    return _event_result("TWO-017", "equation 7.6", {
        "hazard_ratio": ratio,
        "hazard_ratio_definition": "treatment hazard / standard hazard",
        "allocation_ratio": phi,
        "allocation_ratio_definition": "treatment / standard",
        "alpha": alpha, "power": power, "sides": sides,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw)


def freedman_events(*, hazard_ratio: float, allocation_ratio: float = 1.0,
                    alpha: float = 0.05, power: float = 0.80,
                    sides: int = 2) -> dict[str, Any]:
    """TWO-018: Freedman required events, equation 7.7."""
    ratio = _positive("hazard_ratio", hazard_ratio)
    if ratio == 1:
        raise ValueError("hazard_ratio must differ from 1 for a finite event count")
    phi = _positive("allocation_ratio", allocation_ratio)
    z_alpha, z_power = critical_values(alpha, power, sides)
    raw = (1 / phi) * ((1 + phi * ratio) / (1 - ratio)) ** 2 * (z_alpha + z_power) ** 2
    return _event_result("TWO-018", "equation 7.7", {
        "hazard_ratio": ratio,
        "hazard_ratio_definition": "treatment hazard / standard hazard",
        "allocation_ratio": phi,
        "allocation_ratio_definition": "treatment / standard",
        "alpha": alpha, "power": power, "sides": sides,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw)


def events_to_participants(*, parent_result: dict[str, Any],
                           standard_event_probability: float,
                           treatment_event_probability: float,
                           allocation_ratio: float = 1.0,
                           parent_result_key: str = "rounded_events",
                           parent_stage: str = "rounded") -> dict[str, Any]:
    """TWO-019: convert typed required events to participants, equation 7.8."""
    consumed = consume_quantity(
        parent_result, allowed_parent_methods={"TWO-017", "TWO-018"},
        key=parent_result_key, quantity="events", unit="events", stage=parent_stage,
    )
    standard = _probability("standard_event_probability", standard_event_probability)
    treatment = _probability("treatment_event_probability", treatment_event_probability)
    phi = _positive("allocation_ratio", allocation_ratio)
    parent_phi = parent_result.get("inputs", {}).get("allocation_ratio")
    if parent_phi is not None and abs(float(parent_phi) - phi) > 1e-12:
        raise ValueError("allocation_ratio must equal the parent event calculation allocation ratio")
    event_proportion = (standard + phi * treatment) / (1 + phi)
    raw_total = float(consumed["value"]) / event_proportion
    result: dict[str, Any] = {
        "method_id": "TWO-019", "formula_reference": "equation 7.8",
        "inputs": {
            "parent_method_id": parent_result["method_id"],
            "parent_result_key": parent_result_key, "parent_stage": parent_stage,
            "standard_event_probability": standard,
            "treatment_event_probability": treatment,
            "allocation_ratio": phi,
            "allocation_ratio_definition": "treatment / standard",
            "anticipated_event_proportion": event_proportion,
        },
        "raw_required_events": parent_result["raw_events"],
        "rounded_required_events": parent_result["rounded_events"],
        "consumed_required_events": consumed["value"],
        "consumed_event_stage": parent_stage,
        "raw_total": raw_total,
        "rounded_total": ceil(raw_total),
        "final_total": ceil(raw_total),
        "rounding_rule": "divide the explicitly staged required event count by the weighted event probability; ceil groups and enforce allocation block",
        "warnings": [], "provenance": None,
    }
    result.update(allocation_rounding(raw_total, phi))
    parent_inputs = dict(parent_result.get("inputs", {}))
    result["lineage"] = {
        "calculation_type": "conversion",
        "parent_method_id": parent_result["method_id"],
        "consumed_result": consumed,
        "parent_primary_inputs": parent_inputs,
        "parent_inference": {
            key: parent_inputs[key] for key in ("alpha", "power", "sides") if key in parent_inputs
        },
        "transformation": "equation 7.8 required-events to participant-count conversion",
        "child_outputs": [
            {"key": "raw_total", "quantity": "participants", "unit": "participants", "stage": "raw"},
            {"key": "final_total", "quantity": "participants", "unit": "participants", "stage": "final"},
        ],
        "parent_source_provenance": parent_result.get("source_provenance"),
        "parent_validation_evidence": parent_result.get("validation_evidence"),
    }
    return result


schoenfeld_events = contracted(schoenfeld_events)
freedman_events = contracted(freedman_events)
events_to_participants = contracted(events_to_participants)
