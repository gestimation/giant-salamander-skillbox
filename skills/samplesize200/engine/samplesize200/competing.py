"""Chapter 7 competing-risk sample-size calculations.

The public functions retain the book's four planning stages explicitly:
required interest events, arm-specific interest-event probabilities,
participants, and integer/allocation adjustment.
"""

from __future__ import annotations

from math import exp, isfinite, log
from typing import Any, Sequence

from .rounding import allocation_rounding
from .schema_contract import contracted
from .survival import schoenfeld_events


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")
    return value


def _probability(name: str, value: float, *, allow_zero: bool = False) -> float:
    value = float(value)
    lower_ok = value >= 0 if allow_zero else value > 0
    if not isfinite(value) or not lower_ok or value >= 1:
        interval = "[0, 1)" if allow_zero else "(0, 1)"
        raise ValueError(f"{name} must be a finite probability in {interval}")
    return value


def _hazards(name: str, interest: float, competing: Sequence[float]) -> tuple[float, list[float]]:
    interest = _positive(f"{name}_interest_hazard", interest)
    competing_values = [_positive(f"{name}_competing_hazard", value) for value in competing]
    return interest, competing_values


def cause_hazards_from_cifs(*, interest_cif: float, competing_cifs: Sequence[float],
                            reference_time: float) -> dict[str, Any]:
    """Equation 7.10 generalized to one interest and several competing causes."""
    time = _positive("reference_time", reference_time)
    interest = _probability("interest_cif", interest_cif)
    competing = [_probability("competing_cif", value, allow_zero=True) for value in competing_cifs]
    total_cif = interest + sum(competing)
    if total_cif >= 1:
        raise ValueError("the sum of cause-specific cumulative incidences must be less than 1")
    total_hazard = -log(1 - total_cif) / time
    scale = total_hazard / total_cif
    return {
        "interest_hazard": interest * scale,
        "competing_hazards": [value * scale for value in competing],
        "total_hazard": total_hazard,
        "reference_time": time,
        "total_cif": total_cif,
        "formula_reference": "equation 7.10",
    }


def _cause_event_probability(interest: float, competing: Sequence[float],
                             accrual: float, followup: float) -> float:
    total = interest + sum(competing)
    bracket = 1 - (exp(-total * followup) - exp(-total * (followup + accrual))) / (total * accrual)
    return interest / total * bracket


def _derive_subdistribution_ratio(standard_cif: float, treatment_cif: float) -> float:
    standard = _probability("standard_interest_cif", standard_cif)
    treatment = _probability("treatment_interest_cif", treatment_cif)
    return log(1 - treatment) / log(1 - standard)


