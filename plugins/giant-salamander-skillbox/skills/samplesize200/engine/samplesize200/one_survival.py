"""One-sample Kaplan--Meier survival-probability design.

Implements Nagashima et al. (2021), equation (2), restricted to the
arcsine square-root transformation with exponential survival and uniform
accrual.  This is an end-to-end SAMPLE_SIZE procedure, not an event-count
component.
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any

from scipy.integrate import quad


METHOD_ID = "ONE-S-001"
PROCEDURE_ID = "ONE-S-001.SAMPLE_SIZE"


def _probability(name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or not 0 < float(value) < 1:
        raise ValueError(f"{name} must be strictly between 0 and 1")
    return float(value)


def _positive(name: str, value: float, *, allow_zero: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")
    value = float(value)
    if value < 0 if allow_zero else value <= 0:
        raise ValueError(f"{name} must be {'nonnegative' if allow_zero else 'positive'}")
    return value


def _km_variance(survival_probability: float, analysis_time: float,
                 accrual_time: float, followup_time: float) -> tuple[float, dict[str, Any]]:
    """Return asymptotic variance of sqrt(n){S_hat(t)-S(t)}."""
    hazard = -math.log(survival_probability) / analysis_time
    if analysis_time <= followup_time:
        integral = math.exp(hazard * analysis_time) - 1.0
        integration = {"method": "analytic_no_type_i_censoring", "converged": True, "absolute_error": 0.0}
    else:
        total_time = accrual_time + followup_time
        if accrual_time <= 0:
            raise ValueError("accrual_time must be positive when analysis_time exceeds followup_time")
        if analysis_time >= total_time:
            raise ValueError("analysis_time must be less than accrual_time + followup_time")
        first = math.exp(hazard * followup_time) - 1.0
        second, error = quad(
            lambda time: accrual_time * hazard * math.exp(hazard * time) / (total_time - time),
            followup_time, analysis_time, epsabs=1e-12, epsrel=1e-12, limit=200,
        )
        integral = first + second
        integration = {"method": "scipy.integrate.quad", "converged": math.isfinite(second), "absolute_error": error, "epsabs": 1e-12, "epsrel": 1e-12, "subinterval_limit": 200}
    variance = survival_probability ** 2 * integral
    return variance, {"hazard": hazard, "integral": integral, **integration}


def one_sample_survival_arcsine(*, analysis_time: float,
                                null_survival_probability: float,
                                alternative_survival_probability: float,
                                accrual_time: float,
                                followup_time: float,
                                alpha: float = 0.05,
                                power: float = 0.80,
                                sides: int = 1,
                                attrition_rate: float = 0.0) -> dict[str, Any]:
    """Required participants for a transformed one-sample KM test."""
    t = _positive("analysis_time", analysis_time)
    accrual = _positive("accrual_time", accrual_time, allow_zero=True)
    followup = _positive("followup_time", followup_time, allow_zero=True)
    s0 = _probability("null_survival_probability", null_survival_probability)
    s1 = _probability("alternative_survival_probability", alternative_survival_probability)
    alpha = _probability("alpha", alpha)
    power = _probability("power", power)
    if s0 == s1:
        raise ValueError("null and alternative survival probabilities must differ")
    if sides not in {1, 2}:
        raise ValueError("sides must be 1 or 2")
    if not isinstance(attrition_rate, (int, float)) or isinstance(attrition_rate, bool) or not math.isfinite(float(attrition_rate)) or not 0 <= float(attrition_rate) < 1:
        raise ValueError("attrition_rate must be in [0, 1)")
    attrition = float(attrition_rate)

    variance0, integration0 = _km_variance(s0, t, accrual, followup)
    variance1, integration1 = _km_variance(s1, t, accrual, followup)
    transform0 = math.asin(math.sqrt(s0))
    transform1 = math.asin(math.sqrt(s1))
    epsilon = transform1 - transform0
    derivative0 = 1.0 / (2.0 * math.sqrt(s0 * (1.0 - s0)))
    derivative1 = 1.0 / (2.0 * math.sqrt(s1 * (1.0 - s1)))
    tau0 = derivative0 * math.sqrt(variance0)
    tau1 = derivative1 * math.sqrt(variance1)
    z_alpha = NormalDist().inv_cdf(1.0 - alpha / sides)
    z_power = NormalDist().inv_cdf(power)
    raw_total = (tau1 * (z_alpha + z_power) / abs(epsilon)) ** 2
    rounded_total = math.ceil(raw_total)
    raw_attrition_adjusted_total = raw_total / (1.0 - attrition)
    final_total = math.ceil(raw_attrition_adjusted_total)

    quantities = [
        {"key": "raw_total", "value": raw_total, "quantity": "participants", "unit": "person", "stage": "raw"},
        {"key": "rounded_total", "value": rounded_total, "quantity": "participants", "unit": "person", "stage": "rounded"},
        {"key": "raw_attrition_adjusted_total", "value": raw_attrition_adjusted_total, "quantity": "participants", "unit": "person", "stage": "design_constrained"},
        {"key": "final_total", "value": final_total, "quantity": "participants", "unit": "person", "stage": "final"},
    ]
    return {
        "method_id": METHOD_ID,
        "formula_reference": "Nagashima et al. (2021), equation (2), arcsine square-root transformation; exponential survival with uniform accrual",
        "inputs": {
            "analysis_time": t, "null_survival_probability": s0,
            "alternative_survival_probability": s1, "accrual_time": accrual,
            "followup_time": followup, "alpha": alpha, "power": power,
            "sides": sides, "attrition_rate": attrition,
        },
        "intermediate": {
            "transformation": "arcsin_sqrt", "g_null": transform0,
            "g_alternative": transform1, "epsilon": epsilon,
            "derivative_null": derivative0, "derivative_alternative": derivative1,
            "km_variance_null": variance0, "km_variance_alternative": variance1,
            "tau_null": tau0, "tau_alternative": tau1,
            "z_alpha": z_alpha, "z_power": z_power,
            "null_integration": integration0, "alternative_integration": integration1,
        },
        "raw_total": raw_total,
        "rounded_total": rounded_total,
        "raw_attrition_adjusted_total": raw_attrition_adjusted_total,
        "final_total": final_total,
        "rounding_rule": "ceil raw sample size after optional attrition inflation n/(1-r)",
        "warnings": [
            "EXPONENTIAL_SURVIVAL_ASSUMPTION",
            "UNIFORM_ACCRUAL_ASSUMPTION",
            "ARCSINE_SQUARE_ROOT_TRANSFORMED_KM_NORMAL_APPROXIMATION",
        ],
        "quantities": quantities,
        "source_provenance": {
            "chapter": None,
            "equation_or_section": "Nagashima et al. (2021), equation (2), Sections 2.2 and 2.4",
            "preferred_source": "https://doi.org/10.1002/pst.2090",
            "supporting_source": "https://arxiv.org/abs/2012.03355",
            "implementation_page": "https://nshi.jp/contents/stat/onesurv/",
            "source_discrepancy_ids": [],
        },
        "validation_evidence": {
            "scope": "method_implementation",
            "input_match_claim": False,
            "fixed_table_fixture_ids": ["validation/one_s_001_tables.csv::paper_table_3_arcsin"],
            "example_fixture_ids": [],
            "independent_audit_case_ids": ["tests/test_one_s_001_independent_audit.py"],
            "discrepancy_ids": [],
        },
    }


ONE_SURVIVAL_PROCEDURES = {PROCEDURE_ID: one_sample_survival_arcsine}
