"""Chapter 10 repeated-outcome sample-size calculations."""

from __future__ import annotations

from math import ceil, isclose, isfinite
from typing import Any, Sequence

from .continuous import two_sample_mean_guenther
from .rounding import allocation_rounding
from .schema_contract import contracted


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")
    return value


def _count(name: str, value: int, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        relation = "nonnegative" if allow_zero else "positive"
        raise ValueError(f"{name} must be a {relation} integer")
    return value


def _correlation(value: float, measurement_count: int) -> float:
    value = float(value)
    lower = -1 / (measurement_count - 1) if measurement_count > 1 else -1.0
    if not isfinite(value) or not lower < value < 1:
        raise ValueError(f"correlation must be in ({lower}, 1) for the requested measurement count")
    return value


def post_mean_design_effect(*, pre_measurements: int, post_measurements: int,
                            correlation: float) -> float:
    """Equation 10.8, with equation 10.9 when pre_measurements is zero."""
    nu = _count("pre_measurements", pre_measurements, allow_zero=True)
    w = _count("post_measurements", post_measurements)
    rho = _correlation(correlation, nu + w)
    first = (1 + (w - 1) * rho) / w
    second = 0.0 if nu == 0 else nu * rho ** 2 / (1 + (nu - 1) * rho)
    result = first - second
    if result <= 0:
        raise ValueError("equation 10.8 does not produce a positive design effect")
    return result


def _base_result(method_id: str, reference: str, inputs: dict[str, Any],
                 base_raw: float, design_effect: float,
                 assessment_count: int) -> dict[str, Any]:
    raw = base_raw * design_effect
    result: dict[str, Any] = {
        "method_id": method_id,
        "formula_reference": reference,
        "inputs": inputs,
        "base_raw_total": base_raw,
        "design_effect": design_effect,
        "raw_total": raw,
        "rounded_total": ceil(raw),
        "final_total": ceil(raw),
        "raw_assessments": raw * assessment_count,
        "rounded_assessments": ceil(raw) * assessment_count,
        "final_assessments": ceil(raw) * assessment_count,
        "assessment_count_per_participant": assessment_count,
        "rounding_rule": "multiply the unrounded Chapter 5 base size by the design effect, then apply allocation rounding",
        "warnings": [],
        "provenance": None,
    }
    result.update(allocation_rounding(raw, float(inputs["allocation_ratio"])))
    result["final_assessments"] = result["final_total"] * assessment_count
    return result


def repeated_post_mean(*, planned_mean_difference: float, planned_sd: float,
                       pre_measurements: int, post_measurements: int,
                       correlation: float, allocation_ratio: float = 1.0,
                       alpha: float = 0.05, power: float = 0.80,
                       sides: int = 2) -> dict[str, Any]:
    """TWO-031: post-intervention mean comparison, equations 10.7--10.9."""
    difference = float(planned_mean_difference)
    if not isfinite(difference) or difference == 0:
        raise ValueError("planned_mean_difference must be finite and nonzero")
    sd = _positive("planned_sd", planned_sd)
    _positive("allocation_ratio", allocation_ratio)
    effect = abs(difference) / sd
    design_effect = post_mean_design_effect(
        pre_measurements=pre_measurements,
        post_measurements=post_measurements,
        correlation=correlation,
    )
    base = two_sample_mean_guenther(
        standardized_effect=effect, allocation_ratio=allocation_ratio,
        alpha=alpha, power=power, sides=sides,
    )
    inputs = {
        "planned_mean_difference": difference, "planned_sd": sd,
        "standardized_effect": effect, "pre_measurements": pre_measurements,
        "post_measurements": post_measurements, "correlation": correlation,
        "correlation_structure": "compound_symmetry",
        "allocation_ratio": allocation_ratio,
        "allocation_ratio_definition": "treatment / control",
        "alpha": alpha, "power": power, "sides": sides,
    }
    result = _base_result(
        "TWO-031", "equations 10.7, 10.8 and 10.9", inputs,
        float(base["raw_total"]), design_effect,
        pre_measurements + post_measurements,
    )
    result["base_method_id"] = "TWO-009"
    result["repeated_measure_efficiency"] = 1 / design_effect
    return result


def repeated_slope(*, planned_slope_difference: float, planned_intercept_sd: float,
                   measurement_times: Sequence[float], correlation: float,
                   allocation_ratio: float = 1.0, alpha: float = 0.05,
                   power: float = 0.80, sides: int = 2) -> dict[str, Any]:
    """TWO-032: post-intervention slope comparison, equations 10.7, 10.10, 10.11."""
    difference = float(planned_slope_difference)
    if not isfinite(difference) or difference == 0:
        raise ValueError("planned_slope_difference must be finite and nonzero")
    sd = _positive("planned_intercept_sd", planned_intercept_sd)
    _positive("allocation_ratio", allocation_ratio)
    times = [float(value) for value in measurement_times]
    if len(times) < 2 or any(not isfinite(value) for value in times) or len(set(times)) != len(times):
        raise ValueError("measurement_times must contain at least two distinct finite times")
    rho = _correlation(correlation, len(times))
    mean_time = sum(times) / len(times)
    time_sum_squares = sum((value - mean_time) ** 2 for value in times)
    if time_sum_squares <= 0:
        raise ValueError("measurement_times must have positive dispersion")
    design_effect = (1 - rho) / time_sum_squares
    effect = abs(difference) / sd
    base = two_sample_mean_guenther(
        standardized_effect=effect, allocation_ratio=allocation_ratio,
        alpha=alpha, power=power, sides=sides,
    )
    inputs = {
        "planned_slope_difference": difference, "planned_intercept_sd": sd,
        "standardized_effect": effect, "measurement_times": times,
        "correlation": rho, "correlation_structure": "compound_symmetry",
        "allocation_ratio": allocation_ratio,
        "allocation_ratio_definition": "treatment / control",
        "alpha": alpha, "power": power, "sides": sides,
    }
    result = _base_result(
        "TWO-032", "equations 10.7, 10.10 and 10.11", inputs,
        float(base["raw_total"]), design_effect, len(times),
    )
    result.update({
        "base_method_id": "TWO-009", "mean_measurement_time": mean_time,
        "time_sum_squares": time_sum_squares,
        "repeated_measure_efficiency": 1 / design_effect,
    })
    return result


def _covariance(weights: list[float], sd: float, structure: str,
                correlation: float | None, times: list[float] | None,
                covariance_matrix: Sequence[Sequence[float]] | None) -> tuple[float, list[list[float]]]:
    size = len(weights)
    if structure == "covariance_matrix":
        if covariance_matrix is None:
            raise ValueError("covariance_matrix is required for covariance_matrix structure")
        matrix = [[float(value) for value in row] for row in covariance_matrix]
        if len(matrix) != size or any(len(row) != size for row in matrix):
            raise ValueError("covariance_matrix dimensions must match weights")
        if any(not isfinite(value) for row in matrix for value in row):
            raise ValueError("covariance_matrix must be finite")
        if any(not isclose(matrix[i][j], matrix[j][i], rel_tol=0, abs_tol=1e-10) for i in range(size) for j in range(size)):
            raise ValueError("covariance_matrix must be symmetric")
    else:
        if correlation is None:
            raise ValueError("correlation is required for a named correlation structure")
        rho = _correlation(correlation, size)
        if structure == "compound_symmetry":
            matrix = [[sd ** 2 * (1 if i == j else rho) for j in range(size)] for i in range(size)]
        elif structure == "ar1":
            time_values = list(range(size)) if times is None else times
            if len(time_values) != size or any(not isfinite(value) for value in time_values):
                raise ValueError("measurement_times must match weights for AR(1)")
            matrix = [[sd ** 2 * rho ** abs(time_values[i] - time_values[j]) for j in range(size)] for i in range(size)]
        else:
            raise ValueError("correlation_structure must be compound_symmetry, ar1, or covariance_matrix")
    variance = sum(weights[i] * weights[j] * matrix[i][j] for i in range(size) for j in range(size))
    if not isfinite(variance) or variance <= 0:
        raise ValueError("weights and covariance must produce a positive finite contrast variance")
    return variance, matrix


def repeated_weighted_contrast(*, planned_contrast_difference: float,
                               planned_sd: float, weights: Sequence[float],
                               correlation_structure: str,
                               correlation: float | None = None,
                               measurement_times: Sequence[float] | None = None,
                               covariance_matrix: Sequence[Sequence[float]] | None = None,
                               allocation_ratio: float = 1.0,
                               alpha: float = 0.05, power: float = 0.80,
                               sides: int = 2) -> dict[str, Any]:
    """TWO-033: selected/weighted repeated comparison, equations 10.12--10.14."""
    difference = float(planned_contrast_difference)
    if not isfinite(difference) or difference == 0:
        raise ValueError("planned_contrast_difference must be finite and nonzero")
    sd = _positive("planned_sd", planned_sd)
    _positive("allocation_ratio", allocation_ratio)
    weight_values = [float(value) for value in weights]
    if len(weight_values) < 2 or any(not isfinite(value) for value in weight_values) or all(value == 0 for value in weight_values):
        raise ValueError("weights must contain at least two finite values and not be all zero")
    times = None if measurement_times is None else [float(value) for value in measurement_times]
    variance, matrix = _covariance(
        weight_values, sd, correlation_structure, correlation, times, covariance_matrix,
    )
    design_effect = variance / sd ** 2
    effect = abs(difference) / sd
    base = two_sample_mean_guenther(
        standardized_effect=effect, allocation_ratio=allocation_ratio,
        alpha=alpha, power=power, sides=sides,
    )
    inputs = {
        "planned_contrast_difference": difference, "planned_sd": sd,
        "standardized_effect": effect, "weights": weight_values,
        "correlation_structure": correlation_structure,
        "correlation": correlation, "measurement_times": times,
        "covariance_matrix": matrix,
        "allocation_ratio": allocation_ratio,
        "allocation_ratio_definition": "treatment / control",
        "alpha": alpha, "power": power, "sides": sides,
    }
    result = _base_result(
        "TWO-033", "equations 10.7, 10.12, 10.13 and 10.14", inputs,
        float(base["raw_total"]), design_effect, len(weight_values),
    )
    result.update({
        "base_method_id": "TWO-009", "contrast_variance": variance,
        "repeated_measure_efficiency": 1 / design_effect,
    })
    if not isclose(sum(weight_values), 0.0, rel_tol=0.0, abs_tol=1e-10):
        result["warnings"].append("weights do not sum to zero; this is a weighted estimand rather than a contrast")
    return result


repeated_post_mean = contracted(repeated_post_mean)
repeated_slope = contracted(repeated_slope)
repeated_weighted_contrast = contracted(repeated_weighted_contrast)
