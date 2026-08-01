"""Chapter 21 reference-interval and diagnostic-accuracy calculations."""

from __future__ import annotations

from math import ceil, exp, isfinite, pi, sqrt
from statistics import NormalDist
from typing import Any, Literal

from scipy.stats import binom

from .rounding import allocation_rounding
from .schema_contract import contracted


TargetMetric = Literal["sensitivity", "specificity"]


def _open_probability(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 < value < 1:
        raise ValueError(f"{name} must be a finite number in (0, 1)")
    return value


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")
    return value


def _target(target_metric: str, prevalence: float) -> tuple[str, float]:
    prevalence = _open_probability("prevalence", prevalence)
    if target_metric == "sensitivity":
        return target_metric, prevalence
    if target_metric == "specificity":
        return target_metric, 1 - prevalence
    raise ValueError("target_metric must be 'sensitivity' or 'specificity'")


def _sides(value: int) -> int:
    if value not in (1, 2):
        raise ValueError("sides must be 1 or 2")
    return value


def _participant_result(method_id: str, reference: str, inputs: dict[str, Any], raw: float,
                        *, role: str | None = "reference", warnings: list[str] | None = None,
                        extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isfinite(raw) or raw <= 0:
        raise ValueError("inputs do not produce a finite positive participant count")
    final = ceil(raw)
    result: dict[str, Any] = {
        "method_id": method_id,
        "formula_reference": reference,
        "inputs": inputs,
        "raw_total": raw,
        "rounded_total": final,
        "final_total": final,
        "final_total_participants": final,
        "rounding_rule": "ceil the unrounded participant count once after all formula terms",
        "warnings": list(warnings or ()),
        "provenance": None,
    }
    if role is not None:
        result[f"raw_{role}_participants"] = raw
        result[f"rounded_{role}_participants"] = final
        result[f"final_{role}_participants"] = final
    if extra:
        result.update(extra)
    return result


def normal_reference_interval_precision(*, reference_interval_level: float,
                                        cutoff_confidence_level: float,
                                        precision_ratio: float,
                                        limit_side: str = "both",
                                        analysis_scale: str = "original") -> dict[str, Any]:
    """DIAG-001: normal-theory reference-limit precision, equations 21.1--21.7."""
    ri = _open_probability("reference_interval_level", reference_interval_level)
    confidence = _open_probability("cutoff_confidence_level", cutoff_confidence_level)
    rho = _positive("precision_ratio", precision_ratio)
    if limit_side not in {"lower", "upper", "both"}:
        raise ValueError("limit_side must be 'lower', 'upper', or 'both'")
    if analysis_scale not in {"original", "log"}:
        raise ValueError("analysis_scale must be 'original' or 'log'")
    z_ri = NormalDist().inv_cdf((1 + ri) / 2)
    z_cut = NormalDist().inv_cdf((1 + confidence) / 2)
    raw = 3 * (z_cut / (rho * z_ri)) ** 2
    return _participant_result("DIAG-001", "equations 21.1 through 21.7", {
        "reference_interval_level": ri,
        "reference_interval_tail_probability": (1 - ri) / 2,
        "cutoff_confidence_level": confidence,
        "cutoff_ci_tail_probability": (1 - confidence) / 2,
        "precision_ratio": rho,
        "precision_definition": "full cutoff-limit CI width divided by full reference interval width",
        "limit_side": limit_side,
        "analysis_scale": analysis_scale,
        "z_reference_interval": z_ri,
        "z_cutoff_confidence": z_cut,
    }, raw, extra={"transformation": analysis_scale, "transformed_scale": analysis_scale})


def rank_reference_interval_precision(*, reference_interval_level: float,
                                      cutoff_confidence_level: float,
                                      precision_ratio: float,
                                      limit_side: str = "both") -> dict[str, Any]:
    """DIAG-002: rank-based reference-limit precision, equations 21.9--21.14."""
    ri = _open_probability("reference_interval_level", reference_interval_level)
    confidence = _open_probability("cutoff_confidence_level", cutoff_confidence_level)
    rho = _positive("precision_ratio", precision_ratio)
    if limit_side not in {"lower", "upper", "both"}:
        raise ValueError("limit_side must be 'lower', 'upper', or 'both'")
    z_ri = NormalDist().inv_cdf((1 + ri) / 2)
    z_cut = NormalDist().inv_cdf((1 + confidence) / 2)
    q = (1 - confidence) / 2
    density = exp(-z_cut * z_cut / 2) / sqrt(2 * pi)
    eta = sqrt(q * (1 - q)) / density
    raw = sqrt(3) * eta * (z_cut / (rho * z_ri)) ** 2
    rank_lower = raw * (1 - ri) / 2 - z_cut * sqrt(raw * (1 - ri) / 2 * (1 - (1 - ri) / 2))
    rank_upper = 1 + raw * (1 + ri) / 2 + z_cut * sqrt(raw * (1 + ri) / 2 * (1 - (1 + ri) / 2))
    return _participant_result("DIAG-002", "equations 21.9 through 21.14", {
        "reference_interval_level": ri,
        "cutoff_confidence_level": confidence,
        "precision_ratio": rho,
        "precision_definition": "full cutoff-limit CI width divided by full reference interval width",
        "limit_side": limit_side,
        "z_reference_interval": z_ri,
        "z_cutoff_confidence": z_cut,
        "tail_rank_probability": q,
    }, raw, extra={
        "eta": eta,
        "normal_density_at_cutoff_quantile": density,
        "raw_lower_rank": rank_lower,
        "raw_upper_rank": rank_upper,
        "rounded_lower_rank": max(1, ceil(rank_lower)),
        "rounded_upper_rank": ceil(rank_upper),
    })


def single_accuracy_large_sample(*, target_metric: TargetMetric, known_accuracy: float,
                                 planned_accuracy: float, prevalence: float,
                                 alpha: float = .05, power: float = .8,
                                 sides: int = 2) -> dict[str, Any]:
    """DIAG-003: large-sample sensitivity/specificity calculation, equation 21.15."""
    target_metric, information_fraction = _target(target_metric, prevalence)
    p0 = _open_probability("known_accuracy", known_accuracy)
    p1 = _open_probability("planned_accuracy", planned_accuracy)
    if p0 == p1:
        raise ValueError("planned_accuracy must differ from known_accuracy")
    alpha = _open_probability("alpha", alpha)
    power = _open_probability("power", power)
    sides = _sides(sides)
    z_alpha = NormalDist().inv_cdf(1 - alpha / sides)
    z_power = NormalDist().inv_cdf(power)
    raw_information = ((z_alpha * sqrt(p0 * (1 - p0)) +
                        z_power * sqrt(p1 * (1 - p1))) / abs(p1 - p0)) ** 2
    raw_total = raw_information / information_fraction
    rounded_information = ceil(raw_information)
    final = ceil(raw_total)
    role = "disease" if target_metric == "sensitivity" else "nondisease"
    warnings = ["equation 21.15 is a large-sample normal approximation"]
    if min(raw_information * p1, raw_information * (1 - p1)) < 5:
        warnings.append("planned expected successes or failures are below 5; consider DIAG-004")
    return _participant_result("DIAG-003", "equation 21.15", {
        "target_metric": target_metric, "known_accuracy": p0, "planned_accuracy": p1,
        "effect_direction": "increase" if p1 > p0 else "decrease",
        "prevalence": prevalence, "information_fraction": information_fraction,
        "alpha": alpha, "power": power, "sides": sides,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw_total, role=None, warnings=warnings, extra={
        "raw_information_participants": raw_information,
        "rounded_information_participants": rounded_information,
        f"raw_{role}_participants": raw_information,
        f"rounded_{role}_participants": rounded_information,
        f"final_{role}_participants": rounded_information,
        "raw_total_participants": raw_total,
        "rounded_total_participants": final,
        "final_total_participants": final,
    })


def _upper_critical(n: int, p0: float, alpha: float) -> tuple[int, float]:
    critical = int(binom.ppf(1 - alpha, n, p0)) + 1
    while critical > 0 and float(binom.sf(critical - 2, n, p0)) <= alpha:
        critical -= 1
    while critical <= n and float(binom.sf(critical - 1, n, p0)) > alpha:
        critical += 1
    actual_alpha = float(binom.sf(critical - 1, n, p0)) if critical <= n else 0.0
    return critical, actual_alpha


def _lower_critical(n: int, p0: float, alpha: float) -> tuple[int, float]:
    critical = int(binom.ppf(alpha, n, p0))
    while critical >= 0 and float(binom.cdf(critical, n, p0)) > alpha:
        critical -= 1
    while critical + 1 <= n and float(binom.cdf(critical + 1, n, p0)) <= alpha:
        critical += 1
    actual_alpha = float(binom.cdf(critical, n, p0)) if critical >= 0 else 0.0
    return critical, actual_alpha


def single_accuracy_exact(*, target_metric: TargetMetric, known_accuracy: float,
                          planned_accuracy: float, prevalence: float,
                          alpha: float = .05, power: float = .8, sides: int = 1,
                          max_information_participants: int = 100_000) -> dict[str, Any]:
    """DIAG-004: exact one-sided binomial critical-region integer search."""
    target_metric, information_fraction = _target(target_metric, prevalence)
    p0 = _open_probability("known_accuracy", known_accuracy)
    p1 = _open_probability("planned_accuracy", planned_accuracy)
    if p0 == p1:
        raise ValueError("planned_accuracy must differ from known_accuracy")
    alpha = _open_probability("alpha", alpha)
    power = _open_probability("power", power)
    if sides != 1:
        raise ValueError("DIAG-004 supports only directional one-sided exact tests (sides=1)")
    if not isinstance(max_information_participants, int) or max_information_participants < 1:
        raise ValueError("max_information_participants must be a positive integer")
    direction = "upper" if p1 > p0 else "lower"
    critical = -1
    actual_alpha = achieved = 0.0
    for n in range(1, max_information_participants + 1):
        if direction == "upper":
            critical, actual_alpha = _upper_critical(n, p0, alpha)
            achieved = float(binom.sf(critical - 1, n, p1)) if critical <= n else 0.0
        else:
            critical, actual_alpha = _lower_critical(n, p0, alpha)
            achieved = float(binom.cdf(critical, n, p1)) if critical >= 0 else 0.0
        if achieved >= power:
            break
    else:
        raise ValueError("exact binomial search did not converge within max_information_participants")
    prior_n = n - 1
    if prior_n >= 1:
        if direction == "upper":
            prior_critical, prior_alpha = _upper_critical(prior_n, p0, alpha)
            prior_power = float(binom.sf(prior_critical - 1, prior_n, p1)) if prior_critical <= prior_n else 0.0
        else:
            prior_critical, prior_alpha = _lower_critical(prior_n, p0, alpha)
            prior_power = float(binom.cdf(prior_critical, prior_n, p1)) if prior_critical >= 0 else 0.0
    else:
        prior_critical, prior_alpha, prior_power = None, None, None
    raw_total = n / information_fraction
    final_total = ceil(raw_total)
    role = "disease" if target_metric == "sensitivity" else "nondisease"
    result = _participant_result("DIAG-004", "chapter 21.3 exact-binomial recommendation", {
        "target_metric": target_metric, "known_accuracy": p0, "planned_accuracy": p1,
        "effect_direction": "increase" if p1 > p0 else "decrease",
        "test_direction": direction, "prevalence": prevalence,
        "information_fraction": information_fraction, "alpha": alpha,
        "power": power, "sides": 1,
        "max_information_participants": max_information_participants,
    }, raw_total, role=None, extra={
        "information_participants": n,
        "raw_information_participants": float(n),
        "rounded_information_participants": n,
        f"raw_{role}_participants": float(n),
        f"rounded_{role}_participants": n,
        f"final_{role}_participants": n,
        "critical_value": critical,
        "critical_region": f"X >= {critical}" if direction == "upper" else f"X <= {critical}",
        "actual_type_i_error": actual_alpha,
        "achieved_power": achieved,
        "n_minus_1": prior_n,
        "n_minus_1_critical_value": prior_critical,
        "n_minus_1_actual_type_i_error": prior_alpha,
        "n_minus_1_power": prior_power,
        "raw_total_participants": raw_total,
        "rounded_total_participants": final_total,
        "final_total_participants": final_total,
        "search_iterations": n,
        "converged": True,
        "search": {"type": "ascending integer exact-binomial search", "minimum": 1,
                   "maximum": max_information_participants, "iterations": n,
                   "stopping_condition": "actual alpha <= alpha and achieved power >= target",
                   "converged": True},
    })
    result["rounding_rule"] = "exact integer information count; ceil n/information_fraction for total participants"
    return result


def independent_accuracy_comparison(*, target_metric: TargetMetric, accuracy_a: float,
                                    accuracy_b: float, prevalence: float,
                                    allocation_ratio: float = 1.0, alpha: float = .05,
                                    power: float = .8, sides: int = 2) -> dict[str, Any]:
    """DIAG-005: independent diagnostic-accuracy comparison, equation 21.16."""
    target_metric, information_fraction = _target(target_metric, prevalence)
    a = _open_probability("accuracy_a", accuracy_a)
    b = _open_probability("accuracy_b", accuracy_b)
    if a == b:
        raise ValueError("accuracy_a and accuracy_b must differ")
    ratio = _positive("allocation_ratio", allocation_ratio)
    alpha = _open_probability("alpha", alpha)
    power = _open_probability("power", power)
    sides = _sides(sides)
    z_alpha = NormalDist().inv_cdf(1 - alpha / sides)
    z_power = NormalDist().inv_cdf(power)
    pooled = (a + ratio * b) / (1 + ratio)
    numerator = (z_alpha * sqrt((1 + ratio) * pooled * (1 - pooled)) +
                 z_power * sqrt(ratio * a * (1 - a) + b * (1 - b))) ** 2
    raw_total = (1 + ratio) / ratio * numerator / (information_fraction * (b - a) ** 2)
    rounded = allocation_rounding(raw_total, ratio)
    return {
        "method_id": "DIAG-005", "formula_reference": "equation 21.16",
        "inputs": {"target_metric": target_metric, "accuracy_a": a, "accuracy_b": b,
                   "effect_direction": "B minus A", "prevalence": prevalence,
                   "information_fraction": information_fraction,
                   "allocation_ratio": ratio, "allocation_definition": "test B / test A (1:phi)",
                   "alpha": alpha, "power": power, "sides": sides,
                   "z_alpha": z_alpha, "z_power": z_power},
        "pooled_accuracy": pooled, "raw_total": raw_total,
        "raw_test_a_participants": rounded["raw_group_control"],
        "raw_test_b_participants": rounded["raw_group_treatment"],
        "rounded_test_a_participants": rounded["rounded_group_control"],
        "rounded_test_b_participants": rounded["rounded_group_treatment"],
        "allocation_adjusted_test_a_participants": rounded["final_group_control"],
        "allocation_adjusted_test_b_participants": rounded["final_group_treatment"],
        "rounded_total": rounded["rounded_total"],
        "final_test_a_participants": rounded["final_group_control"],
        "final_test_b_participants": rounded["final_group_treatment"],
        "final_total": rounded["final_total"],
        "final_total_participants": rounded["final_total"],
        "rounding_rule": rounded["rounding_rule"], "warnings": [], "provenance": None,
    }


def paired_accuracy_comparison(*, target_metric: TargetMetric, accuracy_a: float,
                               accuracy_b: float, prevalence: float,
                               alpha: float = .05, power: float = .8,
                               sides: int = 2, first_order: str = "AB") -> dict[str, Any]:
    """DIAG-006: paired diagnostic-accuracy comparison, equation 21.17."""
    target_metric, information_fraction = _target(target_metric, prevalence)
    a = _open_probability("accuracy_a", accuracy_a)
    b = _open_probability("accuracy_b", accuracy_b)
    if a == b:
        raise ValueError("accuracy_a and accuracy_b must differ")
    if first_order not in {"AB", "BA"}:
        raise ValueError("first_order must be 'AB' or 'BA'")
    alpha = _open_probability("alpha", alpha)
    power = _open_probability("power", power)
    sides = _sides(sides)
    z_alpha = NormalDist().inv_cdf(1 - alpha / sides)
    z_power = NormalDist().inv_cdf(power)
    lam = (1 - a) * b + (1 - b) * a
    xi = (1 - a) * b - (1 - b) * a
    radicand = lam * lam - xi * xi * (3 + lam) / 4
    if lam <= 0 or radicand < 0:
        raise ValueError("inputs do not yield a valid equation 21.17 variance term")
    raw = (z_alpha * lam + z_power * sqrt(radicand)) ** 2 / (information_fraction * lam * xi * xi)
    final = ceil(raw)
    first = ceil(final / 2)
    second = final - first
    ab, ba = (first, second) if first_order == "AB" else (second, first)
    result = _participant_result("DIAG-006", "equation 21.17", {
        "target_metric": target_metric, "accuracy_a": a, "accuracy_b": b,
        "effect_direction": "B minus A", "prevalence": prevalence,
        "information_fraction": information_fraction, "alpha": alpha,
        "power": power, "sides": sides, "first_order": first_order,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw, role="paired", extra={
        "lambda": lam, "xi": xi, "variance_radicand": radicand,
        "raw_paired_participants": raw, "rounded_paired_participants": final,
        "order_ab_participants": ab, "order_ba_participants": ba,
        "final_paired_participants": final, "final_total_participants": final,
    })
    result["rounding_rule"] = "ceil paired total, then assign the odd participant to first_order"
    return result


def roc_auc_ci_width(*, true_positive_rate: float, false_positive_rate: float,
                     nondisease_to_disease_ratio: float, confidence_level: float = .95,
                     target_ci_width: float = .10) -> dict[str, Any]:
    """DIAG-007: binormal ROC-AUC CI-width calculation, equations 21.18--21.21."""
    tpr = _open_probability("true_positive_rate", true_positive_rate)
    fpr = _open_probability("false_positive_rate", false_positive_rate)
    ratio = _positive("nondisease_to_disease_ratio", nondisease_to_disease_ratio)
    confidence = _open_probability("confidence_level", confidence_level)
    width = _positive("target_ci_width", target_ci_width)
    if width >= 1:
        raise ValueError("target_ci_width must be a full AUC CI width in (0, 1)")
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    roc_z = NormalDist().inv_cdf(1 - fpr) - NormalDist().inv_cdf(1 - tpr)
    sigma = (exp(-roc_z * roc_z / 4) / (2 * sqrt(pi)) *
             sqrt((1 + 1 / ratio) + 5 * roc_z * roc_z / 8 + roc_z * roc_z / (8 * ratio)))
    raw_disease = 4 * (sigma / width) ** 2 * z * z
    rounded_disease = ceil(raw_disease)
    raw_nondisease = ratio * raw_disease
    rounded_nondisease = ceil(raw_nondisease)
    # Chapter 21 first rounds the disease count, then derives the non-disease
    # count from R. It does not consistently raise disease n to a ratio block.
    final_disease = rounded_disease
    final_nondisease = ceil(ratio * rounded_disease)
    return {
        "method_id": "DIAG-007", "formula_reference": "equations 21.18 through 21.21",
        "inputs": {"true_positive_rate": tpr, "false_positive_rate": fpr,
                   "sensitivity": tpr, "specificity": 1 - fpr,
                   "nondisease_to_disease_ratio": ratio,
                   "ratio_definition": "nondisease / disease",
                   "confidence_level": confidence, "target_ci_width": width,
                   "width_definition": "full two-sided AUC confidence-interval width"},
        "Z": roc_z, "planned_sigma": sigma, "z_confidence": z,
        "raw_disease_participants": raw_disease,
        "rounded_disease_participants": rounded_disease,
        "raw_nondisease_participants": raw_nondisease,
        "rounded_nondisease_participants": rounded_nondisease,
        "allocation_adjusted_disease_participants": final_disease,
        "allocation_adjusted_nondisease_participants": final_nondisease,
        "raw_total": raw_disease + raw_nondisease,
        "rounded_total": rounded_disease + rounded_nondisease,
        "final_disease_participants": final_disease,
        "final_nondisease_participants": final_nondisease,
        "final_total": final_disease + final_nondisease,
        "final_total_participants": final_disease + final_nondisease,
        "rounding_rule": "ceil disease count; retain separate raw group ceilings; then set final nondisease=ceil(R*rounded disease)",
        "warnings": ["equations 21.18--21.21 assume the binormal ROC model"], "provenance": None,
    }


normal_reference_interval_precision = contracted(normal_reference_interval_precision)
rank_reference_interval_precision = contracted(rank_reference_interval_precision)
single_accuracy_large_sample = contracted(single_accuracy_large_sample)
single_accuracy_exact = contracted(single_accuracy_exact)
independent_accuracy_comparison = contracted(independent_accuracy_comparison)
paired_accuracy_comparison = contracted(paired_accuracy_comparison)
roc_auc_ci_width = contracted(roc_auc_ci_width)
