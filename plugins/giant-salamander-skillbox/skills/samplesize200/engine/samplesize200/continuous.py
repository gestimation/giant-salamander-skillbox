"""Chapter 5 continuous-outcome sample-size formulae."""

from __future__ import annotations

from math import ceil, isfinite, pi, sqrt
from statistics import NormalDist
from typing import Any

from scipy.optimize import brentq
from scipy.stats import nct, t

from .distributions import critical_values
from .rounding import allocation_block, allocation_rounding
from .schema_contract import contracted

NORMAL_WMW_EFFICIENCY = pi / 3.0


def _positive(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")


def _effect(value: float) -> float:
    if not isfinite(value) or value == 0:
        raise ValueError("standardized_effect must be finite and nonzero")
    return abs(value)


def _one_result(method_id: str, reference: str, inputs: dict[str, Any], raw: float) -> dict[str, Any]:
    if not isfinite(raw) or raw <= 0:
        raise ValueError("inputs do not produce a positive finite sample size")
    final = ceil(raw)
    return {
        "method_id": method_id, "formula_reference": reference, "inputs": inputs,
        "raw_total": raw, "raw_group_control": None, "raw_group_treatment": None,
        "rounded_total": final, "rounded_group_control": None,
        "rounded_group_treatment": None, "final_total": final,
        "final_group_control": None, "final_group_treatment": None,
        "rounding_rule": "ceil the unrounded sample size", "warnings": [],
    }


def _two_result(method_id: str, reference: str, inputs: dict[str, Any], raw: float) -> dict[str, Any]:
    result = _one_result(method_id, reference, inputs, raw)
    result.update(allocation_rounding(raw, float(inputs["allocation_ratio"])))
    return result


def one_sample_mean(*, known_mean: float, planned_mean: float, planned_sd: float,
                    alpha: float = 0.05, power: float = 0.80, sides: int = 2) -> dict[str, Any]:
    _positive("planned_sd", planned_sd)
    if not isfinite(known_mean) or not isfinite(planned_mean):
        raise ValueError("means must be finite")
    if planned_mean == known_mean:
        raise ValueError("planned_mean must differ from known_mean for a finite sample size")
    z_alpha, z_power = critical_values(alpha, power, sides)
    delta = abs(planned_mean - known_mean) / planned_sd
    raw = (z_alpha + z_power) ** 2 / delta ** 2 + z_alpha ** 2 / 2.0
    return _one_result("ONE-002", "equation 5.11", {
        "known_mean": known_mean, "planned_mean": planned_mean, "planned_sd": planned_sd,
        "standardized_effect": delta, "alpha": alpha, "power": power, "sides": sides,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw)


def two_sample_mean_guenther(*, standardized_effect: float, allocation_ratio: float = 1.0,
                             alpha: float = 0.05, power: float = 0.80,
                             sides: int = 2) -> dict[str, Any]:
    delta = _effect(standardized_effect)
    _positive("allocation_ratio", allocation_ratio)
    z_alpha, z_power = critical_values(alpha, power, sides)
    raw = ((1.0 + allocation_ratio) ** 2 / allocation_ratio) * (
        z_alpha + z_power
    ) ** 2 / delta ** 2 + z_alpha ** 2 / 2.0
    return _two_result("TWO-009", "equation 5.4", {
        "standardized_effect": delta, "allocation_ratio": allocation_ratio,
        "alpha": alpha, "power": power, "sides": sides,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw)


def _nct_power(total: float, delta: float, phi: float, alpha: float, sides: int) -> float:
    df = total - 2.0
    if df <= 0:
        return 0.0
    psi = delta * sqrt(phi * total) / (1.0 + phi)
    if sides == 2:
        critical = t.ppf(1.0 - alpha / 2.0, df)
        return float(nct.cdf(-critical, df, psi) + nct.sf(critical, df, psi))
    critical = t.ppf(1.0 - alpha, df)
    return float(nct.sf(critical, df, psi))


def two_sample_mean_exact(*, standardized_effect: float, allocation_ratio: float = 1.0,
                          alpha: float = 0.05, power: float = 0.80,
                          sides: int = 2) -> dict[str, Any]:
    delta = _effect(standardized_effect)
    _positive("allocation_ratio", allocation_ratio)
    critical_values(alpha, power, sides)
    # At least two observations per group are required to estimate variance.
    lower, upper = 4.0, 4.0
    while _nct_power(upper, delta, allocation_ratio, alpha, sides) < power:
        upper *= 2.0
        if upper > 1_000_000_000:
            raise ValueError("target power requires a sample size beyond the search limit")
    raw = brentq(
        lambda total: _nct_power(total, delta, allocation_ratio, alpha, sides) - power,
        lower, upper, xtol=1e-10,
    )
    control_block, treatment_block = allocation_block(allocation_ratio)
    block_total = control_block + treatment_block
    blocks = max(ceil(2 / control_block), ceil(2 / treatment_block), ceil(raw / block_total))
    while _nct_power(blocks * block_total, delta, allocation_ratio, alpha, sides) < power:
        blocks += 1
    final_total = blocks * block_total
    result = _two_result("TWO-008", "equations 5.2 and 5.3", {
        "standardized_effect": delta, "allocation_ratio": allocation_ratio,
        "alpha": alpha, "power": power, "sides": sides,
        "degrees_of_freedom": final_total - 2,
        "noncentrality": delta * sqrt(allocation_ratio * final_total) / (1.0 + allocation_ratio),
        "achieved_power": _nct_power(final_total, delta, allocation_ratio, alpha, sides),
    }, raw)
    result["final_group_control"] = blocks * control_block
    result["final_group_treatment"] = blocks * treatment_block
    result["final_total"] = final_total
    result["rounding_rule"] = (
        "solve the continuous noncentral-t power equation, then choose the smallest "
        f"feasible allocation block {control_block}:{treatment_block} attaining target power"
    )
    return result


def two_sample_mean_satterthwaite(*, planned_mean_difference: float,
                                  control_sd: float, treatment_sd: float,
                                  allocation_ratio: float = 1.0,
                                  variance_ratio: float | None = None,
                                  alpha: float = 0.05, power: float = 0.80,
                                  sides: int = 2) -> dict[str, Any]:
    _positive("control_sd", control_sd)
    _positive("treatment_sd", treatment_sd)
    _positive("allocation_ratio", allocation_ratio)
    if not isfinite(planned_mean_difference) or planned_mean_difference == 0:
        raise ValueError("planned_mean_difference must be finite and nonzero")
    tau = (treatment_sd / control_sd) ** 2
    if variance_ratio is not None:
        _positive("variance_ratio", variance_ratio)
        if abs(variance_ratio - tau) > max(1e-12, tau * 1e-10):
            raise ValueError("variance_ratio must equal treatment variance / control variance")
    delta = abs(planned_mean_difference) / control_sd
    phi = allocation_ratio
    z_alpha, z_power = critical_values(alpha, power, sides)
    raw = (1.0 + phi) / phi * (
        (tau + phi) * (z_alpha + z_power) ** 2 / delta ** 2
        + (tau ** 2 + phi ** 3) * z_alpha ** 2 / (2.0 * (tau + phi) ** 2)
    )
    return _two_result("TWO-010", "equation 5.6", {
        "planned_mean_difference": planned_mean_difference, "control_sd": control_sd,
        "treatment_sd": treatment_sd, "standardized_effect": delta,
        "variance_ratio": tau, "variance_ratio_definition": "treatment variance / control variance",
        "allocation_ratio": phi, "allocation_ratio_definition": "treatment / control",
        "alpha": alpha, "power": power, "sides": sides,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw)


def wmw_efficiency(*, standardized_effect: float, efficiency_factor: float,
                   allocation_ratio: float = 1.0, alpha: float = 0.05,
                   power: float = 0.80, sides: int = 2) -> dict[str, Any]:
    delta = _effect(standardized_effect)
    _positive("efficiency_factor", efficiency_factor)
    _positive("allocation_ratio", allocation_ratio)
    z_alpha, z_power = critical_values(alpha, power, sides)
    raw = efficiency_factor * ((1.0 + allocation_ratio) ** 2 / allocation_ratio) * (
        z_alpha + z_power
    ) ** 2 / delta ** 2 + z_alpha ** 2 / 2.0
    return _two_result("TWO-011", "equations 5.7 and 5.8", {
        "standardized_effect": delta, "efficiency_factor": efficiency_factor,
        "allocation_ratio": allocation_ratio, "alpha": alpha, "power": power,
        "sides": sides, "z_alpha": z_alpha, "z_power": z_power,
    }, raw)


def superiority_probability_from_effect(standardized_effect: float) -> float:
    if not isfinite(standardized_effect):
        raise ValueError("standardized_effect must be finite")
    return NormalDist().cdf(standardized_effect / sqrt(2.0))


def wmw_superiority(*, superiority_probability: float | None = None,
                    standardized_effect: float | None = None,
                    allocation_ratio: float = 1.0, alpha: float = 0.05,
                    power: float = 0.80, sides: int = 2) -> dict[str, Any]:
    if (superiority_probability is None) == (standardized_effect is None):
        raise ValueError("provide exactly one of superiority_probability or standardized_effect")
    if standardized_effect is not None:
        if standardized_effect == 0:
            raise ValueError("standardized_effect must be nonzero for a finite sample size")
        probability = superiority_probability_from_effect(standardized_effect)
        input_path = "equation 5.10 from standardized_effect"
    else:
        probability = float(superiority_probability)
        input_path = "direct superiority_probability"
    if not isfinite(probability) or not 0.0 < probability < 1.0:
        raise ValueError("superiority_probability must be strictly between 0 and 1")
    if probability == 0.5:
        raise ValueError("superiority_probability must differ from 0.5 for a finite sample size")
    _positive("allocation_ratio", allocation_ratio)
    z_alpha, z_power = critical_values(alpha, power, sides)
    raw = ((1.0 + allocation_ratio) ** 2 / (12.0 * allocation_ratio)) * (
        z_alpha + z_power
    ) ** 2 / (probability - 0.5) ** 2
    return _two_result("TWO-012", "equations 5.9 and 5.10", {
        "superiority_probability": probability, "standardized_effect": standardized_effect,
        "probability_input_path": input_path, "allocation_ratio": allocation_ratio,
        "alpha": alpha, "power": power, "sides": sides,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw)


one_sample_mean = contracted(one_sample_mean)
two_sample_mean_exact = contracted(two_sample_mean_exact)
two_sample_mean_guenther = contracted(two_sample_mean_guenther)
two_sample_mean_satterthwaite = contracted(two_sample_mean_satterthwaite)
wmw_efficiency = contracted(wmw_efficiency)
wmw_superiority = contracted(wmw_superiority)
