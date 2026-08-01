"""Chapter 6 rate-outcome sample-size formulae."""

from __future__ import annotations

from fractions import Fraction
from math import ceil, isfinite, log, sqrt
from typing import Any

from scipy.optimize import brentq
from scipy.stats import poisson

from .distributions import critical_values
from .rounding import allocation_rounding
from .schema_contract import contracted


def _positive(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")


def _probability(name: str, value: float, *, allow_zero: bool = False) -> None:
    lower_ok = value >= 0 if allow_zero else value > 0
    if not isfinite(value) or not lower_ok or value >= 1:
        bound = "[0, 1)" if allow_zero else "(0, 1)"
        raise ValueError(f"{name} must be a finite probability in {bound}")


def bonferroni_alpha(alpha: float, number_of_reactions: int = 1) -> float:
    """Return alpha/s; this is a shared correction, not a sample-size method."""
    if not isinstance(number_of_reactions, int) or isinstance(number_of_reactions, bool) or number_of_reactions < 1:
        raise ValueError("number_of_reactions must be a positive integer")
    if not isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be a finite number strictly between 0 and 1")
    return alpha / number_of_reactions


def _base(method: str, reference: str, inputs: dict[str, Any], raw_total: float) -> dict[str, Any]:
    if not isfinite(raw_total) or raw_total <= 0:
        raise ValueError("inputs do not produce a positive finite sample size")
    final = ceil(raw_total)
    return {
        "method_id": method, "formula_reference": reference, "inputs": inputs,
        "raw_total": raw_total, "raw_group_control": None, "raw_group_treatment": None,
        "rounded_total": final, "rounded_group_control": None,
        "rounded_group_treatment": None, "final_group_control": None,
        "final_group_treatment": None, "final_total": final,
        "rounding_rule": "ceil the unrounded required count", "warnings": [],
        "provenance": {"source": "Sample Size Tables for Clinical Studies, 4th ed.", "chapter": 6, "formula": reference},
    }


def two_group_poisson_rates(*, standard_rate: float,
                            treatment_rate: float | None = None,
                            rate_ratio: float | None = None,
                            allocation_ratio: float = 1.0,
                            exposure_per_subject: float = 1.0,
                            alpha: float = 0.05, power: float = 0.80,
                            sides: int = 2, number_of_reactions: int = 1) -> dict[str, Any]:
    """TWO-013, equations 6.2 and 6.3; allocation is treatment/standard."""
    _positive("standard_rate", standard_rate)
    if (treatment_rate is None) == (rate_ratio is None):
        raise ValueError("provide exactly one of treatment_rate or rate_ratio")
    if rate_ratio is not None:
        _positive("rate_ratio", rate_ratio)
        if rate_ratio == 1:
            raise ValueError("rate_ratio must differ from 1 for a finite exposure")
        treatment = standard_rate * rate_ratio
        path = "equation 6.3 rate-ratio input"
    else:
        treatment = float(treatment_rate)
        _positive("treatment_rate", treatment)
        if treatment == standard_rate:
            raise ValueError("treatment_rate must differ from standard_rate for a finite exposure")
        rate_ratio = treatment / standard_rate
        path = "equation 6.2 direct-rate input"
    _positive("allocation_ratio", allocation_ratio)
    _positive("exposure_per_subject", exposure_per_subject)
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    z_alpha, z_power = critical_values(adjusted_alpha, power, sides)
    phi = allocation_ratio
    raw_exposure = (1 + phi) / phi * (z_alpha + z_power) ** 2 * (
        treatment + phi * standard_rate
    ) / (treatment - standard_rate) ** 2
    raw_total = raw_exposure / exposure_per_subject
    result = _base("TWO-013", "equations 6.2 and 6.3", {
        "standard_rate": standard_rate, "treatment_rate": treatment,
        "rate_ratio": rate_ratio, "input_path": path, "allocation_ratio": phi,
        "exposure_per_subject": exposure_per_subject, "alpha": alpha,
        "adjusted_alpha": adjusted_alpha, "power": power, "sides": sides,
        "number_of_reactions": number_of_reactions, "z_alpha": z_alpha, "z_power": z_power,
    }, raw_total)
    result.update(allocation_rounding(raw_total, phi))
    result.update({
        "raw_total_exposure": raw_exposure,
        "raw_group_control_exposure": raw_exposure / (1 + phi),
        "raw_group_treatment_exposure": phi * raw_exposure / (1 + phi),
    })
    return result


def two_group_negative_binomial_rates(*, standard_rate: float, treatment_rate: float,
                                      overdispersion: float, mean_exposure: float,
                                      allocation_ratio: float = 1.0,
                                      alpha: float = 0.05, power: float = 0.80,
                                      sides: int = 2, number_of_reactions: int = 1) -> dict[str, Any]:
    """TWO-014, equations 6.4 and 6.5."""
    _positive("standard_rate", standard_rate); _positive("treatment_rate", treatment_rate)
    if treatment_rate == standard_rate:
        raise ValueError("treatment_rate must differ from standard_rate for a finite sample size")
    if not isfinite(overdispersion) or overdispersion < 0:
        raise ValueError("overdispersion must be a finite number greater than or equal to 0")
    _positive("mean_exposure", mean_exposure); _positive("allocation_ratio", allocation_ratio)
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    z_alpha, z_power = critical_values(adjusted_alpha, power, sides)
    phi = allocation_ratio
    variance_factor = (1 / mean_exposure) * (
        1 / standard_rate + 1 / (phi * treatment_rate)
    ) + overdispersion * (1 + phi) / phi
    raw_total = (1 + phi) * variance_factor * (z_alpha + z_power) ** 2 / log(
        treatment_rate / standard_rate
    ) ** 2
    result = _base("TWO-014", "equations 6.4 and 6.5", {
        "standard_rate": standard_rate, "treatment_rate": treatment_rate,
        "overdispersion": overdispersion, "mean_exposure": mean_exposure,
        "allocation_ratio": phi, "variance_factor": variance_factor,
        "alpha": alpha, "adjusted_alpha": adjusted_alpha, "power": power,
        "sides": sides, "number_of_reactions": number_of_reactions,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw_total)
    result.update(allocation_rounding(raw_total, phi))
    return result


def _poisson_lower_tail(mean: float, minimum_events: int) -> float:
    return float(poisson.cdf(minimum_events - 1, mean))


def adverse_event_observation(*, planned_rate: float, minimum_events: int,
                              detection_probability: float) -> dict[str, Any]:
    """ONE-003, numerical equation 6.6 with equation 6.7 at a=1."""
    _positive("planned_rate", planned_rate)
    if not isinstance(minimum_events, int) or isinstance(minimum_events, bool) or minimum_events < 1:
        raise ValueError("minimum_events must be a positive integer")
    _probability("detection_probability", detection_probability)
    gamma = 1 - detection_probability
    analytic_mean = -log(gamma) if minimum_events == 1 else None
    upper = max(1.0, float(minimum_events))
    iterations = 0
    while _poisson_lower_tail(upper, minimum_events) > gamma:
        upper *= 2
        iterations += 1
        if upper > 1e12:
            raise ValueError("numerical root is beyond the search limit")
    root, details = brentq(
        lambda mean: _poisson_lower_tail(mean, minimum_events) - gamma,
        0.0, upper, xtol=1e-12, full_output=True,
    )
    raw_total = root / planned_rate
    result = _base("ONE-003", "equations 6.6 and 6.7", {
        "planned_rate": planned_rate, "minimum_events": minimum_events,
        "detection_probability": detection_probability, "gamma": gamma,
        "poisson_mean_at_root": root, "analytic_poisson_mean_a1": analytic_mean,
    }, raw_total)
    result["convergence"] = {
        "method": "Brent bracketed root of Poisson lower-tail probability",
        "converged": bool(details.converged), "iterations": details.iterations,
        "function_calls": details.function_calls, "bracket_expansions": iterations,
        "residual": _poisson_lower_tail(root, minimum_events) - gamma,
        "analytic_numeric_difference_a1": None if analytic_mean is None else root - analytic_mean,
        "direct_detection_probability_at_final": 1 - _poisson_lower_tail(ceil(raw_total) * planned_rate, minimum_events),
    }
    return result


def known_background_increase(*, background_rate: float, additional_rate: float,
                              alpha: float = 0.05, power: float = 0.80,
                              sides: int = 1, number_of_reactions: int = 1) -> dict[str, Any]:
    """ONE-004, equation 6.8."""
    _probability("background_rate", background_rate, allow_zero=True)
    _positive("additional_rate", additional_rate)
    if background_rate + additional_rate >= 1:
        raise ValueError("background_rate + additional_rate must be less than 1")
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    z_alpha, z_power = critical_values(adjusted_alpha, power, sides)
    raw_total = (
        z_alpha * sqrt(background_rate) + z_power * sqrt(background_rate + additional_rate)
    ) ** 2 / additional_rate ** 2
    return _base("ONE-004", "equation 6.8", {
        "background_rate": background_rate, "additional_rate": additional_rate,
        "alpha": alpha, "adjusted_alpha": adjusted_alpha, "power": power,
        "sides": sides, "number_of_reactions": number_of_reactions,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw_total)


def unknown_background_comparison(*, control_rate: float, additional_rate: float,
                                  control_to_treatment_ratio: float = 1.0,
                                  alpha: float = 0.05, power: float = 0.80,
                                  sides: int = 1, number_of_reactions: int = 1) -> dict[str, Any]:
    """TWO-015, equations 6.9 and 6.10; k=control/treatment."""
    _probability("control_rate", control_rate)
    _positive("additional_rate", additional_rate)
    if control_rate + additional_rate >= 1:
        raise ValueError("control_rate + additional_rate must be less than 1")
    _positive("control_to_treatment_ratio", control_to_treatment_ratio)
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    z_alpha, z_power = critical_values(adjusted_alpha, power, sides)
    k = control_to_treatment_ratio
    treatment_rate = control_rate + additional_rate
    pooled = (k * control_rate + treatment_rate) / (k + 1)
    raw_treatment = (
        z_alpha * sqrt((k + 1) * pooled * (1 - pooled))
        + z_power * sqrt(control_rate * (1 - control_rate) + k * treatment_rate * (1 - treatment_rate))
    ) ** 2 / (k * additional_rate ** 2)
    raw_total = (k + 1) * raw_treatment
    result = _base("TWO-015", "equations 6.9 and 6.10", {
        "control_rate": control_rate, "treatment_rate": treatment_rate,
        "additional_rate": additional_rate, "control_to_treatment_ratio": k,
        "allocation_ratio": 1 / k, "pooled_rate": pooled, "alpha": alpha,
        "adjusted_alpha": adjusted_alpha, "power": power, "sides": sides,
        "number_of_reactions": number_of_reactions, "z_alpha": z_alpha, "z_power": z_power,
    }, raw_total)
    # k is an explicit design ratio, not a rounded observation. Preserve it
    # exactly rather than applying the Chapter 3 displayed-precision heuristic.
    ratio = Fraction(str(k)).limit_denominator(10_000)
    control_block, treatment_block = ratio.numerator, ratio.denominator
    raw_control = k * raw_treatment
    blocks = ceil(max(raw_control / control_block, raw_treatment / treatment_block))
    result.update({
        "raw_group_control": raw_control, "raw_group_treatment": raw_treatment,
        "rounded_total": ceil(raw_total), "rounded_group_control": ceil(raw_control),
        "rounded_group_treatment": ceil(raw_treatment),
        "final_group_control": blocks * control_block,
        "final_group_treatment": blocks * treatment_block,
        "final_total": blocks * (control_block + treatment_block),
        "rounding_rule": (
            "ceil raw total and each group; final values preserve the explicit "
            f"control:treatment block {control_block}:{treatment_block}"
        ),
    })
    result["raw_treatment_required"] = raw_treatment
    return result


def matched_case_control(*, control_rate: float, additional_rate: float,
                         controls_per_case: int = 1, alpha: float = 0.05,
                         power: float = 0.80, sides: int = 1,
                         number_of_reactions: int = 1) -> dict[str, Any]:
    """TWO-016, equations 6.11 and 6.12."""
    _probability("control_rate", control_rate)
    _positive("additional_rate", additional_rate)
    if control_rate + additional_rate >= 1:
        raise ValueError("control_rate + additional_rate must be less than 1")
    if not isinstance(controls_per_case, int) or isinstance(controls_per_case, bool) or controls_per_case < 1:
        raise ValueError("controls_per_case must be a positive integer")
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    z_alpha, z_power = critical_values(adjusted_alpha, power, sides)
    m = controls_per_case
    omega = (control_rate + additional_rate) / (1 + additional_rate)
    pooled = control_rate / (1 + m) * (m + omega / control_rate)
    raw_units = (
        z_alpha * sqrt((1 + m) * pooled * (1 - pooled))
        + z_power * sqrt(control_rate * (1 - control_rate) + m * omega * (1 - omega))
    ) ** 2 / (m * (control_rate - omega) ** 2)
    units = ceil(raw_units)
    result = _base("TWO-016", "equations 6.11 and 6.12", {
        "control_rate": control_rate, "additional_rate": additional_rate,
        "controls_per_case": m, "omega": omega, "pooled_rate": pooled,
        "alpha": alpha, "adjusted_alpha": adjusted_alpha, "power": power,
        "sides": sides, "number_of_reactions": number_of_reactions,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw_units)
    result.update({
        "raw_matched_units": raw_units, "raw_group_control": m * raw_units,
        "raw_group_treatment": raw_units, "raw_subject_total": (m + 1) * raw_units,
        "rounded_matched_units": units, "rounded_group_control": m * units,
        "rounded_group_treatment": units, "final_group_control": m * units,
        "final_group_treatment": units, "final_matched_units": units,
        "final_cases": units, "final_controls": m * units,
        "final_total": (m + 1) * units,
        "rounding_rule": "ceil matched units, then multiply by the integer controls-per-case ratio",
    })
    return result


two_group_poisson_rates = contracted(two_group_poisson_rates)
two_group_negative_binomial_rates = contracted(two_group_negative_binomial_rates)
adverse_event_observation = contracted(adverse_event_observation)
known_background_increase = contracted(known_background_increase)
unknown_background_comparison = contracted(unknown_background_comparison)
matched_case_control = contracted(matched_case_control)
