"""Phase 1 achieved-power evaluation for validated sample-size methods.

The functions in this module reverse the existing sample-size equations at a
fixed, realized integer design.  They are planning-equation power values, not
replacement power methods for the eventual analysis.
"""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from math import gcd, isclose, isfinite, log, sqrt
from statistics import NormalDist
from typing import Any, Callable, Mapping

from ._version import VERSION
from .binary import _proportion as _binary_proportion
from .continuous import (
    _effect as _continuous_effect,
    _nct_power,
    superiority_probability_from_effect,
)
from .distributions import critical_values
from .margin import (
    _direction as _margin_direction,
    _ni_boundary as _margin_ni_boundary,
    _paired_joint as _margin_paired_joint,
    _positive as _margin_positive,
    _probability as _margin_probability,
    _hr_component as _margin_hr_component,
)
from .longitudinal import (
    _correlation as _longitudinal_correlation,
    _covariance as _longitudinal_covariance,
    post_mean_design_effect,
)
from .ordinal import (
    _odds_ratio as _ordinal_odds_ratio,
    _probabilities as _ordinal_probabilities,
    _proportional_treatment,
)
from .paired import (
    _discordant_odds as _paired_discordant_odds,
    _effect_from_scores as _paired_effect_from_scores,
    _paired_t_power,
    _probability as _paired_probability,
)
from .rates import _probability as _rate_probability, bonferroni_alpha


_NORMAL = NormalDist()

BATCH_1_ENGINE_IDS = frozenset({
    "ONE-001", "ONE-004", "TWO-001", "TWO-015", "TWO-016", "TWO-023",
    "MARGIN-004", "MARGIN-005",
})
BATCH_2_ENGINE_IDS = frozenset({
    "ONE-002", "TWO-002", "TWO-004", "TWO-005", "TWO-006", "TWO-007",
    "TWO-009", "TWO-010", "TWO-011", "TWO-012", "TWO-013", "TWO-014",
    "TWO-026", "TWO-029", "TWO-031", "TWO-032", "TWO-033",
    "MARGIN-001", "MARGIN-002", "MARGIN-006",
})
BATCH_3_ENGINE_IDS = frozenset({"TWO-008", "TWO-030"})
PHASE1_POWER_ENGINE_IDS = frozenset(
    BATCH_1_ENGINE_IDS | BATCH_2_ENGINE_IDS | BATCH_3_ENGINE_IDS
)


