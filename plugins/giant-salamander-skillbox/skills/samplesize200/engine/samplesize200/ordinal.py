"""Chapter 4 ordinal-outcome sample-size formulae.

The allocation ratio is always treatment/control.  Category probabilities are
ordered from the lowest to the highest response category.
"""

from __future__ import annotations

from math import isclose, isfinite, log
from typing import Any, Sequence

from .distributions import critical_values
from .rounding import allocation_rounding
from .schema_contract import contracted


def _positive(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")


def _probabilities(name: str, values: Sequence[float]) -> list[float]:
    result = [float(value) for value in values]
    if len(result) < 2:
        raise ValueError(f"{name} must contain at least two categories")
    if any(not isfinite(value) or value < 0 or value > 1 for value in result):
        raise ValueError(f"{name} must contain finite probabilities in [0, 1]")
    if not isclose(sum(result), 1.0, rel_tol=0.0, abs_tol=1e-8):
        raise ValueError(f"{name} must sum to 1")
    return result


def _odds_ratio(value: float) -> float:
    _positive("odds_ratio", value)
    if value == 1:
        raise ValueError("odds_ratio must differ from 1 for a finite sample size")
    return float(value)


def _result(method_id: str, reference: str, inputs: dict[str, Any], raw: float,
            extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isfinite(raw) or raw <= 0:
        raise ValueError("inputs do not produce a positive finite sample size")
    result: dict[str, Any] = {
        "method_id": method_id,
        "formula_reference": reference,
        "inputs": inputs,
        "raw_total": raw,
        "warnings": [],
        "provenance": None,
    }
    result.update(allocation_rounding(raw, float(inputs["allocation_ratio"])))
    if extra:
        result.update(extra)
    return result


def _proportional_treatment(control: Sequence[float], odds_ratio: float) -> list[float]:
    cumulative = 0.0
    treatment_cumulative: list[float] = []
    for probability in control[:-1]:
        cumulative += probability
        treatment_cumulative.append(
            cumulative * odds_ratio / (1.0 - cumulative + cumulative * odds_ratio)
        )
    result: list[float] = []
    previous = 0.0
    for value in treatment_cumulative:
        result.append(value - previous)
        previous = value
    result.append(1.0 - previous)
    return result


def proportional_odds(*, control_proportions: Sequence[float], odds_ratio: float,
                      allocation_ratio: float = 1.0, alpha: float = 0.05,
                      power: float = 0.80, sides: int = 2,
                      gamma_from_control_only: bool = False,
                      gamma_proportions: Sequence[float] | None = None) -> dict[str, Any]:
    """TWO-004: equations 4.2--4.4, formal proportional-odds method."""
    control = _probabilities("control_proportions", control_proportions)
    odds_ratio = _odds_ratio(odds_ratio)
    _positive("allocation_ratio", allocation_ratio)
    z_alpha, z_power = critical_values(alpha, power, sides)
    treatment = _proportional_treatment(control, odds_ratio)
    if gamma_proportions is not None:
        gamma_values = _probabilities("gamma_proportions", gamma_proportions)
        if len(gamma_values) != len(control):
            raise ValueError("gamma_proportions must have the same categories as control_proportions")
    elif gamma_from_control_only:
        gamma_values = control
    else:
        gamma_values = [(left + right) / 2.0 for left, right in zip(control, treatment)]
    denominator = 1.0 - sum(value ** 3 for value in gamma_values)
    if denominator <= 0:
        raise ValueError("category probabilities do not produce a finite Gamma")
    gamma = 3.0 / denominator
    raw = gamma * (1.0 + allocation_ratio) ** 2 / allocation_ratio * (
        z_alpha + z_power
    ) ** 2 / log(odds_ratio) ** 2
    return _result("TWO-004", "equations 4.2, 4.3 and 4.4", {
        "control_proportions": control,
        "odds_ratio": odds_ratio,
        "allocation_ratio": allocation_ratio,
        "allocation_ratio_definition": "treatment / control",
        "alpha": alpha,
        "power": power,
        "sides": sides,
        "gamma_from_control_only": gamma_from_control_only,
        "gamma_proportions_input": list(gamma_proportions) if gamma_proportions is not None else None,
        "z_alpha": z_alpha,
        "z_power": z_power,
    }, raw, {
        "derived_treatment_proportions": treatment,
        "gamma_proportions": gamma_values,
        "gamma_denominator": denominator,
        "gamma": gamma,
    })


def equal_category_approximation(*, category_count: int, odds_ratio: float,
                                 allocation_ratio: float = 1.0,
                                 alpha: float = 0.05, power: float = 0.80,
                                 sides: int = 2) -> dict[str, Any]:
    """TWO-005: equation 4.6 inserted into equation 4.3."""
    if isinstance(category_count, bool) or not isinstance(category_count, int) or category_count < 2:
        raise ValueError("category_count must be an integer of at least 2")
    odds_ratio = _odds_ratio(odds_ratio)
    _positive("allocation_ratio", allocation_ratio)
    z_alpha, z_power = critical_values(alpha, power, sides)
    gamma = 3.0 / (1.0 - 1.0 / category_count ** 2)
    raw = gamma * (1.0 + allocation_ratio) ** 2 / allocation_ratio * (
        z_alpha + z_power
    ) ** 2 / log(odds_ratio) ** 2
    return _result("TWO-005", "equations 4.3 and 4.6", {
        "category_count": category_count,
        "odds_ratio": odds_ratio,
        "allocation_ratio": allocation_ratio,
        "allocation_ratio_definition": "treatment / control",
        "alpha": alpha,
        "power": power,
        "sides": sides,
        "z_alpha": z_alpha,
        "z_power": z_power,
    }, raw, {"gamma": gamma})


def many_category_approximation(*, category_count: int, odds_ratio: float,
                                allocation_ratio: float = 1.0,
                                alpha: float = 0.05, power: float = 0.80,
                                sides: int = 2) -> dict[str, Any]:
    """TWO-006: equation 4.7, restricted to its stated kappa > 5 domain."""
    if isinstance(category_count, bool) or not isinstance(category_count, int) or category_count <= 5:
        raise ValueError("category_count must be an integer greater than 5 for equation 4.7")
    odds_ratio = _odds_ratio(odds_ratio)
    _positive("allocation_ratio", allocation_ratio)
    z_alpha, z_power = critical_values(alpha, power, sides)
    raw = 3.0 * (1.0 + allocation_ratio) ** 2 / allocation_ratio * (
        z_alpha + z_power
    ) ** 2 / log(odds_ratio) ** 2
    return _result("TWO-006", "equation 4.7", {
        "category_count": category_count,
        "odds_ratio": odds_ratio,
        "allocation_ratio": allocation_ratio,
        "allocation_ratio_definition": "treatment / control",
        "alpha": alpha,
        "power": power,
        "sides": sides,
        "z_alpha": z_alpha,
        "z_power": z_power,
    }, raw, {"gamma_approximation": 3.0})


def mann_whitney_nonproportional(*, standard_proportions: Sequence[float],
                                 treatment_proportions: Sequence[float],
                                 allocation_ratio: float = 1.0,
                                 alpha: float = 0.05, power: float = 0.80,
                                 sides: int = 2) -> dict[str, Any]:
    """TWO-007: equation 4.8, tie-adjusted Mann--Whitney method."""
    standard = _probabilities("standard_proportions", standard_proportions)
    treatment = _probabilities("treatment_proportions", treatment_proportions)
    if len(standard) != len(treatment):
        raise ValueError("standard_proportions and treatment_proportions must have equal length")
    _positive("allocation_ratio", allocation_ratio)
    z_alpha, z_power = critical_values(alpha, power, sides)
    phi = allocation_ratio
    variance_term = 1.0 - sum(
        (phi * left + right) ** 3 for left, right in zip(standard, treatment)
    ) / (1.0 + phi) ** 3
    superiority = 0.0
    treatment_below = 0.0
    for left, right in zip(standard, treatment):
        superiority += left * treatment_below
        treatment_below += right
    superiority += 0.5 * sum(left * right for left, right in zip(standard, treatment))
    effect = superiority - 0.5
    if isclose(effect, 0.0, rel_tol=0.0, abs_tol=1e-15):
        raise ValueError("the Mann-Whitney superiority probability is 0.5; sample size is infinite")
    raw = (1.0 + phi) ** 2 / (12.0 * phi) * (z_alpha + z_power) ** 2 * (
        variance_term / effect ** 2
    )
    return _result("TWO-007", "equation 4.8", {
        "standard_proportions": standard,
        "treatment_proportions": treatment,
        "allocation_ratio": phi,
        "allocation_ratio_definition": "treatment / standard",
        "alpha": alpha,
        "power": power,
        "sides": sides,
        "z_alpha": z_alpha,
        "z_power": z_power,
    }, raw, {
        "variance_term": variance_term,
        "superiority_probability": superiority,
        "mann_whitney_effect": effect,
    })


proportional_odds = contracted(proportional_odds)
equal_category_approximation = contracted(equal_category_approximation)
many_category_approximation = contracted(many_category_approximation)
mann_whitney_nonproportional = contracted(mann_whitney_nonproportional)
