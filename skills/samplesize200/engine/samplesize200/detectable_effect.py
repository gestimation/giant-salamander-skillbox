"""Analytic detectable-effect inversion for the first supported 16 models.

The existing fixed-design POWER adapters are the calculation source of truth.
This module only performs algebraic inversions of those planning equations and
then sends every result back through ``calculate_power``.  It does not add a
new test, approximation, distribution evaluation, or numerical root search.
"""

from __future__ import annotations

from math import exp, isclose, isfinite, log, sqrt
from statistics import NormalDist
from typing import Any, Callable, Mapping

from ._version import VERSION
from .binary import _proportion as _binary_proportion
from .continuous import superiority_probability_from_effect
from .distributions import critical_values
from .longitudinal import (
    _correlation as _longitudinal_correlation,
    _covariance as _longitudinal_covariance,
    post_mean_design_effect,
)
from .paired import (
    _discordant_odds as _paired_discordant_odds,
    _probability as _paired_probability,
)
from .power import (
    _allocation_design,
    _one_design,
    _pair_design,
    _positive_finite,
    calculate_power,
)
from .rates import _probability as _rate_probability, bonferroni_alpha


_NORMAL = NormalDist()
_POWER_VALIDATION_TOLERANCE = 1e-10

DETECTABLE_EFFECT_ENGINE_IDS = frozenset({
    "ONE-001", "ONE-002", "ONE-004",
    "TWO-005", "TWO-006", "TWO-009", "TWO-010", "TWO-011",
    "TWO-012", "TWO-013", "TWO-023", "TWO-026", "TWO-029",
    "TWO-031", "TWO-032", "TWO-033",
})


def _canonical_model_id(engine_id: str) -> str:
    canonical = str(engine_id).upper()
    for suffix in (".DETECTABLE_EFFECT", ".SAMPLE_SIZE", ".POWER", ".N"):
        if canonical.endswith(suffix):
            return canonical[:-len(suffix)]
    return canonical


def _target_critical_values(
    alpha: float, target_power: float, sides: int,
) -> tuple[float, float]:
    za, zt = critical_values(alpha, target_power, sides)
    null_limit = _NORMAL.cdf(-za)
    if target_power <= null_limit:
        raise ValueError(
            "target_power must exceed the existing planning equation's null-boundary power"
        )
    return za, zt


def _direction_sign(direction: str | None, *, field: str = "direction") -> tuple[int, str]:
    if not isinstance(direction, str):
        raise ValueError(f"{field} is required")
    normalized = direction.strip().lower().replace("-", "_").replace(" ", "_")
    positive = {
        "higher", "larger", "increase", "increased", "above", "greater",
        "positive", "right", "upper", "above_null",
    }
    negative = {
        "lower", "smaller", "decrease", "decreased", "below", "less",
        "negative", "left", "below_null",
    }
    if normalized in positive:
        return 1, "higher"
    if normalized in negative:
        return -1, "lower"
    raise ValueError(
        f"{field} must identify the higher/increase or lower/decrease alternative"
    )


def _inverse_quadratic_effect_distance(
    information_size: float,
    *,
    factor: float,
    additive_correction: float,
    z_alpha: float,
    z_target: float,
) -> float:
    """Invert information=factor*(z_alpha+z_target)^2/effect^2+H."""
    information = _positive_finite("information_size", information_size)
    factor = _positive_finite("factor", factor)
    correction = float(additive_correction)
    if not isfinite(correction) or correction < 0:
        raise ValueError("additive_correction must be finite and nonnegative")
    if information <= correction:
        raise ValueError(
            "realized design is not larger than the existing additive sample-size correction"
        )
    distance = (z_alpha + z_target) * sqrt(factor / (information - correction))
    return _positive_finite("detectable effect distance", distance)


def _inverse_fixed_log_ratio(
    information_size: float,
    *,
    allocation_ratio: float,
    gamma: float,
    z_alpha: float,
    z_target: float,
    direction_sign: int,
) -> float:
    information = _positive_finite("information_size", information_size)
    phi = _positive_finite("allocation_ratio", allocation_ratio)
    gamma = _positive_finite("gamma", gamma)
    magnitude = (z_alpha + z_target) * sqrt(
        gamma * (1 + phi) ** 2 / (phi * information)
    )
    if not isfinite(magnitude) or magnitude <= 0:
        raise ValueError("inputs do not produce a positive finite log-ratio distance")
    try:
        ratio = exp(direction_sign * magnitude)
    except OverflowError as exc:
        raise ValueError("detectable ratio is outside the finite numeric domain") from exc
    return _positive_finite("detectable ratio", ratio)