def _positive_integer(name: str, value: int, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer of at least {minimum}")
    return value


def _positive_finite(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")
    return value


def _nonnegative_finite(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return value


def _z_alpha(alpha: float, sidedness: int) -> float:
    # power=0.5 gives z_beta=0 and reuses the existing inference validation.
    return critical_values(alpha, 0.5, sidedness)[0]


def _normal_power_from_zbeta(z_beta: float) -> float:
    if not isfinite(z_beta):
        raise ValueError("the existing sample-size inverse did not produce a finite z_beta")
    return min(1.0, max(0.0, float(_NORMAL.cdf(z_beta))))


def _achieved_power_weighted_normal(
    information_size: float,
    *,
    scale: float,
    null_weight: float,
    alternative_weight: float,
    distance: float,
    z_alpha: float,
) -> tuple[float, float]:
    """Invert N=L*(z_alpha*A+z_beta*B)^2/D^2."""
    size = _positive_finite("information_size", information_size)
    scale = _positive_finite("scale", scale)
    null_weight = _nonnegative_finite("null_weight", null_weight)
    alternative_weight = _positive_finite("alternative_weight", alternative_weight)
    distance = _positive_finite("distance", distance)
    z_beta = (distance * sqrt(size / scale) - z_alpha * null_weight) / alternative_weight
    return _normal_power_from_zbeta(z_beta), z_beta


def _achieved_power_quadratic_normal(
    information_size: float,
    *,
    coefficient: float,
    additive_correction: float,
    z_alpha: float,
) -> tuple[float, float]:
    """Invert N=K*(z_alpha+z_beta)^2+H."""
    size = _positive_finite("information_size", information_size)
    coefficient = _positive_finite("coefficient", coefficient)
    correction = float(additive_correction)
    if not isfinite(correction) or correction < 0:
        raise ValueError("additive_correction must be finite and nonnegative")
    if size <= correction:
        raise ValueError(
            "realized design is not larger than the existing additive sample-size correction"
        )
    z_beta = sqrt((size - correction) / coefficient) - z_alpha
    return _normal_power_from_zbeta(z_beta), z_beta


def _achieved_power_existing_distribution(value: float) -> float:
    """Validate a fixed-N power returned by an already-used distribution evaluator."""
    value = float(value)
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("existing distribution evaluator returned power outside [0, 1]")
    return value


def _achieved_power_existing_noncentral_t(
    evaluator: Callable[..., float], *args: Any, **kwargs: Any
) -> float:
    """Batch 3 kernel: call an existing fixed-N noncentral-t evaluator once."""
    return _achieved_power_existing_distribution(evaluator(*args, **kwargs))


def _one_design(n: int) -> dict[str, Any]:
    n = _positive_integer("n", n)
    return {"unit": "participants", "n": n, "total": n}


def _allocation_design(first_role: str, first: int, second_role: str, second: int) -> dict[str, Any]:
    first = _positive_integer(f"n_{first_role}", first)
    second = _positive_integer(f"n_{second_role}", second)
    divisor = gcd(first, second)
    return {
        "unit": "participants",
        "groups": {first_role: first, second_role: second},
        "total": first + second,
        "allocation_block": {first_role: first // divisor, second_role: second // divisor},
    }


def _pair_design(n_pairs: int, *, even_sequence: bool, subjects_per_pair: int) -> dict[str, Any]:
    n_pairs = _positive_integer("n_pairs", n_pairs)
    subjects_per_pair = _positive_integer("subjects_per_pair", subjects_per_pair)
    if not isinstance(even_sequence, bool):
        raise ValueError("even_sequence must be boolean")
    if even_sequence and n_pairs % 2:
        raise ValueError("n_pairs must be even when even_sequence is true")
    return {
        "unit": "pairs",
        "n_pairs": n_pairs,
        "subjects_per_pair": subjects_per_pair,
        "total_participants": n_pairs * subjects_per_pair,
        "even_sequence": even_sequence,
    }


def _matched_design(n_cases: int, n_controls: int) -> dict[str, Any]:
    cases = _positive_integer("n_cases", n_cases)
    controls = _positive_integer("n_controls", n_controls)
    if controls % cases:
        raise ValueError("n_controls must be an exact integer multiple of n_cases")
    controls_per_case = controls // cases
    return {
        "unit": "matched_units",
        "n_cases": cases,
        "n_controls": controls,
        "controls_per_case": controls_per_case,
        "matched_units": cases,
        "total_participants": cases + controls,
    }


def previous_feasible_design(engine_id: str, realized_design: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return the preceding complete integer design used by Phase 1 QC."""
    model = _canonical_model_id(engine_id)
    design = deepcopy(dict(realized_design))
    unit = design.get("unit")
    if unit == "participants" and "n" in design:
        if design["n"] <= 1:
            return None
        design["n"] -= 1
        design["total"] -= 1
        return design
    if unit == "participants" and "groups" in design:
        groups = dict(design["groups"])
        block = dict(design["allocation_block"])
        minimum = 2 if model == "TWO-008" else 1
        if any(groups[role] - block[role] < minimum for role in groups):
            return None
        for role in groups:
            groups[role] -= block[role]
        design["groups"] = groups
        design["total"] = sum(groups.values())
        return design
    if unit == "matched_units":
        if design["n_cases"] <= 1:
            return None
        decrement = design["controls_per_case"]
        design["n_cases"] -= 1
        design["matched_units"] -= 1
        design["n_controls"] -= decrement
        design["total_participants"] -= decrement + 1
        return design
    if unit == "pairs":
        decrement = 2 if design.get("even_sequence") else 1
        minimum = 2 if model == "TWO-030" else 1
        if design["n_pairs"] - decrement < minimum:
            return None
        design["n_pairs"] -= decrement
        design["total_participants"] -= decrement * design["subjects_per_pair"]
        return design
    raise ValueError("unrecognized realized design")


def _power_result(
    engine_id: str,
    *,
    achieved_power: float,
    alpha: float,
    sidedness: int,
    realized_design: dict[str, Any],
    method: str,
    calculation_mode: str,
    inputs: dict[str, Any],
    warnings: list[str] | None = None,
    trace: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model = _canonical_model_id(engine_id)
    result: dict[str, Any] = {
        "product": "SAMPLESIZE200 Alpha",
        "version": VERSION,
        "release_stage": "alpha",
        "engine_id": model,
        "model_id": model,
        "method_id": model,
        "procedure_id": f"{model}.POWER",
        "source_sample_size_procedure_id": f"{model}.SAMPLE_SIZE",
        "operation": "power",
        "calculation_target": "power",
        "result_type": "achieved_power",
        "calculation_basis": "inverse_of_existing_sample_size_method",
        "achieved_power": _achieved_power_existing_distribution(achieved_power),
        "alpha": float(alpha),
        "sidedness": sidedness,
        "realized_design": realized_design,
        "method": method,
        "calculation_mode": calculation_mode,
        "inputs": inputs,
        "warnings": list(warnings or []),
        "calculation_trace": dict(trace or {}),
        "schema_status": "preview",
        "final_public_api": False,
    }
    result["primary_result"] = {
        "key": "achieved_power",
        "value": result["achieved_power"],
        "quantity": "power",
        "unit": "probability",
        "stage": "final",
    }
    if extra:
        result.update(extra)
    return result


def _quadratic_power_result(
    engine_id: str,
    *,
    information_size: float,
    coefficient: float,
    additive_correction: float,
    alpha: float,
    sidedness: int,
    realized_design: dict[str, Any],
    method: str,
    inputs: dict[str, Any],
    trace: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    za = _z_alpha(alpha, sidedness)
    achieved, zb = _achieved_power_quadratic_normal(
        information_size, coefficient=coefficient,
        additive_correction=additive_correction, z_alpha=za,
    )
    calculation_trace = {
        "kernel": "quadratic_normal",
        "information_size": information_size,
        "coefficient": coefficient,
        "additive_correction": additive_correction,
        "z_alpha": za,
        "z_beta_equivalent": zb,
    }
    calculation_trace.update(trace or {})
    return _power_result(
        engine_id, achieved_power=achieved, alpha=alpha, sidedness=sidedness,
        realized_design=realized_design, method=method,
        calculation_mode="inverse_of_existing_sample_size_method",
        inputs=inputs, warnings=warnings, trace=calculation_trace, extra=extra,
    )


def _power_one_001(
    *, planned_proportion: float, known_proportion: float, n: int,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    _binary_proportion("planned_proportion", planned_proportion)
    _binary_proportion("known_proportion", known_proportion)
    distance = abs(planned_proportion - known_proportion)
    if distance == 0:
        raise ValueError("planned_proportion must differ from known_proportion")
    design = _one_design(n)
    za = _z_alpha(alpha, sides)
    null_weight = sqrt(known_proportion * (1 - known_proportion))
    alternative_weight = sqrt(planned_proportion * (1 - planned_proportion))
    if alternative_weight == 0:
        raise ValueError("planned_proportion must have positive alternative variance")
    achieved, zb = _achieved_power_weighted_normal(
        n, scale=1.0, null_weight=null_weight,
        alternative_weight=alternative_weight, distance=distance, z_alpha=za,
    )
    return _power_result(
        "ONE-001", achieved_power=achieved, alpha=alpha, sidedness=sides,
        realized_design=design, method="equation 3.6 (two-sided) / 3.7 (one-sided)",
        calculation_mode="inverse_of_existing_sample_size_method",
        inputs={"planned_proportion": planned_proportion, "known_proportion": known_proportion, "n": n},
        trace={"kernel": "weighted_linear_normal", "z_alpha": za, "z_beta_equivalent": zb,
               "scale": 1.0, "null_weight": null_weight,
               "alternative_weight": alternative_weight, "distance": distance},
        extra={"null_value": known_proportion, "alternative_value": planned_proportion,
               "effect_measure": "risk_difference"},
    )


def _power_two_001(
    *, control_proportion: float, treatment_proportion: float,
    n_control: int, n_treatment: int, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    _binary_proportion("control_proportion", control_proportion)
    _binary_proportion("treatment_proportion", treatment_proportion)
    distance = abs(treatment_proportion - control_proportion)
    if distance == 0:
        raise ValueError("control and treatment proportions must differ")
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment / n_control
    pooled = (control_proportion + phi * treatment_proportion) / (1 + phi)
    null_weight = sqrt((1 + phi) * pooled * (1 - pooled))
    alternative_weight = sqrt(
        phi * control_proportion * (1 - control_proportion)
        + treatment_proportion * (1 - treatment_proportion)
    )
    za = _z_alpha(alpha, sides)
    scale = (1 + phi) / phi
    achieved, zb = _achieved_power_weighted_normal(
        design["total"], scale=scale, null_weight=null_weight,
        alternative_weight=alternative_weight, distance=distance, z_alpha=za,
    )
    return _power_result(
        "TWO-001", achieved_power=achieved, alpha=alpha, sidedness=sides,
        realized_design=design, method="equations 3.2 and 3.3",
        calculation_mode="inverse_of_existing_sample_size_method",
        inputs={"control_proportion": control_proportion,
                "treatment_proportion": treatment_proportion,
                "n_control": n_control, "n_treatment": n_treatment},
        trace={"kernel": "weighted_linear_normal", "z_alpha": za,
               "z_beta_equivalent": zb, "scale": scale,
               "null_weight": null_weight, "alternative_weight": alternative_weight,
               "distance": distance, "pooled_proportion": pooled},
        extra={"null_value": 0.0, "alternative_value": treatment_proportion-control_proportion,
               "effect_measure": "risk_difference", "allocation_ratio": phi},
    )


def _power_one_004(
    *, background_rate: float, additional_rate: float, n: int,
    alpha: float = 0.05, sides: int = 1, number_of_reactions: int = 1,
) -> dict[str, Any]:
    _rate_probability("background_rate", background_rate, allow_zero=True)
    additional = _positive_finite("additional_rate", additional_rate)
    if background_rate + additional >= 1:
        raise ValueError("background_rate + additional_rate must be less than 1")
    design = _one_design(n)
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    za = _z_alpha(adjusted_alpha, sides)
    null_weight = sqrt(background_rate)
    alternative_weight = sqrt(background_rate + additional)
    achieved, zb = _achieved_power_weighted_normal(
        n, scale=1.0, null_weight=null_weight,
        alternative_weight=alternative_weight, distance=additional, z_alpha=za,
    )
    return _power_result(
        "ONE-004", achieved_power=achieved, alpha=alpha, sidedness=sides,
        realized_design=design, method="equation 6.8 normal/Poisson rare-event approximation",
        calculation_mode="inverse_of_existing_sample_size_method",
        inputs={"background_rate": background_rate, "additional_rate": additional,
                "n": n, "number_of_reactions": number_of_reactions},
        trace={"kernel": "weighted_linear_normal", "z_alpha": za,
               "z_beta_equivalent": zb, "scale": 1.0,
               "null_weight": null_weight, "alternative_weight": alternative_weight,
               "distance": additional, "adjusted_alpha": adjusted_alpha},
        extra={"null_value": background_rate,
               "alternative_value": background_rate+additional,
               "effect_measure": "rate_difference", "adjusted_alpha": adjusted_alpha},
    )


def _power_two_015(
    *, control_rate: float, additional_rate: float,
    n_control: int, n_treatment: int, alpha: float = 0.05, sides: int = 1,
    number_of_reactions: int = 1,
) -> dict[str, Any]:
    _rate_probability("control_rate", control_rate)
    additional = _positive_finite("additional_rate", additional_rate)
    if control_rate + additional >= 1:
        raise ValueError("control_rate + additional_rate must be less than 1")
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    k = n_control / n_treatment
    ratio = Fraction(str(k)).limit_denominator(10_000)
    control_block, treatment_block = ratio.numerator, ratio.denominator
    if (
        n_control % control_block
        or n_treatment % treatment_block
        or n_control // control_block != n_treatment // treatment_block
    ):
        raise ValueError(
            "realized TWO-015 groups must form a complete control:treatment block "
            "under the existing Fraction(...).limit_denominator(10000) rule"
        )
    design["allocation_block"] = {
        "control": control_block, "treatment": treatment_block,
    }
    treatment_rate = control_rate + additional
    pooled = (k*control_rate + treatment_rate)/(k+1)
    null_weight = sqrt((k+1)*pooled*(1-pooled))
    alternative_weight = sqrt(
        control_rate*(1-control_rate) + k*treatment_rate*(1-treatment_rate)
    )
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    za = _z_alpha(adjusted_alpha, sides)
    scale = (k+1)/k
    achieved, zb = _achieved_power_weighted_normal(
        design["total"], scale=scale, null_weight=null_weight,
        alternative_weight=alternative_weight, distance=additional, z_alpha=za,
    )
    design["control_to_treatment_ratio"] = k
    design["allocation_ratio_definition"] = "control/treatment"
    return _power_result(
        "TWO-015", achieved_power=achieved, alpha=alpha, sidedness=sides,
        realized_design=design, method="equations 6.9 and 6.10",
        calculation_mode="inverse_of_existing_sample_size_method",
        inputs={"control_rate": control_rate, "additional_rate": additional,
                "n_control": n_control, "n_treatment": n_treatment,
                "number_of_reactions": number_of_reactions},
        warnings=[
            "TWO-015 uses control/treatment; the adapter normalized this direction without changing group labels"
        ],
        trace={"kernel": "weighted_linear_normal", "z_alpha": za,
               "z_beta_equivalent": zb, "scale": scale,
               "null_weight": null_weight, "alternative_weight": alternative_weight,
               "distance": additional, "pooled_rate": pooled,
               "adjusted_alpha": adjusted_alpha},
        extra={"null_value": 0.0, "alternative_value": additional,
               "effect_measure": "rate_difference", "allocation_ratio": k,
               "allocation_ratio_definition": "control/treatment",
               "adjusted_alpha": adjusted_alpha},
    )


def _power_two_016(
    *, control_rate: float, additional_rate: float,
    n_cases: int, n_controls: int, alpha: float = 0.05, sides: int = 1,
    number_of_reactions: int = 1,
) -> dict[str, Any]:
    _rate_probability("control_rate", control_rate)
    additional = _positive_finite("additional_rate", additional_rate)
    if control_rate + additional >= 1:
        raise ValueError("control_rate + additional_rate must be less than 1")
    design = _matched_design(n_cases, n_controls)
    m = design["controls_per_case"]
    omega = (control_rate+additional)/(1+additional)
    pooled = control_rate/(1+m)*(m+omega/control_rate)
    null_weight = sqrt((1+m)*pooled*(1-pooled))
    alternative_weight = sqrt(
        control_rate*(1-control_rate) + m*omega*(1-omega)
    )
    distance = abs(control_rate-omega)
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    za = _z_alpha(adjusted_alpha, sides)
    achieved, zb = _achieved_power_weighted_normal(
        design["matched_units"], scale=1/m, null_weight=null_weight,
        alternative_weight=alternative_weight, distance=distance, z_alpha=za,
    )
    return _power_result(
        "TWO-016", achieved_power=achieved, alpha=alpha, sidedness=sides,
        realized_design=design, method="equations 6.11 and 6.12",
        calculation_mode="inverse_of_existing_sample_size_method",
        inputs={"control_rate": control_rate, "additional_rate": additional,
                "n_cases": n_cases, "n_controls": n_controls,
                "number_of_reactions": number_of_reactions},
        trace={"kernel": "weighted_linear_normal", "z_alpha": za,
               "z_beta_equivalent": zb, "scale": 1/m,
               "null_weight": null_weight, "alternative_weight": alternative_weight,
               "distance": distance, "omega": omega, "pooled_rate": pooled,
               "adjusted_alpha": adjusted_alpha},
        extra={"null_value": 0.0, "alternative_value": additional,
               "effect_measure": "matched_rate_difference",
               "allocation_ratio": m, "allocation_ratio_definition": "controls/case",
               "adjusted_alpha": adjusted_alpha},
    )


def _power_two_023(
    *, discordant_odds_ratio: float, discordant_fraction: float,
    n_pairs: int, alpha: float = 0.05, sides: int = 2,
    subjects_per_pair: int = 1, even_sequence: bool = False,
) -> dict[str, Any]:
    psi = _paired_discordant_odds(discordant_odds_ratio)
    fraction = _paired_probability("discordant_fraction", discordant_fraction, strict=False)
    if fraction == 0:
        raise ValueError("discordant_fraction must be greater than 0")
    design = _pair_design(n_pairs, even_sequence=even_sequence,
                          subjects_per_pair=subjects_per_pair)
    radical = (psi+1)**2 - (psi-1)**2*fraction
    za = _z_alpha(alpha, sides)
    achieved, zb = _achieved_power_weighted_normal(
        n_pairs, scale=1.0, null_weight=psi+1,
        alternative_weight=sqrt(radical),
        distance=abs(psi-1)*sqrt(fraction), z_alpha=za,
    )
    return _power_result(
        "TWO-023", achieved_power=achieved, alpha=alpha, sidedness=sides,
        realized_design=design, method="equation 8.1 Connett-Smith-McHugh normal approximation",
        calculation_mode="inverse_of_existing_sample_size_method",
        inputs={"discordant_odds_ratio": psi, "discordant_fraction": fraction,
                "n_pairs": n_pairs, "subjects_per_pair": subjects_per_pair,
                "even_sequence": even_sequence},
        trace={"kernel": "weighted_linear_normal", "z_alpha": za,
               "z_beta_equivalent": zb, "scale": 1.0,
               "null_weight": psi+1, "alternative_weight": sqrt(radical),
               "distance": abs(psi-1)*sqrt(fraction)},
        extra={"null_value": 1.0, "alternative_value": psi,
               "effect_measure": "discordant_odds_ratio"},
    )


def _power_margin_005(
    *, standard_proportion: float, test_proportion: float, positive_margin: float,
    n_pairs: int, joint_success_probability: float | None = None,
    alpha: float = 0.025, favorable_direction: str = "larger",
    subjects_per_pair: int = 1, even_sequence: bool = False,
) -> dict[str, Any]:
    ps = _margin_probability("standard_proportion", standard_proportion)
    pt = _margin_probability("test_proportion", test_proportion)
    margin = _margin_positive("positive_margin", positive_margin)
    direction = _margin_direction(favorable_direction)
    source_ps, source_pt = (ps, pt) if direction == "larger" else (pt, ps)
    pi11, pi11_source = _margin_paired_joint(
        source_ps, source_pt, margin, joint_success_probability
    )
    delta = source_ps-source_pt
    a = source_ps-pi11
    b = 2*a-delta-margin
    c = a-delta
    d = a-delta-margin
    if min(a, b, c, d) <= 0:
        raise ValueError("paired joint probability and margin make equation 11.7 undefined")
    design = _pair_design(n_pairs, even_sequence=even_sequence,
                          subjects_per_pair=subjects_per_pair)
    za = _z_alpha(alpha, 1)
    null_weight = b*sqrt(c)
    alternative_weight = (2*a-delta)*sqrt(d)
    achieved, zb = _achieved_power_weighted_normal(
        n_pairs, scale=1/(a*b), null_weight=null_weight,
        alternative_weight=alternative_weight, distance=margin, z_alpha=za,
    )
    boundary = -margin if direction == "larger" else margin
    return _power_result(
        "MARGIN-005", achieved_power=achieved, alpha=alpha, sidedness=1,
        realized_design=design, method="equations 11.7 and 11.8 paired risk-difference noninferiority",
        calculation_mode="inverse_of_existing_sample_size_method",
        inputs={"standard_proportion": ps, "test_proportion": pt,
                "positive_margin": margin, "joint_success_probability": pi11,
                "joint_success_source": pi11_source, "favorable_direction": direction,
                "n_pairs": n_pairs, "subjects_per_pair": subjects_per_pair,
                "even_sequence": even_sequence},
        trace={"kernel": "weighted_linear_normal", "z_alpha": za,
               "z_beta_equivalent": zb, "scale": 1/(a*b),
               "null_weight": null_weight, "alternative_weight": alternative_weight,
               "distance": margin, "equation_11_7_a": a, "equation_11_7_b": b,
               "equation_11_7_c": c, "equation_11_7_d": d},
        extra={"null_value": boundary, "alternative_value": pt-ps,
               "effect_measure": "paired_risk_difference_test_minus_standard",
               "margin": margin, "favorable_direction": direction},
    )
def _power_one_002(
    *, known_mean: float, planned_mean: float, planned_sd: float, n: int,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    sd = _positive_finite("planned_sd", planned_sd)
    if not isfinite(known_mean) or not isfinite(planned_mean):
        raise ValueError("means must be finite")
    if planned_mean == known_mean:
        raise ValueError("planned_mean must differ from known_mean")
    effect = abs(planned_mean-known_mean)/sd
    design = _one_design(n)
    za = _z_alpha(alpha, sides)
    return _quadratic_power_result(
        "ONE-002", information_size=n, coefficient=1/effect**2,
        additive_correction=za**2/2, alpha=alpha, sidedness=sides,
        realized_design=design, method="equation 5.11 Guenther normal approximation",
        inputs={"known_mean": known_mean, "planned_mean": planned_mean,
                "planned_sd": sd, "n": n},
        extra={"null_value": known_mean, "alternative_value": planned_mean,
               "effect_measure": "standardized_mean_difference"},
    )


def _power_two_002(
    *, control_proportion: float, odds_ratio: float, n_control: int,
    n_treatment: int, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    _binary_proportion("control_proportion", control_proportion)
    if control_proportion in (0.0, 1.0):
        raise ValueError("control_proportion must be strictly between 0 and 1")
    odds = _positive_finite("odds_ratio", odds_ratio)
    if odds == 1:
        raise ValueError("odds_ratio must differ from 1")
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    treatment = odds*control_proportion/(1-control_proportion+odds*control_proportion)
    pooled = (control_proportion+phi*treatment)/(1+phi)
    coefficient = (1+phi)**2/(phi*log(odds)**2*pooled*(1-pooled))
    return _quadratic_power_result(
        "TWO-002", information_size=design["total"], coefficient=coefficient,
        additive_correction=0.0, alpha=alpha, sidedness=sides,
        realized_design=design, method="equations 3.1, 3.3, and 3.4 log-odds normal approximation",
        inputs={"control_proportion": control_proportion, "odds_ratio": odds,
                "n_control": n_control, "n_treatment": n_treatment},
        trace={"pooled_proportion": pooled, "derived_treatment_proportion": treatment},
        extra={"null_value": 1.0, "alternative_value": odds,
               "effect_measure": "odds_ratio", "allocation_ratio": phi},
    )


def _power_two_004(
    *, control_proportions: list[float], odds_ratio: float,
    n_control: int, n_treatment: int, alpha: float = 0.05, sides: int = 2,
    gamma_from_control_only: bool = False,
    gamma_proportions: list[float] | None = None,
) -> dict[str, Any]:
    control = _ordinal_probabilities("control_proportions", control_proportions)
    odds = _ordinal_odds_ratio(odds_ratio)
    treatment = _proportional_treatment(control, odds)
    if gamma_proportions is not None:
        gamma_values = _ordinal_probabilities("gamma_proportions", gamma_proportions)
        if len(gamma_values) != len(control):
            raise ValueError("gamma_proportions must have the same categories as control_proportions")
    elif gamma_from_control_only:
        gamma_values = control
    else:
        gamma_values = [(left+right)/2 for left, right in zip(control, treatment)]
    denominator = 1-sum(value**3 for value in gamma_values)
    if denominator <= 0:
        raise ValueError("category probabilities do not produce a finite Gamma")
    gamma = 3/denominator
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    coefficient = gamma*(1+phi)**2/(phi*log(odds)**2)
    return _quadratic_power_result(
        "TWO-004", information_size=design["total"], coefficient=coefficient,
        additive_correction=0.0, alpha=alpha, sidedness=sides,
        realized_design=design, method="equations 4.2, 4.3 and 4.4 proportional-odds normal approximation",
        inputs={"control_proportions": control, "odds_ratio": odds,
                "gamma_from_control_only": gamma_from_control_only,
                "gamma_proportions": gamma_proportions,
                "n_control": n_control, "n_treatment": n_treatment},
        trace={"gamma": gamma, "gamma_proportions": gamma_values,
               "derived_treatment_proportions": treatment},
        extra={"null_value": 1.0, "alternative_value": odds,
               "effect_measure": "proportional_odds_ratio", "allocation_ratio": phi},
    )


def _power_two_005(
    *, category_count: int, odds_ratio: float, n_control: int,
    n_treatment: int, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    if isinstance(category_count, bool) or not isinstance(category_count, int) or category_count < 2:
        raise ValueError("category_count must be an integer of at least 2")
    odds = _ordinal_odds_ratio(odds_ratio)
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    gamma = 3/(1-1/category_count**2)
    coefficient = gamma*(1+phi)**2/(phi*log(odds)**2)
    return _quadratic_power_result(
        "TWO-005", information_size=design["total"], coefficient=coefficient,
        additive_correction=0.0, alpha=alpha, sidedness=sides,
        realized_design=design, method="equations 4.3 and 4.6 equal-category approximation",
        inputs={"category_count": category_count, "odds_ratio": odds,
                "n_control": n_control, "n_treatment": n_treatment},
        trace={"gamma": gamma},
        extra={"null_value": 1.0, "alternative_value": odds,
               "effect_measure": "ordinal_odds_ratio", "allocation_ratio": phi},
    )


def _power_two_006(
    *, category_count: int, odds_ratio: float, n_control: int,
    n_treatment: int, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    if isinstance(category_count, bool) or not isinstance(category_count, int) or category_count <= 5:
        raise ValueError("category_count must be an integer greater than 5")
    odds = _ordinal_odds_ratio(odds_ratio)
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    coefficient = 3*(1+phi)**2/(phi*log(odds)**2)
    return _quadratic_power_result(
        "TWO-006", information_size=design["total"], coefficient=coefficient,
        additive_correction=0.0, alpha=alpha, sidedness=sides,
        realized_design=design, method="equation 4.7 many-category approximation",
        inputs={"category_count": category_count, "odds_ratio": odds,
                "n_control": n_control, "n_treatment": n_treatment},
        trace={"gamma_approximation": 3.0},
        extra={"null_value": 1.0, "alternative_value": odds,
               "effect_measure": "ordinal_odds_ratio", "allocation_ratio": phi},
    )


def _power_two_007(
    *, standard_proportions: list[float], treatment_proportions: list[float],
    n_standard: int, n_treatment: int, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    standard = _ordinal_probabilities("standard_proportions", standard_proportions)
    treatment = _ordinal_probabilities("treatment_proportions", treatment_proportions)
    if len(standard) != len(treatment):
        raise ValueError("standard_proportions and treatment_proportions must have equal length")
    design = _allocation_design("standard", n_standard, "treatment", n_treatment)
    phi = n_treatment/n_standard
    variance = 1-sum((phi*left+right)**3 for left, right in zip(standard, treatment))/(1+phi)**3
    superiority = 0.0
    treatment_below = 0.0
    for left, right in zip(standard, treatment):
        superiority += left*treatment_below
        treatment_below += right
    superiority += 0.5*sum(left*right for left, right in zip(standard, treatment))
    effect = superiority-0.5
    if isclose(effect, 0.0, rel_tol=0.0, abs_tol=1e-15):
        raise ValueError("the Mann-Whitney superiority probability is 0.5")
    coefficient = (1+phi)**2*variance/(12*phi*effect**2)
    return _quadratic_power_result(
        "TWO-007", information_size=design["total"], coefficient=coefficient,
        additive_correction=0.0, alpha=alpha, sidedness=sides,
        realized_design=design, method="equation 4.8 tie-adjusted Mann-Whitney normal approximation",
        inputs={"standard_proportions": standard, "treatment_proportions": treatment,
                "n_standard": n_standard, "n_treatment": n_treatment},
        trace={"variance_term": variance, "superiority_probability": superiority},
        extra={"null_value": 0.5, "alternative_value": superiority,
               "effect_measure": "mann_whitney_superiority_probability",
               "allocation_ratio": phi},
    )


def _power_two_009(
    *, standardized_effect: float, n_control: int, n_treatment: int,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    effect = _continuous_effect(standardized_effect)
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    za = _z_alpha(alpha, sides)
    return _quadratic_power_result(
        "TWO-009", information_size=design["total"],
        coefficient=(1+phi)**2/(phi*effect**2), additive_correction=za**2/2,
        alpha=alpha, sidedness=sides, realized_design=design,
        method="equation 5.4 Guenther normal approximation",
        inputs={"standardized_effect": effect, "n_control": n_control,
                "n_treatment": n_treatment},
        extra={"null_value": 0.0, "alternative_value": effect,
               "effect_measure": "standardized_mean_difference", "allocation_ratio": phi},
    )


def _power_two_010(
    *, planned_mean_difference: float, control_sd: float, treatment_sd: float,
    n_control: int, n_treatment: int, variance_ratio: float | None = None,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    csd = _positive_finite("control_sd", control_sd)
    tsd = _positive_finite("treatment_sd", treatment_sd)
    if not isfinite(planned_mean_difference) or planned_mean_difference == 0:
        raise ValueError("planned_mean_difference must be finite and nonzero")
    tau = (tsd/csd)**2
    if variance_ratio is not None:
        supplied = _positive_finite("variance_ratio", variance_ratio)
        if abs(supplied-tau) > max(1e-12, tau*1e-10):
            raise ValueError("variance_ratio must equal treatment variance / control variance")
    effect = abs(planned_mean_difference)/csd
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    za = _z_alpha(alpha, sides)
    coefficient = (1+phi)*(tau+phi)/(phi*effect**2)
    correction = (1+phi)*(tau**2+phi**3)*za**2/(2*phi*(tau+phi)**2)
    return _quadratic_power_result(
        "TWO-010", information_size=design["total"], coefficient=coefficient,
        additive_correction=correction, alpha=alpha, sidedness=sides,
        realized_design=design, method="equation 5.6 Satterthwaite approximation",
        inputs={"planned_mean_difference": planned_mean_difference,
                "control_sd": csd, "treatment_sd": tsd, "variance_ratio": tau,
                "n_control": n_control, "n_treatment": n_treatment},
        trace={"standardized_effect": effect, "variance_ratio": tau},
        extra={"null_value": 0.0, "alternative_value": planned_mean_difference,
               "effect_measure": "mean_difference", "allocation_ratio": phi},
    )


def _power_two_011(
    *, standardized_effect: float, efficiency_factor: float,
    n_control: int, n_treatment: int, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    effect = _continuous_effect(standardized_effect)
    efficiency = _positive_finite("efficiency_factor", efficiency_factor)
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    za = _z_alpha(alpha, sides)
    coefficient = efficiency*(1+phi)**2/(phi*effect**2)
    return _quadratic_power_result(
        "TWO-011", information_size=design["total"], coefficient=coefficient,
        additive_correction=za**2/2, alpha=alpha, sidedness=sides,
        realized_design=design, method="equations 5.7 and 5.8 WMW efficiency approximation",
        inputs={"standardized_effect": effect, "efficiency_factor": efficiency,
                "n_control": n_control, "n_treatment": n_treatment},
        extra={"null_value": 0.0, "alternative_value": effect,
               "effect_measure": "standardized_location_effect", "allocation_ratio": phi},
    )


def _power_two_012(
    *, n_control: int, n_treatment: int,
    superiority_probability: float | None = None,
    standardized_effect: float | None = None,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    if (superiority_probability is None) == (standardized_effect is None):
        raise ValueError("provide exactly one of superiority_probability or standardized_effect")
    if standardized_effect is not None:
        if not isfinite(standardized_effect) or standardized_effect == 0:
            raise ValueError("standardized_effect must be finite and nonzero")
        probability = superiority_probability_from_effect(standardized_effect)
        input_path = "equation 5.10 from standardized_effect"
    else:
        probability = float(superiority_probability)
        input_path = "direct superiority_probability"
    if not isfinite(probability) or not 0 < probability < 1 or probability == 0.5:
        raise ValueError("superiority_probability must be in (0, 1) and differ from 0.5")
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    coefficient = (1+phi)**2/(12*phi*(probability-0.5)**2)
    return _quadratic_power_result(
        "TWO-012", information_size=design["total"], coefficient=coefficient,
        additive_correction=0.0, alpha=alpha, sidedness=sides,
        realized_design=design, method="equations 5.9 and 5.10 WMW superiority approximation",
        inputs={"superiority_probability": probability,
                "standardized_effect": standardized_effect,
                "probability_input_path": input_path,
                "n_control": n_control, "n_treatment": n_treatment},
        extra={"null_value": 0.5, "alternative_value": probability,
               "effect_measure": "superiority_probability", "allocation_ratio": phi},
    )


def _power_two_013(
    *, standard_rate: float, n_standard: int, n_treatment: int,
    treatment_rate: float | None = None, rate_ratio: float | None = None,
    exposure_per_subject: float = 1.0, alpha: float = 0.05, sides: int = 2,
    number_of_reactions: int = 1,
) -> dict[str, Any]:
    standard = _positive_finite("standard_rate", standard_rate)
    if (treatment_rate is None) == (rate_ratio is None):
        raise ValueError("provide exactly one of treatment_rate or rate_ratio")
    if rate_ratio is not None:
        ratio = _positive_finite("rate_ratio", rate_ratio)
        if ratio == 1:
            raise ValueError("rate_ratio must differ from 1")
        treatment = standard*ratio
        input_path = "equation 6.3 rate-ratio input"
    else:
        treatment = _positive_finite("treatment_rate", float(treatment_rate))
        if treatment == standard:
            raise ValueError("treatment_rate must differ from standard_rate")
        ratio = treatment/standard
        input_path = "equation 6.2 direct-rate input"
    exposure = _positive_finite("exposure_per_subject", exposure_per_subject)
    design = _allocation_design("standard", n_standard, "treatment", n_treatment)
    phi = n_treatment/n_standard
    coefficient = (1+phi)/phi*(treatment+phi*standard)/(treatment-standard)**2/exposure
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    return _quadratic_power_result(
        "TWO-013", information_size=design["total"], coefficient=coefficient,
        additive_correction=0.0, alpha=adjusted_alpha, sidedness=sides,
        realized_design=design, method="equations 6.2 and 6.3 Poisson-rate normal approximation",
        inputs={"standard_rate": standard, "treatment_rate": treatment,
                "rate_ratio": ratio, "input_path": input_path,
                "exposure_per_subject": exposure, "n_standard": n_standard,
                "n_treatment": n_treatment, "number_of_reactions": number_of_reactions},
        trace={"nominal_alpha": alpha, "adjusted_alpha": adjusted_alpha},
        extra={"alpha": alpha, "adjusted_alpha": adjusted_alpha,
               "null_value": 1.0, "alternative_value": ratio,
               "effect_measure": "rate_ratio", "allocation_ratio": phi},
    )


def _power_two_014(
    *, standard_rate: float, treatment_rate: float, overdispersion: float,
    mean_exposure: float, n_standard: int, n_treatment: int,
    alpha: float = 0.05, sides: int = 2, number_of_reactions: int = 1,
) -> dict[str, Any]:
    standard = _positive_finite("standard_rate", standard_rate)
    treatment = _positive_finite("treatment_rate", treatment_rate)
    if treatment == standard:
        raise ValueError("treatment_rate must differ from standard_rate")
    if not isfinite(overdispersion) or overdispersion < 0:
        raise ValueError("overdispersion must be finite and nonnegative")
    exposure = _positive_finite("mean_exposure", mean_exposure)
    design = _allocation_design("standard", n_standard, "treatment", n_treatment)
    phi = n_treatment/n_standard
    variance = (1/exposure)*(1/standard+1/(phi*treatment))+overdispersion*(1+phi)/phi
    coefficient = (1+phi)*variance/log(treatment/standard)**2
    adjusted_alpha = bonferroni_alpha(alpha, number_of_reactions)
    return _quadratic_power_result(
        "TWO-014", information_size=design["total"], coefficient=coefficient,
        additive_correction=0.0, alpha=adjusted_alpha, sidedness=sides,
        realized_design=design, method="equations 6.4 and 6.5 negative-binomial rate approximation",
        inputs={"standard_rate": standard, "treatment_rate": treatment,
                "overdispersion": overdispersion, "mean_exposure": exposure,
                "n_standard": n_standard, "n_treatment": n_treatment,
                "number_of_reactions": number_of_reactions},
        trace={"nominal_alpha": alpha, "adjusted_alpha": adjusted_alpha,
               "variance_factor": variance},
        extra={"alpha": alpha, "adjusted_alpha": adjusted_alpha,
               "null_value": 1.0, "alternative_value": treatment/standard,
               "effect_measure": "rate_ratio", "allocation_ratio": phi},
    )


def _power_two_026(
    *, n_pairs: int, standardized_effect: float | None = None,
    difference_scores: list[float] | None = None,
    conditional_probabilities: list[float] | None = None,
    alpha: float = 0.05, sides: int = 2, subjects_per_pair: int = 1,
    even_sequence: bool = False,
) -> dict[str, Any]:
    if standardized_effect is not None:
        if difference_scores is not None or conditional_probabilities is not None:
            raise ValueError("provide standardized_effect or score probabilities, not both")
        effect = abs(_positive_finite("standardized_effect", standardized_effect))
        eta = sigma = None
    else:
        if difference_scores is None or conditional_probabilities is None:
            raise ValueError("difference_scores and conditional_probabilities are required together")
        effect, eta, sigma = _paired_effect_from_scores(difference_scores, conditional_probabilities)
    design = _pair_design(n_pairs, even_sequence=even_sequence,
                          subjects_per_pair=subjects_per_pair)
    za = _z_alpha(alpha, sides)
    return _quadratic_power_result(
        "TWO-026", information_size=n_pairs, coefficient=2/effect**2,
        additive_correction=za**2/2, alpha=alpha, sidedness=sides,
        realized_design=design, method="equations 8.6--8.9 paired ordinal signed-rank approximation",
        inputs={"standardized_effect": effect, "difference_scores": difference_scores,
                "conditional_probabilities": conditional_probabilities,
                "n_pairs": n_pairs, "subjects_per_pair": subjects_per_pair,
                "even_sequence": even_sequence},
        trace={"eta_plan": eta, "sigma_discordant": sigma},
        extra={"null_value": 0.0, "alternative_value": effect,
               "effect_measure": "paired_standardized_effect"},
    )


def _power_two_029(
    *, standardized_effect: float, n_pairs: int, alpha: float = 0.05,
    sides: int = 2, subjects_per_pair: int = 1, even_sequence: bool = False,
) -> dict[str, Any]:
    effect = abs(_positive_finite("standardized_effect", standardized_effect))
    design = _pair_design(n_pairs, even_sequence=even_sequence,
                          subjects_per_pair=subjects_per_pair)
    za = _z_alpha(alpha, sides)
    return _quadratic_power_result(
        "TWO-029", information_size=n_pairs, coefficient=2/effect**2,
        additive_correction=za**2/2, alpha=alpha, sidedness=sides,
        realized_design=design, method="equation 8.12 paired continuous normal/Guenther approximation",
        inputs={"standardized_effect": effect, "n_pairs": n_pairs,
                "subjects_per_pair": subjects_per_pair, "even_sequence": even_sequence},
        extra={"null_value": 0.0, "alternative_value": effect,
               "effect_measure": "paired_standardized_mean_difference"},
    )


def _power_two_031(
    *, planned_mean_difference: float, planned_sd: float,
    pre_measurements: int, post_measurements: int, correlation: float,
    n_control: int, n_treatment: int, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    if not isfinite(planned_mean_difference) or planned_mean_difference == 0:
        raise ValueError("planned_mean_difference must be finite and nonzero")
    sd = _positive_finite("planned_sd", planned_sd)
    effect = abs(planned_mean_difference)/sd
    design_effect = post_mean_design_effect(
        pre_measurements=pre_measurements, post_measurements=post_measurements,
        correlation=correlation,
    )
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    za = _z_alpha(alpha, sides)
    return _quadratic_power_result(
        "TWO-031", information_size=design["total"]/design_effect,
        coefficient=(1+phi)**2/(phi*effect**2), additive_correction=za**2/2,
        alpha=alpha, sidedness=sides, realized_design=design,
        method="equations 10.7--10.9 repeated post-mean design effect over TWO-009",
        inputs={"planned_mean_difference": planned_mean_difference, "planned_sd": sd,
                "pre_measurements": pre_measurements, "post_measurements": post_measurements,
                "correlation": correlation, "n_control": n_control,
                "n_treatment": n_treatment},
        trace={"design_effect": design_effect,
               "realized_effective_total": design["total"]/design_effect},
        extra={"null_value": 0.0, "alternative_value": planned_mean_difference,
               "effect_measure": "repeated_post_mean_difference",
               "allocation_ratio": phi},
    )


def _power_two_032(
    *, planned_slope_difference: float, planned_intercept_sd: float,
    measurement_times: list[float], correlation: float,
    n_control: int, n_treatment: int, alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    if not isfinite(planned_slope_difference) or planned_slope_difference == 0:
        raise ValueError("planned_slope_difference must be finite and nonzero")
    sd = _positive_finite("planned_intercept_sd", planned_intercept_sd)
    times = [float(value) for value in measurement_times]
    if len(times) < 2 or any(not isfinite(value) for value in times) or len(set(times)) != len(times):
        raise ValueError("measurement_times must contain at least two distinct finite times")
    rho = _longitudinal_correlation(correlation, len(times))
    mean_time = sum(times)/len(times)
    time_sum_squares = sum((value-mean_time)**2 for value in times)
    if time_sum_squares <= 0:
        raise ValueError("measurement_times must have positive dispersion")
    design_effect = (1-rho)/time_sum_squares
    effect = abs(planned_slope_difference)/sd
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    za = _z_alpha(alpha, sides)
    return _quadratic_power_result(
        "TWO-032", information_size=design["total"]/design_effect,
        coefficient=(1+phi)**2/(phi*effect**2), additive_correction=za**2/2,
        alpha=alpha, sidedness=sides, realized_design=design,
        method="equations 10.7, 10.10 and 10.11 repeated slope design effect over TWO-009",
        inputs={"planned_slope_difference": planned_slope_difference,
                "planned_intercept_sd": sd, "measurement_times": times,
                "correlation": rho, "n_control": n_control,
                "n_treatment": n_treatment},
        trace={"design_effect": design_effect, "mean_measurement_time": mean_time,
               "time_sum_squares": time_sum_squares,
               "realized_effective_total": design["total"]/design_effect},
        extra={"null_value": 0.0, "alternative_value": planned_slope_difference,
               "effect_measure": "repeated_slope_difference", "allocation_ratio": phi},
    )


def _power_two_033(
    *, planned_contrast_difference: float, planned_sd: float, weights: list[float],
    correlation_structure: str, n_control: int, n_treatment: int,
    correlation: float | None = None,
    measurement_times: list[float] | None = None,
    covariance_matrix: list[list[float]] | None = None,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    if not isfinite(planned_contrast_difference) or planned_contrast_difference == 0:
        raise ValueError("planned_contrast_difference must be finite and nonzero")
    sd = _positive_finite("planned_sd", planned_sd)
    weight_values = [float(value) for value in weights]
    if len(weight_values) < 2 or any(not isfinite(value) for value in weight_values) or all(value == 0 for value in weight_values):
        raise ValueError("weights must contain at least two finite values and not be all zero")
    times = None if measurement_times is None else [float(value) for value in measurement_times]
    variance, matrix = _longitudinal_covariance(
        weight_values, sd, correlation_structure, correlation, times, covariance_matrix,
    )
    design_effect = variance/sd**2
    effect = abs(planned_contrast_difference)/sd
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    phi = n_treatment/n_control
    za = _z_alpha(alpha, sides)
    warnings = []
    if not isclose(sum(weight_values), 0.0, rel_tol=0.0, abs_tol=1e-10):
        warnings.append("weights do not sum to zero; this is a weighted estimand rather than a contrast")
    return _quadratic_power_result(
        "TWO-033", information_size=design["total"]/design_effect,
        coefficient=(1+phi)**2/(phi*effect**2), additive_correction=za**2/2,
        alpha=alpha, sidedness=sides, realized_design=design,
        method="equations 10.7 and 10.12--10.14 weighted-contrast design effect over TWO-009",
        inputs={"planned_contrast_difference": planned_contrast_difference,
                "planned_sd": sd, "weights": weight_values,
                "correlation_structure": correlation_structure,
                "correlation": correlation, "measurement_times": times,
                "covariance_matrix": matrix, "n_control": n_control,
                "n_treatment": n_treatment},
        trace={"design_effect": design_effect, "contrast_variance": variance,
               "realized_effective_total": design["total"]/design_effect},
        warnings=warnings,
        extra={"null_value": 0.0, "alternative_value": planned_contrast_difference,
               "effect_measure": "repeated_weighted_contrast_difference",
               "allocation_ratio": phi},
    )


def _power_margin_001(
    *, planned_standard: float, planned_test: float, standard_deviation: float,
    positive_margin: float, n_standard: int, n_test: int,
    alpha: float = 0.025, favorable_direction: str = "larger",
) -> dict[str, Any]:
    sd = _margin_positive("standard_deviation", standard_deviation)
    margin = _margin_positive("positive_margin", positive_margin)
    direction = _margin_direction(favorable_direction)
    planned = float(planned_test)-float(planned_standard)
    boundary, distance = _margin_ni_boundary(planned, margin, direction)
    design = _allocation_design("standard", n_standard, "test", n_test)
    phi = n_test/n_standard
    coefficient = (1+phi)**2*sd**2/(phi*distance**2)
    return _quadratic_power_result(
        "MARGIN-001", information_size=design["total"], coefficient=coefficient,
        additive_correction=0.0, alpha=alpha, sidedness=1,
        realized_design=design, method="equation 11.3 independent mean noninferiority",
        inputs={"planned_standard": planned_standard, "planned_test": planned_test,
                "standard_deviation": sd, "positive_margin": margin,
                "favorable_direction": direction, "n_standard": n_standard,
                "n_test": n_test},
        trace={"signed_null_boundary": boundary, "distance_from_boundary": distance},
        extra={"null_value": boundary, "alternative_value": planned,
               "effect_measure": "mean_difference_test_minus_standard",
               "margin": margin, "favorable_direction": direction,
               "allocation_ratio": phi},
    )


def _power_margin_002(
    *, planned_standard: float, planned_test: float,
    paired_standard_deviation: float, positive_margin: float, n_pairs: int,
    alpha: float = 0.025, favorable_direction: str = "larger",
    subjects_per_pair: int = 1, even_sequence: bool = False,
) -> dict[str, Any]:
    sd = _margin_positive("paired_standard_deviation", paired_standard_deviation)
    margin = _margin_positive("positive_margin", positive_margin)
    direction = _margin_direction(favorable_direction)
    planned = float(planned_test)-float(planned_standard)
    boundary, distance = _margin_ni_boundary(planned, margin, direction)
    design = _pair_design(n_pairs, even_sequence=even_sequence,
                          subjects_per_pair=subjects_per_pair)
    return _quadratic_power_result(
        "MARGIN-002", information_size=n_pairs, coefficient=2*sd**2/distance**2,
        additive_correction=0.0, alpha=alpha, sidedness=1,
        realized_design=design, method="equation 11.4 paired mean noninferiority",
        inputs={"planned_standard": planned_standard, "planned_test": planned_test,
                "paired_standard_deviation": sd, "positive_margin": margin,
                "favorable_direction": direction, "n_pairs": n_pairs,
                "subjects_per_pair": subjects_per_pair, "even_sequence": even_sequence},
        trace={"signed_null_boundary": boundary, "distance_from_boundary": distance},
        extra={"null_value": boundary, "alternative_value": planned,
               "effect_measure": "paired_mean_difference_test_minus_standard",
               "margin": margin, "favorable_direction": direction},
    )


def _power_margin_006(
    *, planned_hazard_ratio: float, positive_margin: float,
    standard_hazard: float, accrual_time: float, followup_time: float,
    n_standard: int, n_test: int, censoring_hazard: float = 0.0,
    alpha: float = 0.025, favorable_direction: str = "smaller",
) -> dict[str, Any]:
    hr = _margin_positive("planned_hazard_ratio", planned_hazard_ratio)
    margin = _margin_positive("positive_margin", positive_margin)
    direction = _margin_direction(favorable_direction)
    boundary = margin if direction == "smaller" else 1/margin
    distance = boundary-hr if direction == "smaller" else hr-boundary
    if distance <= 0:
        raise ValueError("planned hazard ratio must lie on the favorable side of the boundary")
    hazard = _margin_positive("standard_hazard", standard_hazard)
    accrual = _margin_positive("accrual_time", accrual_time)
    followup = _margin_positive("followup_time", followup_time)
    censoring = float(censoring_hazard)
    if not isfinite(censoring) or censoring < 0:
        raise ValueError("censoring_hazard must be finite and nonnegative")
    design = _allocation_design("standard", n_standard, "test", n_test)
    phi = n_test/n_standard
    coefficient, audit = _margin_hr_component(
        hr, boundary, hazard, censoring, accrual, followup, phi, 0.0, 1.0,
    )
    return _quadratic_power_result(
        "MARGIN-006", information_size=design["total"], coefficient=coefficient,
        additive_correction=0.0, alpha=alpha, sidedness=1,
        realized_design=design, method="equations 11.9--11.11 hazard-ratio noninferiority",
        inputs={"planned_hazard_ratio": hr, "positive_margin": margin,
                "standard_hazard": hazard, "censoring_hazard": censoring,
                "accrual_time": accrual, "followup_time": followup,
                "favorable_direction": direction, "n_standard": n_standard,
                "n_test": n_test},
        trace={"signed_null_boundary": boundary, **audit},
        extra={"null_value": boundary, "alternative_value": hr,
               "effect_measure": "hazard_ratio_test_over_standard",
               "margin": margin, "favorable_direction": direction,
               "allocation_ratio": phi},
    )


def _power_two_008(
    *, standardized_effect: float, n_control: int, n_treatment: int,
    alpha: float = 0.05, sides: int = 2,
) -> dict[str, Any]:
    effect = _continuous_effect(standardized_effect)
    design = _allocation_design("control", n_control, "treatment", n_treatment)
    if n_control < 2 or n_treatment < 2:
        raise ValueError("TWO-008 requires at least two observations per group")
    # Reuse the exact fixed-total evaluator used by the sample-size engine.
    critical_values(alpha, 0.5, sides)
    phi = n_treatment/n_control
    total = design["total"]
    achieved = _achieved_power_existing_noncentral_t(
        _nct_power, total, effect, phi, alpha, sides
    )
    degrees = total-2
    noncentrality = effect*sqrt(phi*total)/(1+phi)
    return _power_result(
        "TWO-008", achieved_power=achieved, alpha=alpha, sidedness=sides,
        realized_design=design, method="equations 5.2 and 5.3 existing noncentral-t evaluation",
        calculation_mode="existing_noncentral_t_evaluation",
        inputs={"standardized_effect": effect, "n_control": n_control,
                "n_treatment": n_treatment},
        trace={"kernel": "existing_noncentral_t", "degrees_of_freedom": degrees,
               "noncentrality_parameter": noncentrality},
        extra={"null_value": 0.0, "alternative_value": effect,
               "effect_measure": "standardized_mean_difference",
               "allocation_ratio": phi, "degrees_of_freedom": degrees,
               "noncentrality_parameter": noncentrality},
    )


def _power_two_030(
    *, standardized_effect: float, n_pairs: int, alpha: float = 0.05,
    sides: int = 2, subjects_per_pair: int = 1, even_sequence: bool = False,
) -> dict[str, Any]:
    effect = abs(_positive_finite("standardized_effect", standardized_effect))
    design = _pair_design(n_pairs, even_sequence=even_sequence,
                          subjects_per_pair=subjects_per_pair)
    if n_pairs < 2:
        raise ValueError("TWO-030 requires at least two pairs")
    critical_values(alpha, 0.5, sides)
    achieved = _achieved_power_existing_noncentral_t(
        _paired_t_power, n_pairs, effect, alpha, sides
    )
    degrees = n_pairs-1
    noncentrality = effect*sqrt(n_pairs/2)
    return _power_result(
        "TWO-030", achieved_power=achieved, alpha=alpha, sidedness=sides,
        realized_design=design, method="existing paired noncentral-t evaluation following equation 8.12",
        calculation_mode="existing_noncentral_t_evaluation",
        inputs={"standardized_effect": effect, "n_pairs": n_pairs,
                "subjects_per_pair": subjects_per_pair, "even_sequence": even_sequence},
        trace={"kernel": "existing_noncentral_t", "degrees_of_freedom": degrees,
               "noncentrality_parameter": noncentrality},
        extra={"null_value": 0.0, "alternative_value": effect,
               "effect_measure": "paired_standardized_mean_difference",
               "degrees_of_freedom": degrees,
               "noncentrality_parameter": noncentrality},
    )


def _power_margin_004(
    *, standard_proportion: float, test_proportion: float, positive_margin: float,
    n_standard: int, n_test: int, alpha: float = 0.025,
    favorable_direction: str = "larger",
) -> dict[str, Any]:
    ps = _margin_probability("standard_proportion", standard_proportion)
    pt = _margin_probability("test_proportion", test_proportion)
    margin = _margin_positive("positive_margin", positive_margin)
    direction = _margin_direction(favorable_direction)
    planned = pt - ps
    boundary, distance = _margin_ni_boundary(planned, margin, direction)
    design = _allocation_design("standard", n_standard, "test", n_test)
    phi = n_test / n_standard
    variance = phi * ps * (1-ps) + pt * (1-pt)
    weight = sqrt(variance)
    za = _z_alpha(alpha, 1)
    scale = (1+phi)/phi
    achieved, zb = _achieved_power_weighted_normal(
        design["total"], scale=scale, null_weight=weight,
        alternative_weight=weight, distance=distance, z_alpha=za,
    )
    return _power_result(
        "MARGIN-004", achieved_power=achieved, alpha=alpha, sidedness=1,
        realized_design=design, method="equation 11.6 simple risk-difference noninferiority",
        calculation_mode="inverse_of_existing_sample_size_method",
        inputs={"standard_proportion": ps, "test_proportion": pt,
                "positive_margin": margin, "favorable_direction": direction,
                "n_standard": n_standard, "n_test": n_test},
        trace={"kernel": "weighted_linear_normal", "z_alpha": za,
               "z_beta_equivalent": zb, "scale": scale,
               "null_weight": weight, "alternative_weight": weight,
               "distance": distance, "signed_null_boundary": boundary},
        extra={"null_value": boundary, "alternative_value": planned,
               "effect_measure": "risk_difference_test_minus_standard",
               "margin": margin, "favorable_direction": direction,
               "allocation_ratio": phi},
    )


POWER_METHODS: dict[str, Callable[..., dict[str, Any]]] = {
    "ONE-001": _power_one_001,
    "ONE-002": _power_one_002,
    "ONE-004": _power_one_004,
    "TWO-001": _power_two_001,
    "TWO-002": _power_two_002,
    "TWO-004": _power_two_004,
    "TWO-005": _power_two_005,
    "TWO-006": _power_two_006,
    "TWO-007": _power_two_007,
    "TWO-008": _power_two_008,
    "TWO-009": _power_two_009,
    "TWO-010": _power_two_010,
    "TWO-011": _power_two_011,
    "TWO-012": _power_two_012,
    "TWO-013": _power_two_013,
    "TWO-014": _power_two_014,
    "TWO-015": _power_two_015,
    "TWO-016": _power_two_016,
    "TWO-023": _power_two_023,
    "TWO-026": _power_two_026,
    "TWO-029": _power_two_029,
    "TWO-030": _power_two_030,
    "TWO-031": _power_two_031,
    "TWO-032": _power_two_032,
    "TWO-033": _power_two_033,
    "MARGIN-001": _power_margin_001,
    "MARGIN-002": _power_margin_002,
    "MARGIN-004": _power_margin_004,
    "MARGIN-005": _power_margin_005,
    "MARGIN-006": _power_margin_006,
}


def _canonical_model_id(engine_id: str) -> str:
    canonical = str(engine_id).upper()
    for suffix in (".SAMPLE_SIZE", ".POWER", ".N"):
        if canonical.endswith(suffix):
            canonical = canonical[:-len(suffix)]
            break
    return canonical


def calculate_power(engine_id: str, inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate Phase 1 achieved power for a fixed realized integer design."""
    model = _canonical_model_id(engine_id)
    if model not in PHASE1_POWER_ENGINE_IDS:
        raise ValueError(f"power is not supported for {engine_id}")
    if model not in POWER_METHODS:
        raise ValueError(f"Phase 1 power adapter is not yet available for {engine_id}")
    if not isinstance(inputs, Mapping):
        raise ValueError("power inputs must be an object")
    return POWER_METHODS[model](**dict(inputs))


__all__ = [
    "BATCH_1_ENGINE_IDS", "BATCH_2_ENGINE_IDS", "BATCH_3_ENGINE_IDS",
    "PHASE1_POWER_ENGINE_IDS", "POWER_METHODS", "calculate_power",
    "previous_feasible_design",
]
