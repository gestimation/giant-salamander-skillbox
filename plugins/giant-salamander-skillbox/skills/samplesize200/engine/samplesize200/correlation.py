"""Chapter 19 correlation detection and confidence-interval precision."""

from __future__ import annotations

from math import atanh, ceil, isfinite, sqrt, tanh
from statistics import NormalDist
from typing import Any

from .schema_contract import consume_quantity, contracted


def _correlation(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not -1 < value < 1:
        raise ValueError(f"{name} must be a finite correlation strictly between -1 and 1")
    return value


def _probability(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 < value < 1:
        raise ValueError(f"{name} must be a finite number in (0, 1)")
    return value


def _width(value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 < value < 2:
        raise ValueError("width must be a finite full correlation-interval width in (0, 2)")
    return value


def _result(method_id: str, reference: str, inputs: dict[str, Any], raw: float,
            *, warnings: list[str] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isfinite(raw) or raw <= 3:
        raise ValueError("inputs do not produce a finite sample size greater than 3")
    final = ceil(raw)
    result: dict[str, Any] = {
        "method_id": method_id, "formula_reference": reference, "inputs": inputs,
        "raw_total": raw, "rounded_total": final, "final_total": final,
        "raw_participants": raw, "rounded_participants": final, "final_participants": final,
        "rounding_rule": "ceil the unrounded participant count once after all formula terms",
        "warnings": list(warnings or ()), "provenance": None,
    }
    if extra:
        result.update(extra)
    return result


def correlation_detection(*, planned_correlation: float, null_correlation: float = 0.0,
                          alpha: float = 0.05, power: float = 0.80, sides: int = 2,
                          correlation_type: str = "pearson", tolerance: float = 1.0,
                          max_iterations: int = 100) -> dict[str, Any]:
    """CORR-001: corrected Fisher-z iteration, equations 19.1--19.3."""
    planned = _correlation("planned_correlation", planned_correlation)
    null = _correlation("null_correlation", null_correlation)
    if planned == null:
        raise ValueError("planned_correlation must differ from null_correlation")
    if correlation_type not in {"pearson", "spearman"}:
        raise ValueError("correlation_type must be 'pearson' or 'spearman'")
    alpha = _probability("alpha", alpha)
    power = _probability("power", power)
    if sides not in (1, 2):
        raise ValueError("sides must be 1 or 2")
    tolerance = float(tolerance)
    if not isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance must be greater than 0")
    if not isinstance(max_iterations, int) or max_iterations <= 0:
        raise ValueError("max_iterations must be a positive integer")
    z_alpha = NormalDist().inv_cdf(1 - alpha / sides)
    z_power = NormalDist().inv_cdf(power)
    numerator = (z_alpha + z_power) ** 2
    initial_effect = atanh(planned) - atanh(null)
    current = numerator / initial_effect ** 2 + 3
    history = [{"iteration": 0, "effect_z": initial_effect, "raw_n": current}]
    converged = False
    for iteration in range(1, max_iterations + 1):
        corrected_effect = initial_effect + (planned - null) / (2 * (current - 1))
        updated = numerator / corrected_effect ** 2 + 3
        history.append({"iteration": iteration, "effect_z": corrected_effect, "raw_n": updated,
                        "absolute_change": abs(updated - current)})
        if abs(updated - current) <= tolerance:
            current = updated
            converged = True
            break
        current = updated
    if not converged:
        raise ValueError("corrected Fisher-z iteration did not converge within max_iterations")
    return _result("CORR-001", "equations 19.1, 19.2, and 19.3", {
        "planned_correlation": planned, "null_correlation": null,
        "effect_direction": "planned minus null on corrected Fisher-z scale",
        "correlation_type": correlation_type, "alpha": alpha, "power": power,
        "sides": sides, "z_alpha": z_alpha, "z_power": z_power,
        "tolerance": tolerance, "max_iterations": max_iterations,
    }, current, extra={
        "initial_raw_total": history[0]["raw_n"], "iterations": len(history) - 1,
        "converged": converged, "iteration_history": history,
        "search": {"type": "fixed-point", "range": "N > 3", "tolerance": tolerance,
                   "max_iterations": max_iterations, "converged": converged},
    })


def pearson_ci_initial(*, planned_correlation: float, width: float,
                       confidence_level: float = 0.95) -> dict[str, Any]:
    """CORR-002: Pearson CI-width initial approximation, equations 19.4--19.5."""
    rho = _correlation("planned_correlation", planned_correlation)
    width = _width(width)
    confidence = _probability("confidence_level", confidence_level)
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    raw = 4 * z * z * (1 - rho * rho) ** 2 / width ** 2 + 3
    warnings = []
    if raw <= 55 or abs(rho) >= .7:
        warnings.append("equation 19.5 is described as most accurate for N>55 and |rho|<0.7")
    return _result("CORR-002", "equations 19.4 and 19.5", {
        "planned_correlation": rho, "width": width, "width_definition": "full CI width",
        "half_width": width / 2, "confidence_level": confidence, "z_confidence": z,
        "correlation_type": "pearson",
    }, raw, warnings=warnings)


def _refined_ci(*, method_id: str, parent_method: str, parent_result: dict[str, Any],
                rho: float, width: float, confidence: float, theta: float,
                reference: str) -> dict[str, Any]:
    consumed = consume_quantity(parent_result, allowed_parent_methods={parent_method},
                                key="raw_participants", quantity="participants",
                                unit="person", stage="raw")
    initial = float(consumed["value"])
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    center = atanh(rho)
    upper_z = center + theta * z / sqrt(initial - 3)
    lower_z = center - theta * z / sqrt(initial - 3)
    achieved_initial_width = tanh(upper_z) - tanh(lower_z)
    refined = (initial - 3) * (achieved_initial_width / width) ** 2 + 3
    result = _result(method_id, reference, {
        "planned_correlation": rho, "width": width, "width_definition": "full CI width",
        "half_width": width / 2, "confidence_level": confidence, "z_confidence": z,
        "theta": theta, "parent_method_id": parent_method,
    }, refined, extra={
        "initial_raw_total": initial,
        "initial_rounded_total": parent_result["rounded_participants"],
        "initial_achieved_width": achieved_initial_width,
        "refined_raw_total": refined, "iterations": 1, "converged": True,
        "search": {"type": "closed-form one-step Fisher refinement", "range": "N > 3",
                   "tolerance": None, "max_iterations": 1, "converged": True},
    })
    result["lineage"] = {
        "calculation_type": "refinement", "parent_method_id": parent_method,
        "consumed_result": consumed, "parent_primary_inputs": parent_result["inputs"],
        "parent_inference": {"confidence_level": confidence},
        "transformation": reference,
        "initial_raw_sample_size": initial,
        "initial_rounded_sample_size": parent_result["rounded_participants"],
        "refined_sample_size": refined,
        "iterations": 1, "converged": True,
        "child_outputs": [
            {"key": "raw_participants", "quantity": "participants", "unit": "person", "stage": "raw"},
            {"key": "final_participants", "quantity": "participants", "unit": "person", "stage": "final"},
        ],
        "parent_source_provenance": parent_result.get("source_provenance"),
        "parent_validation_evidence": parent_result.get("validation_evidence"),
    }
    return result


def pearson_ci_refined(*, planned_correlation: float, width: float,
                       confidence_level: float = 0.95) -> dict[str, Any]:
    """CORR-003: Pearson Fisher-transformed CI-width refinement, equations 19.6--19.8."""
    rho = _correlation("planned_correlation", planned_correlation)
    width = _width(width)
    confidence = _probability("confidence_level", confidence_level)
    parent = pearson_ci_initial(planned_correlation=rho, width=width,
                                confidence_level=confidence)
    return _refined_ci(method_id="CORR-003", parent_method="CORR-002",
                       parent_result=parent, rho=rho, width=width,
                       confidence=confidence, theta=1.0,
                       reference="equations 19.6, 19.7, and 19.8")


def spearman_ci_initial(*, planned_correlation: float, width: float,
                        confidence_level: float = 0.95) -> dict[str, Any]:
    """CORR-004: Spearman CI-width initial approximation, equations 19.9--19.10."""
    rho = _correlation("planned_correlation", planned_correlation)
    width = _width(width)
    confidence = _probability("confidence_level", confidence_level)
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    theta_squared = 1 + rho * rho / 2
    raw = 4 * z * z * (1 - rho * rho) ** 2 * theta_squared / width ** 2 + 3
    return _result("CORR-004", "equations 19.9 and 19.10", {
        "planned_correlation": rho, "width": width, "width_definition": "full CI width",
        "half_width": width / 2, "confidence_level": confidence, "z_confidence": z,
        "correlation_type": "spearman", "theta": sqrt(theta_squared),
    }, raw)


def spearman_ci_refined(*, planned_correlation: float, width: float,
                        confidence_level: float = 0.95) -> dict[str, Any]:
    """CORR-005: Spearman Fisher-transformed CI-width refinement, equations 19.6--19.8 and 19.11."""
    rho = _correlation("planned_correlation", planned_correlation)
    width = _width(width)
    confidence = _probability("confidence_level", confidence_level)
    parent = spearman_ci_initial(planned_correlation=rho, width=width,
                                 confidence_level=confidence)
    return _refined_ci(method_id="CORR-005", parent_method="CORR-004",
                       parent_result=parent, rho=rho, width=width,
                       confidence=confidence, theta=sqrt(1 + rho * rho / 2),
                       reference="equations 19.6, 19.7, 19.8, and 19.11")


correlation_detection = contracted(correlation_detection)
pearson_ci_initial = contracted(pearson_ci_initial)
pearson_ci_refined = contracted(pearson_ci_refined)
spearman_ci_initial = contracted(spearman_ci_initial)
spearman_ci_refined = contracted(spearman_ci_refined)