def _result(*, method_id: str, formula_reference: str, effect_name: str,
            effect_value: float, event_result: dict[str, Any], standard_probability: float,
            treatment_probability: float, allocation_ratio: float,
            inputs: dict[str, Any], probability_details: dict[str, Any]) -> dict[str, Any]:
    phi = _positive("allocation_ratio", allocation_ratio)
    weighted_probability = (standard_probability + phi * treatment_probability) / (1 + phi)
    consumed_events = event_result["rounded_events"]
    raw_total = consumed_events / weighted_probability
    result: dict[str, Any] = {
        "method_id": method_id,
        "formula_reference": formula_reference,
        "inputs": inputs,
        "effect_metric": {"scale": effect_name, "direction": "treatment / standard", "value": effect_value},
        "raw_required_events": event_result["raw_events"],
        "rounded_required_events": event_result["rounded_events"],
        "consumed_required_events": consumed_events,
        "consumed_event_stage": "rounded",
        "standard_interest_event_probability": standard_probability,
        "treatment_interest_event_probability": treatment_probability,
        "weighted_interest_event_probability": weighted_probability,
        "event_probability_details": probability_details,
        "raw_total": raw_total,
        "warnings": [],
        "provenance": None,
        "calculation_stages": [
            {"stage": 1, "name": "effect_and_required_events", "effect_metric": effect_name,
             "raw_events": event_result["raw_events"], "rounded_events": consumed_events},
            {"stage": 2, "name": "arm_interest_event_probabilities",
             "standard": standard_probability, "treatment": treatment_probability,
             "weighted": weighted_probability},
            {"stage": 3, "name": "required_participants", "raw_total": raw_total},
            {"stage": 4, "name": "allocation_and_integer_constraints"},
        ],
        "internal_components": {
            "event_method_id": "TWO-017",
            "event_formula_reference": "equation 7.6",
            "event_inputs": event_result["inputs"],
            "event_result_key": "rounded_events",
            "event_quantity": "events", "event_unit": "events", "event_stage": "rounded",
            "participant_conversion": "equations 7.12 and 7.13",
        },
    }
    result.update(allocation_rounding(raw_total, phi))
    result["calculation_stages"][3].update({
        "rounded_total": result["rounded_total"],
        "rounded_group_control": result["rounded_group_control"],
        "rounded_group_treatment": result["rounded_group_treatment"],
        "final_group_control": result["final_group_control"],
        "final_group_treatment": result["final_group_treatment"],
        "final_total": result["final_total"],
    })
    result["lineage"] = {
        "calculation_type": "composite",
        "parent_method_id": "TWO-017",
        "consumed_result": {"key": "rounded_events", "value": consumed_events,
                            "quantity": "events", "unit": "events", "stage": "rounded"},
        "parent_primary_inputs": event_result["inputs"],
        "parent_inference": {key: event_result["inputs"][key] for key in ("alpha", "power", "sides")},
        "transformation": "arm event probabilities, weighted event probability, participant conversion, allocation block",
        "child_outputs": [
            {"key": "raw_total", "quantity": "participants", "unit": "participants", "stage": "raw"},
            {"key": "final_total", "quantity": "participants", "unit": "participants", "stage": "final"},
        ],
    }
    return result


def cause_specific_hazard_competing_risk(*, cause_specific_hazard_ratio: float,
                                         standard_interest_hazard: float,
                                         standard_competing_hazards: Sequence[float],
                                         treatment_interest_hazard: float,
                                         treatment_competing_hazards: Sequence[float],
                                         accrual_duration: float,
                                         additional_followup: float,
                                         allocation_ratio: float = 1.0,
                                         alpha: float = 0.05, power: float = 0.80,
                                         sides: int = 2) -> dict[str, Any]:
    """TWO-020: cause-specific hazard design, equations 7.6 and 7.11--7.13."""
    ratio = _positive("cause_specific_hazard_ratio", cause_specific_hazard_ratio)
    if ratio == 1:
        raise ValueError("cause_specific_hazard_ratio must differ from 1")
    phi = _positive("allocation_ratio", allocation_ratio)
    accrual = _positive("accrual_duration", accrual_duration)
    followup = _positive("additional_followup", additional_followup)
    standard_interest, standard_competing = _hazards("standard", standard_interest_hazard, standard_competing_hazards)
    treatment_interest, treatment_competing = _hazards("treatment", treatment_interest_hazard, treatment_competing_hazards)
    standard_probability = _cause_event_probability(standard_interest, standard_competing, accrual, followup)
    treatment_probability = _cause_event_probability(treatment_interest, treatment_competing, accrual, followup)
    event_result = schoenfeld_events(hazard_ratio=ratio, allocation_ratio=phi,
                                     alpha=alpha, power=power, sides=sides)
    inputs = {
        "cause_specific_hazard_ratio": ratio,
        "cause_specific_hazard_ratio_definition": "treatment cause-specific hazard / standard cause-specific hazard",
        "standard_interest_hazard": standard_interest,
        "standard_competing_hazards": standard_competing,
        "treatment_interest_hazard": treatment_interest,
        "treatment_competing_hazards": treatment_competing,
        "hazard_unit": "per time unit",
        "accrual_duration": accrual, "additional_followup": followup,
        "allocation_ratio": phi, "allocation_ratio_definition": "treatment / standard",
        "alpha": alpha, "power": power, "sides": sides,
    }
    return _result(
        method_id="TWO-020", formula_reference="equations 7.6, 7.11, 7.12, and 7.13",
        effect_name="cause_specific_hazard_ratio", effect_value=ratio,
        event_result=event_result, standard_probability=standard_probability,
        treatment_probability=treatment_probability, allocation_ratio=phi, inputs=inputs,
        probability_details={"model": "constant cause-specific hazards with uniform accrual",
                             "formula_reference": "equation 7.11"},
    )