def _quadratic_roots(a: float, b: float, c: float) -> list[float]:
    """Return real algebraic roots without iterative search."""
    if not all(isfinite(value) for value in (a, b, c)):
        raise ValueError("quadratic coefficients must be finite")
    scale = max(1.0, abs(a), abs(b), abs(c))
    epsilon = 1e-14 * scale
    if abs(a) <= epsilon:
        if abs(b) <= epsilon:
            return []
        return [-c / b]
    discriminant = b * b - 4 * a * c
    discriminant_scale = max(1.0, b * b, abs(4 * a * c))
    if discriminant < -1e-14 * discriminant_scale:
        return []
    radical = sqrt(max(0.0, discriminant))
    if radical == 0:
        return [-b / (2 * a)]
    # The q form avoids avoidable cancellation for one of the roots.
    q = -0.5 * (b + radical if b >= 0 else b - radical)
    if q == 0:
        return [(-b + radical) / (2 * a), (-b - radical) / (2 * a)]
    return [q / a, c / q]


def _inverse_bounded_quadratic_candidate(
    a: float, b: float, c: float,
) -> list[float]:
    """Shared analytic candidate kernel for bounded quadratic inversions."""
    return _quadratic_roots(a, b, c)


def _inverse_poisson_rate_ratio_quadratic(
    *,
    total: int,
    allocation_ratio: float,
    standard_rate: float,
    exposure: float,
    z_alpha: float,
    z_target: float,
) -> list[float]:
    phi = _positive_finite("allocation_ratio", allocation_ratio)
    standard = _positive_finite("standard_rate", standard_rate)
    exposure = _positive_finite("exposure_per_subject", exposure)
    rsum = z_alpha + z_target
    q = total * standard * exposure * phi / ((1 + phi) * rsum ** 2)
    return _quadratic_roots(q, -(2 * q + 1), q - phi)


def _inverse_superiority_probability(
    *,
    total: int,
    allocation_ratio: float,
    z_alpha: float,
    z_target: float,
    direction_sign: int,
) -> float:
    phi = _positive_finite("allocation_ratio", allocation_ratio)
    distance = (z_alpha + z_target) * (1 + phi) / sqrt(12 * phi * total)
    probability = 0.5 + direction_sign * distance
    if not 0 < probability < 1:
        raise ValueError(
            "target power is unattainable within the superiority-probability domain"
        )
    return probability


