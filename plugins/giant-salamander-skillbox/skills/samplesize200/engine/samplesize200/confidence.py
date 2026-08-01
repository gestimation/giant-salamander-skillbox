"""Chapter 9 confidence-interval precision sample-size calculations.

Definitions used throughout:
* width is the full interval width, upper limit minus lower limit;
* half_width is width / 2;
* relative_precision is half_width divided by the magnitude of the planned
  estimand.  Formulae using another definition expose it explicitly.

These are provisional method-level interfaces, not a final cross-chapter API.
"""

from __future__ import annotations

from math import ceil, isfinite, log, sqrt
from typing import Any

from scipy.optimize import brentq
from scipy.stats import t

from .distributions import normal_quantile
from .rounding import allocation_block, allocation_rounding
from .schema_contract import contracted, consume_quantity, correction_lineage


def _alpha(value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 < value < 1:
        raise ValueError("alpha must be a finite number strictly between 0 and 1")
    return value


def _probability(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be a finite probability in [0, 1]")
    return value


def _strict_probability(name: str, value: float) -> float:
    value = _probability(name, value)
    if value in (0, 1):
        raise ValueError(f"{name} must be strictly between 0 and 1 for this approximation")
    return value


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")
    return value


def _width(value: float) -> float:
    value = _positive("width", value)
    if value > 1:
        raise ValueError("a proportion confidence-interval width cannot exceed 1")
    return value


def _z(alpha: float) -> float:
    return normal_quantile(1 - _alpha(alpha) / 2)


def _one_result(method_id: str, reference: str, inputs: dict[str, Any], raw: float,
                *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isfinite(raw) or raw <= 0:
        raise ValueError("inputs do not produce a positive finite sample size")
    final = ceil(raw)
    result: dict[str, Any] = {
        "method_id": method_id, "formula_reference": reference, "inputs": inputs,
        "raw_total": raw, "raw_group_control": None, "raw_group_treatment": None,
        "rounded_total": final, "rounded_group_control": None,
        "rounded_group_treatment": None, "final_group_control": None,
        "final_group_treatment": None, "final_total": final,
        "rounding_rule": "ceil the unrounded sample size", "warnings": [],
        "provenance": None,
    }
    if extra:
        result.update(extra)
    return result


def _two_result(method_id: str, reference: str, inputs: dict[str, Any], raw: float,
                *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    result = _one_result(method_id, reference, inputs, raw, extra=extra)
    result.update(allocation_rounding(raw, float(inputs["allocation_ratio"])))
    return result


def one_proportion_normal_absolute(*, planned_proportion: float, width: float,
                                   alpha: float = 0.05) -> dict[str, Any]:
    """CI-001: equation 9.2, normal approximation and full absolute width."""
    proportion = _strict_probability("planned_proportion", planned_proportion)
    width = _width(width)
    z = _z(alpha)
    raw = 4 * proportion * (1 - proportion) * z ** 2 / width ** 2
    return _one_result("CI-001", "equation 9.2", {
        "planned_proportion": proportion, "width": width,
        "width_definition": "full width = upper limit - lower limit",
        "half_width": width / 2, "relative_precision": width / (2 * proportion),
        "relative_precision_definition": "half_width / planned_proportion",
        "alpha": alpha, "sides": 2, "z_alpha": z,
    }, raw)


def one_proportion_normal_relative(*, planned_proportion: float,
                                   relative_precision: float,
                                   alpha: float = 0.05) -> dict[str, Any]:
    """CI-002: equation 9.3, relative precision epsilon."""
    proportion = _strict_probability("planned_proportion", planned_proportion)
    epsilon = _positive("relative_precision", relative_precision)
    z = _z(alpha)
    width = 2 * proportion * epsilon
    if width > 1:
        raise ValueError("relative_precision implies a proportion interval wider than 1")
    raw = (1 - proportion) * z ** 2 / (proportion * epsilon ** 2)
    return _one_result("CI-002", "equation 9.3", {
        "planned_proportion": proportion, "width": width,
        "width_definition": "full width = 2 * planned_proportion * relative_precision",
        "half_width": width / 2, "relative_precision": epsilon,
        "relative_precision_definition": "half_width / planned_proportion",
        "alpha": alpha, "sides": 2, "z_alpha": z,
    }, raw)


def one_proportion_wilson(*, planned_proportion: float, width: float,
                          alpha: float = 0.05) -> dict[str, Any]:
    """CI-003: Wilson-type recommended planning equation 9.5."""
    proportion = _probability("planned_proportion", planned_proportion)
    width = _width(width)
    z = _z(alpha)
    omega = proportion * (1 - proportion) / width ** 2
    raw = ((2 * omega - 1) + sqrt((2 * omega - 1) ** 2 + 1 / width ** 2 - 1)) * z ** 2
    return _one_result("CI-003", "equations 9.4 and 9.5", {
        "planned_proportion": proportion, "width": width,
        "width_definition": "full Wilson interval width = upper limit - lower limit",
        "half_width": width / 2,
        "relative_precision": None if proportion == 0 else width / (2 * proportion),
        "relative_precision_definition": "half_width / planned_proportion when nonzero",
        "alpha": alpha, "sides": 2, "z_alpha": z, "omega_plan": omega,
    }, raw)


def finite_population_correction(*, infinite_population_sample_size: float | None = None,
                                 population_size: int,
                                 parent_result: dict[str, Any] | None = None,
                                 parent_result_key: str = "raw_total",
                                 parent_stage: str = "raw") -> dict[str, Any]:
    """CI-004: equation 9.7 applied to an explicitly supplied base size."""
    if parent_result is not None:
        consumed = consume_quantity(
            parent_result, allowed_parent_methods={"CI-001", "CI-002", "CI-003"},
            key=parent_result_key, quantity="participants", unit="participants", stage=parent_stage,
        )
        parent_value = float(consumed["value"])
        if infinite_population_sample_size is not None and abs(float(infinite_population_sample_size) - parent_value) > 1e-12:
            raise ValueError("infinite_population_sample_size conflicts with the consumed parent quantity")
        base = _positive("infinite_population_sample_size", parent_value)
    else:
        if infinite_population_sample_size is None:
            raise ValueError("provide infinite_population_sample_size or a typed parent_result")
        base = _positive("infinite_population_sample_size", infinite_population_sample_size)
        consumed = {
            "key": "infinite_population_sample_size", "value": base,
            "quantity": "participants", "unit": "participants", "stage": "raw",
        }
    if isinstance(population_size, bool) or not isinstance(population_size, int) or population_size < 1:
        raise ValueError("population_size must be a positive integer")
    raw = population_size * base / (base + population_size)
    result = _one_result("CI-004", "equations 9.6 and 9.7", {
        "infinite_population_sample_size": base, "population_size": population_size,
        "base_size_definition": "unrounded or rounded output of a separately identified infinite-population method",
    }, raw, extra={"sampling_fraction": raw / population_size})
    if result["final_total"] > population_size:
        result["final_total"] = population_size
        result["warnings"].append("ceiling was capped at the finite population size")
    if result["final_total"] / population_size >= .8:
        result["warnings"].append("required sample is at least 80% of the population; a census may be practical")
    if parent_result is not None:
        result["lineage"] = correction_lineage(
            parent_result=parent_result,
            consumed=consumed,
            transformation="equation 9.7 finite-population correction",
            child_outputs=[
                {"key": "raw_total", "quantity": "participants", "unit": "participants", "stage": "raw"},
                {"key": "final_total", "quantity": "participants", "unit": "participants", "stage": "final"},
            ],
        )
    else:
        result["lineage"] = {
            "calculation_type": "correction",
            "parent_method_id": "EXTERNAL-INFINITE-POPULATION-SIZE",
            "consumed_result": consumed,
            "parent_primary_inputs": {"infinite_population_sample_size": base},
            "parent_inference": {},
            "transformation": "equation 9.7 finite-population correction",
            "child_outputs": [
                {"key": "final_total", "quantity": "participants", "unit": "participants", "stage": "final"}
            ],
            "parent_source_provenance": None,
            "parent_validation_evidence": None,
            "warnings": ["legacy scalar parent path; use parent_result for reproducible lineage"],
        }
    return result


def two_proportion_normal_difference(*, control_proportion: float,
                                     treatment_proportion: float, width: float,
                                     allocation_ratio: float = 1.0,
                                     alpha: float = 0.05) -> dict[str, Any]:
    """CI-005: equation 9.10, normal approximation for an independent difference."""
    control = _strict_probability("control_proportion", control_proportion)
    treatment = _strict_probability("treatment_proportion", treatment_proportion)
    width = _width(width)
    phi = _positive("allocation_ratio", allocation_ratio)
    z = _z(alpha)
    raw = 4 * (1 + phi) / phi * (
        phi * control * (1 - control) + treatment * (1 - treatment)
    ) * z ** 2 / width ** 2
    return _two_result("CI-005", "equations 9.8, 9.9 and 9.10", {
        "control_proportion": control, "treatment_proportion": treatment,
        "width": width, "width_definition": "full width of the treatment-minus-control difference interval",
        "half_width": width / 2, "relative_precision": None,
        "allocation_ratio": phi, "allocation_ratio_definition": "treatment / control",
        "alpha": alpha, "sides": 2, "z_alpha": z,
    }, raw)


def _wilson_limits(proportion: float, count: float, z: float) -> tuple[float, float]:
    if count <= 0:
        raise ValueError("group count must be positive")
    a = 2 * count * proportion + z ** 2
    b = z * sqrt(z ** 2 + 4 * count * proportion * (1 - proportion))
    c = 2 * (count + z ** 2)
    return (a - b) / c, (a + b) / c


def _independent_wilson_width(total: float, control: float, treatment: float,
                              phi: float, z: float) -> float:
    control_n = total / (1 + phi)
    treatment_n = phi * control_n
    control_l, control_u = _wilson_limits(control, control_n, z)
    treatment_l, treatment_u = _wilson_limits(treatment, treatment_n, z)
    return sqrt((control - control_l) ** 2 + (treatment_u - treatment) ** 2) + sqrt(
        (treatment - treatment_l) ** 2 + (control_u - control) ** 2
    )


def two_proportion_wilson_difference(*, control_proportion: float,
                                     treatment_proportion: float, width: float,
                                     allocation_ratio: float = 1.0,
                                     alpha: float = 0.05,
                                     search_limit: float = 1_000_000_000) -> dict[str, Any]:
    """CI-006: invert the independent Wilson/Newcombe width in equation 9.11."""
    control = _probability("control_proportion", control_proportion)
    treatment = _probability("treatment_proportion", treatment_proportion)
    width = _width(width)
    phi = _positive("allocation_ratio", allocation_ratio)
    limit = _positive("search_limit", search_limit)
    z = _z(alpha)
    lower, upper = 1e-8, 2.0
    evaluations = 0
    while _independent_wilson_width(upper, control, treatment, phi, z) > width:
        upper *= 2
        evaluations += 1
        if upper > limit:
            raise ValueError("target width requires a sample size beyond search_limit")
    raw = brentq(
        lambda total: _independent_wilson_width(total, control, treatment, phi, z) - width,
        lower, upper, xtol=1e-10,
    )
    result = _two_result("CI-006", "equations 9.4 and 9.11", {
        "control_proportion": control, "treatment_proportion": treatment,
        "width": width, "width_definition": "full Wilson/Newcombe width of the treatment-minus-control difference interval",
        "half_width": width / 2, "relative_precision": None,
        "allocation_ratio": phi, "allocation_ratio_definition": "treatment / control",
        "alpha": alpha, "sides": 2, "z_alpha": z, "search_limit": limit,
    }, raw, extra={
        "search_lower": lower, "search_upper": upper, "root_tolerance": 1e-10,
        "converged": True, "function_evaluations_at_least": evaluations,
    })
    final_control = result["final_group_control"]
    final_treatment = result["final_group_treatment"]
    final_total = final_control + final_treatment
    achieved = _independent_wilson_width(final_total, control, treatment, phi, z)
    control_block, treatment_block = allocation_block(phi)
    previous_total = final_total - control_block - treatment_block
    result["achieved_width"] = achieved
    result["previous_block_width"] = (
        _independent_wilson_width(previous_total, control, treatment, phi, z)
        if previous_total > 0 else None
    )
    return result


def two_proportion_odds_ratio_relative(*, control_proportion: float,
                                       relative_precision: float,
                                       treatment_proportion: float | None = None,
                                       odds_ratio: float | None = None,
                                       allocation_ratio: float = 1.0,
                                       alpha: float = 0.05) -> dict[str, Any]:
    """CI-007: equation 9.15, relative precision for an independent odds ratio."""
    control = _strict_probability("control_proportion", control_proportion)
    epsilon = _positive("relative_precision", relative_precision)
    if not epsilon < 1:
        raise ValueError("relative_precision must be less than 1 because log(1-epsilon) is used")
    if treatment_proportion is None and odds_ratio is None:
        raise ValueError("provide treatment_proportion or odds_ratio")
    if odds_ratio is not None:
        odds = _positive("odds_ratio", odds_ratio)
        derived = control * odds / (1 - control + control * odds)
        if treatment_proportion is not None and abs(float(treatment_proportion) - derived) > 1e-10:
            raise ValueError("treatment_proportion is inconsistent with control_proportion and odds_ratio")
        treatment = derived
    else:
        treatment = _strict_probability("treatment_proportion", float(treatment_proportion))
        odds = treatment * (1 - control) / (control * (1 - treatment))
    treatment = _strict_probability("treatment_proportion", treatment)
    phi = _positive("allocation_ratio", allocation_ratio)
    z = _z(alpha)
    raw = (1 + phi) * (
        1 / (control * (1 - control)) + 1 / (phi * treatment * (1 - treatment))
    ) * z ** 2 / log(1 - epsilon) ** 2
    return _two_result("CI-007", "equations 9.12, 9.14 and 9.15", {
        "control_proportion": control, "treatment_proportion": treatment,
        "odds_ratio": odds, "relative_precision": epsilon,
        "relative_precision_definition": "multiplicative lower half-width: lower limit = OR * (1 - relative_precision)",
        "width": 2 * odds * epsilon,
        "width_definition": "planned symmetric display width OR*(1+epsilon) - OR*(1-epsilon); equation 9.15 uses log(1-epsilon)",
        "half_width": odds * epsilon,
        "allocation_ratio": phi, "allocation_ratio_definition": "treatment / control",
        "alpha": alpha, "sides": 2, "z_alpha": z,
    }, raw)


def _paired_wilson_width(pair_count: float, control: float, treatment: float,
                         correlation: float, z: float) -> float:
    control_l, control_u = _wilson_limits(control, pair_count, z)
    treatment_l, treatment_u = _wilson_limits(treatment, pair_count, z)
    first = (control - control_l) ** 2 - 2 * correlation * (
        control - control_l
    ) * (treatment_u - treatment) + (treatment_u - treatment) ** 2
    second = (treatment - treatment_l) ** 2 - 2 * correlation * (
        treatment - treatment_l
    ) * (control_u - control) + (control_u - control) ** 2
    if first < -1e-14 or second < -1e-14:
        raise ValueError("correlation and marginal proportions produce a negative equation 9.16 radicand")
    return sqrt(max(0.0, first)) + sqrt(max(0.0, second))


def paired_proportion_difference(*, control_proportion: float,
                                 treatment_proportion: float, correlation: float,
                                 width: float, alpha: float = 0.05,
                                 subjects_per_pair: int = 1,
                                 search_limit: float = 1_000_000_000) -> dict[str, Any]:
    """CI-008: invert paired Wilson/Newcombe width, equation 9.16."""
    control = _probability("control_proportion", control_proportion)
    treatment = _probability("treatment_proportion", treatment_proportion)
    correlation = float(correlation)
    if not isfinite(correlation) or not -1 <= correlation <= 1:
        raise ValueError("correlation must be a finite number in [-1, 1]")
    width = _width(width)
    if isinstance(subjects_per_pair, bool) or not isinstance(subjects_per_pair, int) or subjects_per_pair < 1:
        raise ValueError("subjects_per_pair must be a positive integer")
    limit = _positive("search_limit", search_limit)
    z = _z(alpha)
    lower, upper = 1e-8, 2.0
    evaluations = 0
    while _paired_wilson_width(upper, control, treatment, correlation, z) > width:
        upper *= 2
        evaluations += 1
        if upper > limit:
            raise ValueError("target width requires pairs beyond search_limit")
    raw_pairs = brentq(
        lambda count: _paired_wilson_width(count, control, treatment, correlation, z) - width,
        lower, upper, xtol=1e-10,
    )
    final_pairs = ceil(raw_pairs)
    result = _one_result("CI-008", "equations 9.4 and 9.16", {
        "control_proportion": control, "treatment_proportion": treatment,
        "correlation": correlation, "width": width,
        "width_definition": "full paired Wilson/Newcombe difference interval width",
        "half_width": width / 2, "relative_precision": None,
        "alpha": alpha, "sides": 2, "z_alpha": z,
        "subjects_per_pair": subjects_per_pair, "search_limit": limit,
    }, raw_pairs * subjects_per_pair, extra={
        "raw_pairs": raw_pairs, "rounded_pairs": final_pairs,
        "constraint_adjusted_pairs": final_pairs, "final_pairs": final_pairs,
        "search_lower": lower, "search_upper": upper, "root_tolerance": 1e-10,
        "converged": True, "function_evaluations_at_least": evaluations,
        "achieved_width": _paired_wilson_width(final_pairs, control, treatment, correlation, z),
        "previous_pair_width": _paired_wilson_width(final_pairs - 1, control, treatment, correlation, z) if final_pairs > 1 else None,
    })
    result["raw_total"] = raw_pairs * subjects_per_pair
    result["rounded_total"] = final_pairs * subjects_per_pair
    result["final_total"] = final_pairs * subjects_per_pair
    result["rounding_rule"] = "solve equation 9.16 continuously; ceil pairs"
    return result


def _one_mean_root(standardized_width: float, alpha: float,
                   large_sample_shortcut: bool) -> tuple[float, int, dict[str, Any]]:
    width = _positive("standardized_width", standardized_width)
    z = _z(alpha)
    provisional = 4 * z ** 2 / width ** 2
    if large_sample_shortcut and provisional >= 40:
        final = ceil(provisional)
        return provisional, final, {
            "normal_provisional": provisional, "large_sample_shortcut_used": True,
            "converged": True, "search_lower": None, "search_upper": None,
            "root_tolerance": None, "degrees_of_freedom": final - 1,
            "critical_value": z,
        }
    lower, upper = 1.0000001, max(4.0, provisional * 2)
    def equation(count: float) -> float:
        return count - 4 * t.ppf(1 - alpha / 2, count - 1) ** 2 / width ** 2
    while equation(upper) < 0:
        upper *= 2
        if upper > 1_000_000_000:
            raise ValueError("target width requires a sample size beyond the search limit")
    root = brentq(equation, lower, upper, xtol=1e-10)
    final = ceil(root)
    return root, final, {
        "normal_provisional": provisional, "large_sample_shortcut_used": False,
        "converged": True, "search_lower": lower, "search_upper": upper,
        "root_tolerance": 1e-10, "degrees_of_freedom": final - 1,
        "critical_value": float(t.ppf(1 - alpha / 2, final - 1)),
    }


def one_mean_absolute(*, planned_sd: float, width: float, alpha: float = 0.05,
                      large_sample_shortcut: bool = False) -> dict[str, Any]:
    """CI-009: equation 9.18 with explicit t iteration or stated large-N shortcut."""
    sd = _positive("planned_sd", planned_sd)
    width = _positive("width", width)
    standardized = width / sd
    raw, final, audit = _one_mean_root(standardized, _alpha(alpha), large_sample_shortcut)
    result = _one_result("CI-009", "equations 9.17 and 9.18", {
        "planned_sd": sd, "width": width,
        "width_definition": "full mean confidence-interval width",
        "half_width": width / 2, "relative_precision": None,
        "standardized_width": standardized, "alpha": alpha, "sides": 2,
        "large_sample_shortcut": large_sample_shortcut,
    }, raw, extra=audit)
    result["final_total"] = final
    result["rounded_total"] = ceil(raw)
    result["rounding_rule"] = "solve t fixed-point and ceil" if not audit["large_sample_shortcut_used"] else "apply the book's N0>=40 normal shortcut and ceil"
    return result


def one_mean_relative(*, planned_mean: float, planned_sd: float,
                      relative_precision: float, alpha: float = 0.05,
                      large_sample_shortcut: bool = False) -> dict[str, Any]:
    """CI-010: equation 9.19 with t iteration."""
    mean = float(planned_mean)
    if not isfinite(mean) or mean == 0:
        raise ValueError("planned_mean must be finite and nonzero")
    sd = _positive("planned_sd", planned_sd)
    epsilon = _positive("relative_precision", relative_precision)
    width = 2 * abs(mean) * epsilon
    standardized = width / sd
    raw, final, audit = _one_mean_root(standardized, _alpha(alpha), large_sample_shortcut)
    result = _one_result("CI-010", "equation 9.19", {
        "planned_mean": mean, "planned_sd": sd, "width": width,
        "width_definition": "full width = 2 * abs(planned_mean) * relative_precision",
        "half_width": width / 2, "relative_precision": epsilon,
        "relative_precision_definition": "half_width / abs(planned_mean)",
        "standardized_width": standardized, "theta_plan": abs(mean) / sd,
        "alpha": alpha, "sides": 2, "large_sample_shortcut": large_sample_shortcut,
    }, raw, extra=audit)
    result["final_total"] = final
    result["rounded_total"] = ceil(raw)
    result["rounding_rule"] = "solve t fixed-point and ceil" if not audit["large_sample_shortcut_used"] else "apply the book's N0>=40 normal shortcut and ceil"
    return result


def _two_mean_root(standardized_width: float, phi: float, alpha: float,
                   large_sample_shortcut: bool) -> tuple[float, dict[str, Any]]:
    width = _positive("standardized_width", standardized_width)
    z = _z(alpha)
    coefficient = 4 * (1 + phi) ** 2 / phi / width ** 2
    provisional = coefficient * z ** 2
    if large_sample_shortcut and provisional >= 40:
        return provisional, {
            "normal_provisional": provisional, "large_sample_shortcut_used": True,
            "converged": True, "search_lower": None, "search_upper": None,
            "root_tolerance": None,
        }
    lower, upper = 2.0000001, max(6.0, provisional * 2)
    def equation(total: float) -> float:
        return total - coefficient * t.ppf(1 - alpha / 2, total - 2) ** 2
    while equation(upper) < 0:
        upper *= 2
        if upper > 1_000_000_000:
            raise ValueError("target width requires a sample size beyond the search limit")
    root = brentq(equation, lower, upper, xtol=1e-10)
    return root, {
        "normal_provisional": provisional, "large_sample_shortcut_used": False,
        "converged": True, "search_lower": lower, "search_upper": upper,
        "root_tolerance": 1e-10,
    }


def two_mean_difference(*, planned_sd: float, width: float,
                        allocation_ratio: float = 1.0, alpha: float = 0.05,
                        large_sample_shortcut: bool = False) -> dict[str, Any]:
    """CI-011: equation 9.22 with allocation-aware t iteration."""
    sd = _positive("planned_sd", planned_sd)
    width = _positive("width", width)
    phi = _positive("allocation_ratio", allocation_ratio)
    standardized = width / sd
    raw, audit = _two_mean_root(standardized, phi, _alpha(alpha), large_sample_shortcut)
    result = _two_result("CI-011", "equations 9.20, 9.21 and 9.22", {
        "planned_sd": sd, "width": width,
        "width_definition": "full confidence-interval width for treatment-minus-control mean difference",
        "half_width": width / 2, "relative_precision": None,
        "standardized_width": standardized,
        "allocation_ratio": phi, "allocation_ratio_definition": "treatment / control",
        "alpha": alpha, "sides": 2, "large_sample_shortcut": large_sample_shortcut,
    }, raw, extra=audit)
    result["degrees_of_freedom"] = result["final_total"] - 2
    result["critical_value"] = float(t.ppf(1 - alpha / 2, result["degrees_of_freedom"])) if not audit["large_sample_shortcut_used"] else _z(alpha)
    result["rounding_rule"] = ("solve t fixed-point; ceil groups; enforce allocation block" if not audit["large_sample_shortcut_used"] else "apply the book's N0>=40 normal shortcut; ceil groups; enforce allocation block")
    return result


def paired_mean_difference(*, pair_sd: float, width: float, alpha: float = 0.05,
                           subjects_per_pair: int = 1,
                           large_sample_shortcut: bool = False) -> dict[str, Any]:
    """CI-012: equation 9.24 with t iteration."""
    sd = _positive("pair_sd", pair_sd)
    width = _positive("width", width)
    if isinstance(subjects_per_pair, bool) or not isinstance(subjects_per_pair, int) or subjects_per_pair < 1:
        raise ValueError("subjects_per_pair must be a positive integer")
    standardized = width / sd
    raw_pairs, final_pairs, audit = _one_mean_root(standardized, _alpha(alpha), large_sample_shortcut)
    result = _one_result("CI-012", "equations 9.23 and 9.24", {
        "pair_sd": sd, "width": width,
        "width_definition": "full confidence-interval width for the paired mean difference",
        "half_width": width / 2, "relative_precision": None,
        "standardized_width": standardized, "alpha": alpha, "sides": 2,
        "subjects_per_pair": subjects_per_pair,
        "large_sample_shortcut": large_sample_shortcut,
    }, raw_pairs * subjects_per_pair, extra=audit)
    result.update({
        "raw_pairs": raw_pairs, "rounded_pairs": ceil(raw_pairs),
        "constraint_adjusted_pairs": final_pairs, "final_pairs": final_pairs,
        "rounded_total": ceil(raw_pairs) * subjects_per_pair,
        "final_total": final_pairs * subjects_per_pair,
    })
    result["rounding_rule"] = "solve paired t fixed-point and ceil pairs" if not audit["large_sample_shortcut_used"] else "apply the book's N0>=40 normal shortcut and ceil pairs"
    return result


one_proportion_normal_absolute = contracted(one_proportion_normal_absolute)
one_proportion_normal_relative = contracted(one_proportion_normal_relative)
one_proportion_wilson = contracted(one_proportion_wilson)
finite_population_correction = contracted(finite_population_correction)
two_proportion_normal_difference = contracted(two_proportion_normal_difference)
two_proportion_wilson_difference = contracted(two_proportion_wilson_difference)
two_proportion_odds_ratio_relative = contracted(two_proportion_odds_ratio_relative)
paired_proportion_difference = contracted(paired_proportion_difference)
one_mean_absolute = contracted(one_mean_absolute)
one_mean_relative = contracted(one_mean_relative)
two_mean_difference = contracted(two_mean_difference)
paired_mean_difference = contracted(paired_mean_difference)