def subdistribution_fixed_censoring(*, standard_interest_cif: float,
                                    treatment_interest_cif: float,
                                    standard_censoring_probability: float,
                                    treatment_censoring_probability: float,
                                    subdistribution_hazard_ratio: float | None = None,
                                    allocation_ratio: float = 1.0,
                                    alpha: float = 0.05, power: float = 0.80,
                                    sides: int = 2) -> dict[str, Any]:
    """TWO-021: subdistribution-hazard design with fixed-time censoring."""
    standard = _probability("standard_interest_cif", standard_interest_cif)
    treatment = _probability("treatment_interest_cif", treatment_interest_cif)
    standard_censoring = _probability("standard_censoring_probability", standard_censoring_probability, allow_zero=True)
    treatment_censoring = _probability("treatment_censoring_probability", treatment_censoring_probability, allow_zero=True)
    derived = _derive_subdistribution_ratio(standard, treatment)
    ratio = derived if subdistribution_hazard_ratio is None else _positive("subdistribution_hazard_ratio", subdistribution_hazard_ratio)
    if ratio == 1:
        raise ValueError("subdistribution_hazard_ratio must differ from 1")
    phi = _positive("allocation_ratio", allocation_ratio)
    standard_probability = (1 - standard_censoring) * standard
    treatment_probability = (1 - treatment_censoring) * treatment
    event_result = schoenfeld_events(hazard_ratio=ratio, allocation_ratio=phi,
                                     alpha=alpha, power=power, sides=sides)
    inputs = {
        "standard_interest_cif": standard, "treatment_interest_cif": treatment,
        "standard_censoring_probability": standard_censoring,
        "treatment_censoring_probability": treatment_censoring,
        "subdistribution_hazard_ratio": ratio,
        "subdistribution_hazard_ratio_definition": "treatment subdistribution hazard / standard subdistribution hazard",
        "derived_subdistribution_hazard_ratio_equation_7_14": derived,
        "effect_input_path": "derived_from_CIFs" if subdistribution_hazard_ratio is None else "explicit",
        "allocation_ratio": phi, "allocation_ratio_definition": "treatment / standard",
        "alpha": alpha, "power": power, "sides": sides,
    }
    result = _result(
        method_id="TWO-021", formula_reference="equations 7.6, 7.14, 7.16, 7.12, and 7.13",
        effect_name="subdistribution_hazard_ratio", effect_value=ratio,
        event_result=event_result, standard_probability=standard_probability,
        treatment_probability=treatment_probability, allocation_ratio=phi, inputs=inputs,
        probability_details={"model": "fixed-time censoring applied to cumulative incidence",
                             "formula_reference": "equation 7.16"},
    )
    if subdistribution_hazard_ratio is not None and abs(ratio - derived) > 1e-10:
        result["warnings"].append(
            "explicit subdistribution_hazard_ratio differs from equation 7.14 applied to the supplied CIFs; "
            "the explicit effect is used while CIFs determine event probabilities"
        )
    return result