def _select_power_validated_candidate(
    engine_id: str,
    candidates: list[float],
    *,
    target_power: float,
    distance_from_null: Callable[[float], float],
    power_inputs: Callable[[float], dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    valid: list[tuple[float, float, dict[str, Any]]] = []
    for candidate in candidates:
        if not isfinite(candidate):
            continue
        try:
            result = calculate_power(engine_id, power_inputs(candidate))
        except (TypeError, ValueError, OverflowError):
            continue
        residual = abs(result["achieved_power"] - target_power)
        if residual <= _POWER_VALIDATION_TOLERANCE:
            valid.append((distance_from_null(candidate), candidate, result))
    if not valid:
        raise ValueError(
            "target power is unattainable on the selected alternative branch "
            "under the existing POWER equation"
        )
    _, candidate, result = min(valid, key=lambda item: item[0])
    return candidate, result


def _detectable_result(
    engine_id: str,
    *,
    target_power: float,
    power_inputs: dict[str, Any],
    request_inputs: dict[str, Any],
    detectable_effect: float,
    result_name: str,
    null_boundary: float,
    alternative_direction: str,
    inverse_kernel: str,
    power_result: dict[str, Any] | None = None,
    effect_details: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    model = _canonical_model_id(engine_id)
    validated = power_result or calculate_power(model, power_inputs)
    residual = abs(validated["achieved_power"] - target_power)
    if residual > _POWER_VALIDATION_TOLERANCE:
        raise ValueError(
            "analytic inverse did not reproduce target_power in the existing POWER adapter"
        )
    combined_warnings = list(validated.get("warnings", []))
    for warning in warnings or []:
        if warning not in combined_warnings:
            combined_warnings.append(warning)
    result: dict[str, Any] = {
        "product": "samplesize200 Alpha",
        "version": VERSION,
        "release_stage": "alpha",
        "engine_id": model,
        "model_id": model,
        "method_id": model,
        "procedure_id": f"{model}.DETECTABLE_EFFECT",
        "source_power_procedure_id": f"{model}.POWER",
        "source_sample_size_procedure_id": f"{model}.SAMPLE_SIZE",
        "operation": "detectable_effect",
        "calculation_target": "detectable_effect",
        "result_type": "detectable_effect",
        "calculation_basis": "analytic_inverse_of_existing_power_method",
        "target_power": float(target_power),
        "achieved_power": validated["achieved_power"],
        "alpha": validated["alpha"],
        "sidedness": validated["sidedness"],
        "realized_design": validated["realized_design"],
        "method": validated["method"],
        "calculation_mode": "analytic_inverse_of_existing_power",
        "effect_measure": validated["effect_measure"],
        "detectable_effect": float(detectable_effect),
        "result_name": result_name,
        "null_boundary": float(null_boundary),
        "alternative_direction": alternative_direction,
        "inputs": request_inputs,
        "power_validation_inputs": power_inputs,
        "warnings": combined_warnings,
        "calculation_trace": {
            "kernel": inverse_kernel,
            "target_power": float(target_power),
            "power_validation_residual": residual,
            "source_power_kernel": validated.get("calculation_trace", {}).get("kernel"),
        },
        "schema_status": "preview",
        "final_public_api": False,
    }
    result["primary_result"] = {
        "key": result_name,
        "value": result["detectable_effect"],
        "quantity": validated["effect_measure"],
        "unit": "effect_scale",
        "stage": "final",
    }
    if effect_details:
        result.update(effect_details)
    if "adjusted_alpha" in validated:
        result["adjusted_alpha"] = validated["adjusted_alpha"]
    return result


def _detect_one_001(
    *, known_proportion: float, n: int, target_power: float,
    direction: str | None = None, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    _binary_proportion("known_proportion", known_proportion)
    p0 = float(known_proportion)
    design = _one_design(n)
    sign, canonical_direction = _direction_sign(direction)
    za, zt = _target_critical_values(alpha, target_power, sides)
    variance0 = p0 * (1 - p0)
    a = n + zt ** 2
    b = -2 * za * sqrt(n * variance0) - zt ** 2 * sign * (1 - 2 * p0)
    c = (za ** 2 - zt ** 2) * variance0
    distances = _inverse_bounded_quadratic_candidate(a, b, c)
    proportions = [p0 + sign * distance for distance in distances if distance > 0]

    def power_inputs(proportion: float) -> dict[str, Any]:
        return {
            "known_proportion": p0, "planned_proportion": proportion,
            "n": n, "alpha": alpha, "sides": sides,
        }

    planned, validation = _select_power_validated_candidate(
        "ONE-001", [p for p in proportions if 0 < p < 1],
        target_power=target_power,
        distance_from_null=lambda p: abs(p - p0), power_inputs=power_inputs,
    )
    signed_difference = planned - p0
    return _detectable_result(
        "ONE-001", target_power=target_power, power_inputs=power_inputs(planned),
        request_inputs={"known_proportion": p0, "n": n, "target_power": target_power,
                        "direction": direction, "alpha": alpha, "sides": sides},
        detectable_effect=signed_difference, result_name="detectable_risk_difference",
        null_boundary=p0, alternative_direction=canonical_direction,
        inverse_kernel="inverse_bounded_quadratic_candidate", power_result=validation,
        effect_details={"planned_proportion": planned,
                        "signed_risk_difference": signed_difference,
                        "realized_design": design},
    )


def _detect_one_002(
    *, known_mean: float, planned_sd: float, n: int, target_power: float,
    direction: str | None = None, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    if not isfinite(known_mean):
        raise ValueError("known_mean must be finite")
    sd = _positive_finite("planned_sd", planned_sd)
    _one_design(n)
    za, zt = _target_critical_values(alpha, target_power, sides)
    magnitude = _inverse_quadratic_effect_distance(
        n, factor=1.0, additive_correction=za ** 2 / 2,
        z_alpha=za, z_target=zt,
    )
    sign, canonical_direction = (1, "absolute_magnitude")
    if direction is not None:
        sign, canonical_direction = _direction_sign(direction)
    planned_mean = known_mean + sign * sd * magnitude
    power_inputs = {
        "known_mean": known_mean, "planned_mean": planned_mean,
        "planned_sd": sd, "n": n, "alpha": alpha, "sides": sides,
    }
    details: dict[str, Any] = {"standardized_effect_magnitude": magnitude}
    if direction is not None:
        details.update({"planned_mean": planned_mean,
                        "signed_mean_difference": planned_mean - known_mean})
    return _detectable_result(
        "ONE-002", target_power=target_power, power_inputs=power_inputs,
        request_inputs={"known_mean": known_mean, "planned_sd": sd, "n": n,
                        "target_power": target_power, "direction": direction,
                        "alpha": alpha, "sides": sides},
        detectable_effect=magnitude,
        result_name="detectable_standardized_mean_difference_magnitude",
        null_boundary=0.0, alternative_direction=canonical_direction,
        inverse_kernel="inverse_quadratic_effect_distance", effect_details=details,
        warnings=[] if direction is not None else [
            "POWER is sign-symmetric; no signed planned mean was requested"
        ],
    )


def _detect_one_004(
    *, background_rate: float, n: int, target_power: float,
    alpha: float = 0.05, sides: int = 1, number_of_reactions: int = 1,
) -> dict[str, Any]:
    _rate_probability("background_rate", background_rate, allow_zero=True)
    background = float(background_rate)
    _one_design(n)
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    za, zt = _target_critical_values(adjusted_alpha, target_power, sides)
    a = float(n)
    b = -2 * za * sqrt(n * background) - zt ** 2
    c = (za ** 2 - zt ** 2) * background
    candidates = [
        value for value in _inverse_bounded_quadratic_candidate(a, b, c)
        if value > 0 and background + value < 1
    ]

    def power_inputs(additional: float) -> dict[str, Any]:
        return {
            "background_rate": background, "additional_rate": additional,
            "n": n, "alpha": alpha, "sides": sides,
            "number_of_reactions": number_of_reactions,
        }

    additional, validation = _select_power_validated_candidate(
        "ONE-004", candidates, target_power=target_power,
        distance_from_null=lambda value: value, power_inputs=power_inputs,
    )
    return _detectable_result(
        "ONE-004", target_power=target_power, power_inputs=power_inputs(additional),
        request_inputs={"background_rate": background, "n": n,
                        "target_power": target_power, "alpha": alpha, "sides": sides,
                        "number_of_reactions": number_of_reactions},
        detectable_effect=additional, result_name="detectable_additional_rate",
        null_boundary=0.0, alternative_direction="increase",
        inverse_kernel="inverse_bounded_quadratic_candidate", power_result=validation,
        effect_details={"additional_rate": additional,
                        "planned_total_rate": background + additional},
    )


def _detect_two_005_or_006(
    engine_id: str, *, category_count: int, n_control: int, n_treatment: int,
    target_power: float, direction: str | None = None,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    if isinstance(category_count, bool) or not isinstance(category_count, int):
        raise ValueError("category_count must be an integer")
    if engine_id == "TWO-005" and category_count < 2:
        raise ValueError("category_count must be an integer of at least 2")
    if engine_id == "TWO-006" and category_count <= 5:
        raise ValueError("category_count must be an integer greater than 5")
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment / n_control
    sign, canonical_direction = _direction_sign(direction)
    za, zt = _target_critical_values(alpha, target_power, sides)
    gamma = 3 / (1 - 1 / category_count ** 2) if engine_id == "TWO-005" else 3.0
    odds = _inverse_fixed_log_ratio(
        design["total"], allocation_ratio=phi, gamma=gamma,
        z_alpha=za, z_target=zt, direction_sign=sign,
    )
    power_inputs = {
        "category_count": category_count, "odds_ratio": odds,
        "n_control": n_control, "n_treatment": n_treatment,
        "alpha": alpha, "sides": sides,
    }
    return _detectable_result(
        engine_id, target_power=target_power, power_inputs=power_inputs,
        request_inputs={"category_count": category_count, "n_control": n_control,
                        "n_treatment": n_treatment, "target_power": target_power,
                        "direction": direction, "alpha": alpha, "sides": sides},
        detectable_effect=odds, result_name="detectable_odds_ratio",
        null_boundary=1.0, alternative_direction=canonical_direction,
        inverse_kernel="inverse_fixed_log_ratio",
        effect_details={"odds_ratio": odds, "log_odds_ratio": log(odds),
                        "allocation_ratio": phi},
    )


def _detect_two_005(**inputs: Any) -> dict[str, Any]:
    return _detect_two_005_or_006("TWO-005", **inputs)


def _detect_two_006(**inputs: Any) -> dict[str, Any]:
    return _detect_two_005_or_006("TWO-006", **inputs)


def _two_group_quadratic_effect(
    *, n_control: int, n_treatment: int, factor: float,
    correction: float, alpha: float, sides: int, target_power: float,
) -> tuple[dict[str, Any], float, float, float]:
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    za, zt = _target_critical_values(alpha, target_power, sides)
    magnitude = _inverse_quadratic_effect_distance(
        design["total"], factor=factor, additive_correction=correction,
        z_alpha=za, z_target=zt,
    )
    return design, n_treatment / n_control, za, magnitude


def _detect_two_009(
    *, n_control: int, n_treatment: int, target_power: float,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment / n_control
    za, zt = _target_critical_values(alpha, target_power, sides)
    magnitude = _inverse_quadratic_effect_distance(
        design["total"], factor=(1 + phi) ** 2 / phi,
        additive_correction=za ** 2 / 2, z_alpha=za, z_target=zt,
    )
    power_inputs = {"standardized_effect": magnitude, "n_control": n_control,
                    "n_treatment": n_treatment, "alpha": alpha, "sides": sides}
    return _detectable_result(
        "TWO-009", target_power=target_power, power_inputs=power_inputs,
        request_inputs={"n_control": n_control, "n_treatment": n_treatment,
                        "target_power": target_power, "alpha": alpha, "sides": sides},
        detectable_effect=magnitude,
        result_name="detectable_standardized_mean_difference_magnitude",
        null_boundary=0.0, alternative_direction="absolute_magnitude",
        inverse_kernel="inverse_quadratic_effect_distance",
        effect_details={"standardized_effect_magnitude": magnitude,
                        "allocation_ratio": phi},
    )


def _detect_two_010(
    *, control_sd: float, treatment_sd: float, n_control: int, n_treatment: int,
    target_power: float, direction: str | None = None,
    variance_ratio: float | None = None,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    csd = _positive_finite("control_sd", control_sd)
    tsd = _positive_finite("treatment_sd", treatment_sd)
    tau = (tsd / csd) ** 2
    if variance_ratio is not None:
        supplied = _positive_finite("variance_ratio", variance_ratio)
        if abs(supplied - tau) > max(1e-12, tau * 1e-10):
            raise ValueError("variance_ratio must equal treatment variance / control variance")
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment / n_control
    sign, canonical_direction = _direction_sign(direction)
    za, zt = _target_critical_values(alpha, target_power, sides)
    correction = (
        (1 + phi) * (tau ** 2 + phi ** 3) * za ** 2
        / (2 * phi * (tau + phi) ** 2)
    )
    standardized = _inverse_quadratic_effect_distance(
        design["total"], factor=(1 + phi) * (tau + phi) / phi,
        additive_correction=correction, z_alpha=za, z_target=zt,
    )
    difference = sign * csd * standardized
    power_inputs = {
        "planned_mean_difference": difference, "control_sd": csd,
        "treatment_sd": tsd, "variance_ratio": tau,
        "n_control": n_control, "n_treatment": n_treatment,
        "alpha": alpha, "sides": sides,
    }
    return _detectable_result(
        "TWO-010", target_power=target_power, power_inputs=power_inputs,
        request_inputs={"control_sd": csd, "treatment_sd": tsd,
                        "variance_ratio": variance_ratio, "n_control": n_control,
                        "n_treatment": n_treatment, "target_power": target_power,
                        "direction": direction, "alpha": alpha, "sides": sides},
        detectable_effect=difference, result_name="detectable_mean_difference",
        null_boundary=0.0, alternative_direction=canonical_direction,
        inverse_kernel="inverse_quadratic_effect_distance",
        effect_details={"signed_mean_difference": difference,
                        "standardized_effect_magnitude": standardized,
                        "allocation_ratio": phi, "variance_ratio": tau},
    )


def _detect_two_011(
    *, efficiency_factor: float, n_control: int, n_treatment: int,
    target_power: float, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    efficiency = _positive_finite("efficiency_factor", efficiency_factor)
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment / n_control
    za, zt = _target_critical_values(alpha, target_power, sides)
    magnitude = _inverse_quadratic_effect_distance(
        design["total"], factor=efficiency * (1 + phi) ** 2 / phi,
        additive_correction=za ** 2 / 2, z_alpha=za, z_target=zt,
    )
    power_inputs = {"standardized_effect": magnitude,
                    "efficiency_factor": efficiency, "n_control": n_control,
                    "n_treatment": n_treatment, "alpha": alpha, "sides": sides}
    return _detectable_result(
        "TWO-011", target_power=target_power, power_inputs=power_inputs,
        request_inputs={"efficiency_factor": efficiency, "n_control": n_control,
                        "n_treatment": n_treatment, "target_power": target_power,
                        "alpha": alpha, "sides": sides},
        detectable_effect=magnitude,
        result_name="detectable_standardized_location_effect_magnitude",
        null_boundary=0.0, alternative_direction="absolute_magnitude",
        inverse_kernel="inverse_quadratic_effect_distance",
        effect_details={"standardized_effect_magnitude": magnitude,
                        "allocation_ratio": phi},
    )


def _detect_two_012(
    *, n_control: int, n_treatment: int, target_power: float,
    direction: str | None = None, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment / n_control
    sign, canonical_direction = _direction_sign(direction)
    za, zt = _target_critical_values(alpha, target_power, sides)
    probability = _inverse_superiority_probability(
        total=design["total"], allocation_ratio=phi, z_alpha=za,
        z_target=zt, direction_sign=sign,
    )
    standardized = sqrt(2) * _NORMAL.inv_cdf(probability)
    # Exercise the current transform in QC without making it the source formula.
    if not isclose(
        superiority_probability_from_effect(standardized), probability,
        rel_tol=0.0, abs_tol=1e-14,
    ):
        raise ValueError("existing superiority-probability scale transform did not round trip")
    power_inputs = {"superiority_probability": probability,
                    "n_control": n_control, "n_treatment": n_treatment,
                    "alpha": alpha, "sides": sides}
    return _detectable_result(
        "TWO-012", target_power=target_power, power_inputs=power_inputs,
        request_inputs={"n_control": n_control, "n_treatment": n_treatment,
                        "target_power": target_power, "direction": direction,
                        "alpha": alpha, "sides": sides},
        detectable_effect=probability,
        result_name="detectable_superiority_probability",
        null_boundary=0.5, alternative_direction=canonical_direction,
        inverse_kernel="inverse_superiority_probability",
        effect_details={"superiority_probability": probability,
                        "standardized_effect": standardized,
                        "distance_from_null": abs(probability - 0.5),
                        "allocation_ratio": phi},
    )


def _detect_two_013(
    *, standard_rate: float, n_standard: int, n_treatment: int,
    target_power: float, direction: str | None = None,
    exposure_per_subject: float = 1.0,
    alpha: float = 0.05, sides: int = 2, number_of_reactions: int = 1,
) -> dict[str, Any]:
    standard = _positive_finite("standard_rate", standard_rate)
    exposure = _positive_finite("exposure_per_subject", exposure_per_subject)
    design = _allocation_design("standard", n_standard, "treatment", n_treatment)
    phi = n_treatment / n_standard
    sign, canonical_direction = _direction_sign(direction)
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    za, zt = _target_critical_values(adjusted_alpha, target_power, sides)
    candidates = _inverse_poisson_rate_ratio_quadratic(
        total=design["total"], allocation_ratio=phi, standard_rate=standard,
        exposure=exposure, z_alpha=za, z_target=zt,
    )
    candidates = [
        ratio for ratio in candidates
        if ratio > 0 and ((sign > 0 and ratio > 1) or (sign < 0 and ratio < 1))
    ]

    def power_inputs(ratio: float) -> dict[str, Any]:
        return {
            "standard_rate": standard, "rate_ratio": ratio,
            "exposure_per_subject": exposure, "n_standard": n_standard,
            "n_treatment": n_treatment, "alpha": alpha, "sides": sides,
            "number_of_reactions": number_of_reactions,
        }

    ratio, validation = _select_power_validated_candidate(
        "TWO-013", candidates, target_power=target_power,
        distance_from_null=lambda value: abs(log(value)), power_inputs=power_inputs,
    )
    return _detectable_result(
        "TWO-013", target_power=target_power, power_inputs=power_inputs(ratio),
        request_inputs={"standard_rate": standard,
                        "exposure_per_subject": exposure, "n_standard": n_standard,
                        "n_treatment": n_treatment, "target_power": target_power,
                        "direction": direction, "alpha": alpha, "sides": sides,
                        "number_of_reactions": number_of_reactions},
        detectable_effect=ratio, result_name="detectable_rate_ratio",
        null_boundary=1.0, alternative_direction=canonical_direction,
        inverse_kernel="inverse_poisson_rate_ratio_quadratic", power_result=validation,
        effect_details={"rate_ratio": ratio, "log_rate_ratio": log(ratio),
                        "treatment_rate": standard * ratio,
                        "allocation_ratio": phi},
    )


def _detect_two_023(
    *, discordant_fraction: float, n_pairs: int, target_power: float,
    direction: str | None = None, alpha: float = 0.05, sides: int = 2,
    subjects_per_pair: int = 1, even_sequence: bool = False,
) -> dict[str, Any]:
    fraction = _paired_probability("discordant_fraction", discordant_fraction, strict=False)
    if fraction == 0:
        raise ValueError("discordant_fraction must be greater than 0")
    _pair_design(n_pairs, even_sequence=even_sequence, subjects_per_pair=subjects_per_pair)
    sign, canonical_direction = _direction_sign(direction)
    za, zt = _target_critical_values(alpha, target_power, sides)
    root_n = sqrt(fraction * n_pairs)
    linear_psi = sign * root_n - za
    linear_constant = -sign * root_n - za
    a = linear_psi ** 2 - zt ** 2 * (1 - fraction)
    b = 2 * linear_psi * linear_constant - zt ** 2 * (2 + 2 * fraction)
    c = linear_constant ** 2 - zt ** 2 * (1 - fraction)
    candidates = [
        _paired_discordant_odds(value)
        for value in _inverse_bounded_quadratic_candidate(a, b, c)
        if value > 0 and ((sign > 0 and value > 1) or (sign < 0 and value < 1))
    ]

    def power_inputs(odds: float) -> dict[str, Any]:
        return {
            "discordant_odds_ratio": odds, "discordant_fraction": fraction,
            "n_pairs": n_pairs, "alpha": alpha, "sides": sides,
            "subjects_per_pair": subjects_per_pair, "even_sequence": even_sequence,
        }

    odds, validation = _select_power_validated_candidate(
        "TWO-023", candidates, target_power=target_power,
        distance_from_null=lambda value: abs(log(value)), power_inputs=power_inputs,
    )
    return _detectable_result(
        "TWO-023", target_power=target_power, power_inputs=power_inputs(odds),
        request_inputs={"discordant_fraction": fraction, "n_pairs": n_pairs,
                        "target_power": target_power, "direction": direction,
                        "alpha": alpha, "sides": sides,
                        "subjects_per_pair": subjects_per_pair,
                        "even_sequence": even_sequence},
        detectable_effect=odds, result_name="detectable_discordant_odds_ratio",
        null_boundary=1.0, alternative_direction=canonical_direction,
        inverse_kernel="inverse_bounded_quadratic_candidate", power_result=validation,
        effect_details={"discordant_odds_ratio": odds,
                        "absolute_log_odds_ratio": abs(log(odds))},
    )


def _paired_quadratic_effect(
    engine_id: str, *, n_pairs: int, target_power: float,
    alpha: float, sides: int, subjects_per_pair: int, even_sequence: bool,
) -> dict[str, Any]:
    _pair_design(n_pairs, even_sequence=even_sequence, subjects_per_pair=subjects_per_pair)
    za, zt = _target_critical_values(alpha, target_power, sides)
    magnitude = _inverse_quadratic_effect_distance(
        n_pairs, factor=2.0, additive_correction=za ** 2 / 2,
        z_alpha=za, z_target=zt,
    )
    power_inputs = {"standardized_effect": magnitude, "n_pairs": n_pairs,
                    "alpha": alpha, "sides": sides,
                    "subjects_per_pair": subjects_per_pair,
                    "even_sequence": even_sequence}
    result_name = (
        "detectable_paired_standardized_effect_magnitude"
        if engine_id == "TWO-026"
        else "detectable_paired_standardized_mean_difference_magnitude"
    )
    return _detectable_result(
        engine_id, target_power=target_power, power_inputs=power_inputs,
        request_inputs={"n_pairs": n_pairs, "target_power": target_power,
                        "alpha": alpha, "sides": sides,
                        "subjects_per_pair": subjects_per_pair,
                        "even_sequence": even_sequence},
        detectable_effect=magnitude, result_name=result_name,
        null_boundary=0.0, alternative_direction="absolute_magnitude",
        inverse_kernel="inverse_quadratic_effect_distance",
        effect_details={"standardized_effect_magnitude": magnitude},
    )


def _detect_two_026(
    *, n_pairs: int, target_power: float, alpha: float = 0.05, sides: int = 2,
    subjects_per_pair: int = 1, even_sequence: bool = False,
) -> dict[str, Any]:
    return _paired_quadratic_effect(
        "TWO-026", n_pairs=n_pairs, target_power=target_power,
        alpha=alpha, sides=sides, subjects_per_pair=subjects_per_pair,
        even_sequence=even_sequence,
    )


def _detect_two_029(
    *, n_pairs: int, target_power: float, alpha: float = 0.05, sides: int = 2,
    subjects_per_pair: int = 1, even_sequence: bool = False,
) -> dict[str, Any]:
    return _paired_quadratic_effect(
        "TWO-029", n_pairs=n_pairs, target_power=target_power,
        alpha=alpha, sides=sides, subjects_per_pair=subjects_per_pair,
        even_sequence=even_sequence,
    )


def _longitudinal_detectable(
    engine_id: str, *, difference_key: str, planned_sd: float,
    design_effect: float, power_nuisance: dict[str, Any], n_control: int,
    n_treatment: int, target_power: float, direction: str,
    alpha: float, sides: int, warnings: list[str] | None = None,
) -> dict[str, Any]:
    sd = _positive_finite("planned_sd", planned_sd)
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment / n_control
    sign, canonical_direction = _direction_sign(direction)
    za, zt = _target_critical_values(alpha, target_power, sides)
    standardized = _inverse_quadratic_effect_distance(
        design["total"] / design_effect, factor=(1 + phi) ** 2 / phi,
        additive_correction=za ** 2 / 2, z_alpha=za, z_target=zt,
    )
    difference = sign * sd * standardized
    power_inputs = {
        difference_key: difference, **power_nuisance,
        "n_control": n_control, "n_treatment": n_treatment,
        "alpha": alpha, "sides": sides,
    }
    result_names = {
        "TWO-031": "detectable_repeated_post_mean_difference",
        "TWO-032": "detectable_repeated_slope_difference",
        "TWO-033": "detectable_repeated_weighted_difference",
    }
    return _detectable_result(
        engine_id, target_power=target_power, power_inputs=power_inputs,
        request_inputs={**power_nuisance, "n_control": n_control,
                        "n_treatment": n_treatment, "target_power": target_power,
                        "direction": direction, "alpha": alpha, "sides": sides},
        detectable_effect=difference, result_name=result_names[engine_id],
        null_boundary=0.0, alternative_direction=canonical_direction,
        inverse_kernel="inverse_quadratic_effect_distance", warnings=warnings,
        effect_details={"signed_difference": difference,
                        "standardized_effect_magnitude": standardized,
                        "design_effect": design_effect,
                        "realized_effective_total": design["total"] / design_effect,
                        "allocation_ratio": phi},
    )


def _detect_two_031(
    *, planned_sd: float, pre_measurements: int, post_measurements: int,
    correlation: float, n_control: int, n_treatment: int, target_power: float,
    direction: str | None = None, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    design_effect = post_mean_design_effect(
        pre_measurements=pre_measurements, post_measurements=post_measurements,
        correlation=correlation,
    )
    return _longitudinal_detectable(
        "TWO-031", difference_key="planned_mean_difference",
        planned_sd=planned_sd, design_effect=design_effect,
        power_nuisance={"planned_sd": planned_sd,
                        "pre_measurements": pre_measurements,
                        "post_measurements": post_measurements,
                        "correlation": correlation},
        n_control=n_control, n_treatment=n_treatment,
        target_power=target_power, direction=direction, alpha=alpha, sides=sides,
    )


def _detect_two_032(
    *, planned_intercept_sd: float, measurement_times: list[float],
    correlation: float, n_control: int, n_treatment: int, target_power: float,
    direction: str | None = None, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    sd = _positive_finite("planned_intercept_sd", planned_intercept_sd)
    times = [float(value) for value in measurement_times]
    if len(times) < 2 or any(not isfinite(value) for value in times) or len(set(times)) != len(times):
        raise ValueError("measurement_times must contain at least two distinct finite times")
    rho = _longitudinal_correlation(correlation, len(times))
    mean_time = sum(times) / len(times)
    time_sum_squares = sum((value - mean_time) ** 2 for value in times)
    if time_sum_squares <= 0:
        raise ValueError("measurement_times must have positive dispersion")
    design_effect = (1 - rho) / time_sum_squares
    return _longitudinal_detectable(
        "TWO-032", difference_key="planned_slope_difference",
        planned_sd=sd, design_effect=design_effect,
        power_nuisance={"planned_intercept_sd": sd,
                        "measurement_times": times, "correlation": rho},
        n_control=n_control, n_treatment=n_treatment,
        target_power=target_power, direction=direction, alpha=alpha, sides=sides,
    )


def _detect_two_033(
    *, planned_sd: float, weights: list[float], correlation_structure: str,
    n_control: int, n_treatment: int, target_power: float,
    direction: str | None = None,
    correlation: float | None = None, measurement_times: list[float] | None = None,
    covariance_matrix: list[list[float]] | None = None,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    sd = _positive_finite("planned_sd", planned_sd)
    weight_values = [float(value) for value in weights]
    if (
        len(weight_values) < 2
        or any(not isfinite(value) for value in weight_values)
        or all(value == 0 for value in weight_values)
    ):
        raise ValueError("weights must contain at least two finite values and not be all zero")
    times = None if measurement_times is None else [float(value) for value in measurement_times]
    variance, matrix = _longitudinal_covariance(
        weight_values, sd, correlation_structure, correlation, times, covariance_matrix,
    )
    warnings = []
    if not isclose(sum(weight_values), 0.0, rel_tol=0.0, abs_tol=1e-10):
        warnings.append(
            "weights do not sum to zero; this is a weighted estimand rather than a contrast"
        )
    return _longitudinal_detectable(
        "TWO-033", difference_key="planned_contrast_difference",
        planned_sd=sd, design_effect=variance / sd ** 2,
        power_nuisance={"planned_sd": sd, "weights": weight_values,
                        "correlation_structure": correlation_structure,
                        "correlation": correlation, "measurement_times": times,
                        "covariance_matrix": matrix},
        n_control=n_control, n_treatment=n_treatment,
        target_power=target_power, direction=direction, alpha=alpha, sides=sides,
        warnings=warnings,
    )


DETECTABLE_EFFECT_METHODS: dict[str, Callable[..., dict[str, Any]]] = {
    "ONE-001": _detect_one_001,
    "ONE-002": _detect_one_002,
    "ONE-004": _detect_one_004,
    "TWO-005": _detect_two_005,
    "TWO-006": _detect_two_006,
    "TWO-009": _detect_two_009,
    "TWO-010": _detect_two_010,
    "TWO-011": _detect_two_011,
    "TWO-012": _detect_two_012,
    "TWO-013": _detect_two_013,
    "TWO-023": _detect_two_023,
    "TWO-026": _detect_two_026,
    "TWO-029": _detect_two_029,
    "TWO-031": _detect_two_031,
    "TWO-032": _detect_two_032,
    "TWO-033": _detect_two_033,
}


def calculate_detectable_effect(
    engine_id: str, inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the analytic effect that reproduces target POWER at a fixed design."""
    model = _canonical_model_id(engine_id)
    if model not in DETECTABLE_EFFECT_ENGINE_IDS:
        raise ValueError(f"detectable_effect is not supported for {engine_id}")
    if not isinstance(inputs, Mapping):
        raise TypeError("detectable-effect inputs must be a mapping")
    return DETECTABLE_EFFECT_METHODS[model](**dict(inputs))


__all__ = [
    "DETECTABLE_EFFECT_ENGINE_IDS", "DETECTABLE_EFFECT_METHODS",
    "calculate_detectable_effect",
]