def subdistribution_accrual_integration(*, standard_interest_cif: float,
                                        treatment_interest_cif: float,
                                        reference_time: float,
                                        accrual_duration: float,
                                        additional_followup: float,
                                        subdistribution_hazard_ratio: float | None = None,
                                        allocation_ratio: float = 1.0,
                                        alpha: float = 0.05, power: float = 0.80,
                                        sides: int = 2) -> dict[str, Any]:
    """TWO-022: subdistribution-hazard design with Simpson accrual integration."""
    standard = _probability("standard_interest_cif", standard_interest_cif)
    treatment = _probability("treatment_interest_cif", treatment_interest_cif)
    reference = _positive("reference_time", reference_time)
    accrual = _positive("accrual_duration", accrual_duration)
    followup = _positive("additional_followup", additional_followup)
    derived = _derive_subdistribution_ratio(standard, treatment)
    ratio = derived if subdistribution_hazard_ratio is None else _positive("subdistribution_hazard_ratio", subdistribution_hazard_ratio)
    if ratio == 1:
        raise ValueError("subdistribution_hazard_ratio must differ from 1")
    phi = _positive("allocation_ratio", allocation_ratio)
    standard_lambda = -log(1 - standard) / reference
    treatment_lambda = -log(1 - treatment) / reference
    times = [followup, followup + accrual / 2, followup + accrual]
    weights = [1, 4, 1]

    def integrate(rate: float) -> tuple[float, list[float]]:
        values = [1 - exp(-rate * time) for time in times]
        return sum(weight * value for weight, value in zip(weights, values)) / 6, values

    standard_probability, standard_nodes = integrate(standard_lambda)
    treatment_probability, treatment_nodes = integrate(treatment_lambda)
    event_result = schoenfeld_events(hazard_ratio=ratio, allocation_ratio=phi,
                                     alpha=alpha, power=power, sides=sides)
    inputs = {
        "standard_interest_cif": standard, "treatment_interest_cif": treatment,
        "reference_time": reference, "accrual_duration": accrual,
        "additional_followup": followup,
        "subdistribution_hazard_ratio": ratio,
        "subdistribution_hazard_ratio_definition": "treatment subdistribution hazard / standard subdistribution hazard",
        "derived_subdistribution_hazard_ratio_equation_7_14": derived,
        "effect_input_path": "derived_from_CIFs" if subdistribution_hazard_ratio is None else "explicit",
        "allocation_ratio": phi, "allocation_ratio_definition": "treatment / standard",
        "alpha": alpha, "power": power, "sides": sides,
    }
    details = {
        "model": "exponential cumulative incidence with uniform accrual",
        "formula_reference": "equations 7.15 and 7.17",
        "integration_method": "three-point Simpson rule",
        "integration_nodes": times, "integration_weights": weights,
        "standard_subdistribution_rate": standard_lambda,
        "treatment_subdistribution_rate": treatment_lambda,
        "standard_node_cifs": standard_nodes,
        "treatment_node_cifs": treatment_nodes,
        "convergence": {"iterative": False, "fixed_nodes": 3, "tolerance": None,
                        "search_range": None, "converged": True},
    }
    result = _result(
        method_id="TWO-022", formula_reference="equations 7.6, 7.14, 7.15, 7.17, 7.12, and 7.13",
        effect_name="subdistribution_hazard_ratio", effect_value=ratio,
        event_result=event_result, standard_probability=standard_probability,
        treatment_probability=treatment_probability, allocation_ratio=phi, inputs=inputs,
        probability_details=details,
    )
    if subdistribution_hazard_ratio is not None and abs(ratio - derived) > 1e-10:
        result["warnings"].append(
            "explicit subdistribution_hazard_ratio differs from equation 7.14 applied to the supplied CIFs; "
            "the explicit effect is used while CIFs determine event probabilities"
        )
    return result


cause_specific_hazard_competing_risk = contracted(cause_specific_hazard_competing_risk)
subdistribution_fixed_censoring = contracted(subdistribution_fixed_censoring)
subdistribution_accrual_integration = contracted(subdistribution_accrual_integration)
