"""Chapter 11 noninferiority, equivalence, and crossover-BE procedures.

These are preview procedure interfaces.  The canonical difference is test
minus standard (T-S), whereas Chapter 11 prints S-T for means/proportions.
Positive margins are retained and transformed to signed null boundaries.
"""

from __future__ import annotations

from math import ceil, exp, isfinite, log, sqrt
from statistics import NormalDist
from typing import Any, Callable

from scipy.optimize import minimize_scalar
from scipy.stats import t

from ._version import VERSION
from .rounding import allocation_rounding


_N = NormalDist()


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than 0")
    return value


def _probability(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 < value < 1:
        raise ValueError(f"{name} must be a finite probability in (0, 1)")
    return value


def _inference(alpha: float, power: float) -> tuple[float, float]:
    alpha = _probability("alpha", alpha)
    power = _probability("power", power)
    return _N.inv_cdf(1 - alpha), _N.inv_cdf(power)


def _direction(value: str) -> str:
    if value not in {"larger", "smaller"}:
        raise ValueError("favorable_direction must be 'larger' or 'smaller'")
    return value


def _component_power(planned: float, lower: float, upper: float, power: float) -> tuple[float, str]:
    midpoint = (lower + upper) / 2
    symmetric = abs(planned - midpoint) <= 1e-12 * max(1.0, abs(planned), abs(midpoint))
    if symmetric:
        return 1 - (1 - power) / 2, "symmetric plan: Chapter 11 splits beta equally between the two limits"
    return power, "asymmetric plan: Chapter 11 assigns beta to the limiting one-sided hypothesis"


def _quantities(raw: float, rounded: int, final: int, *, paired: bool = False,
                subjects_per_pair: int = 1) -> list[dict[str, Any]]:
    if paired:
        return [
            {"key": "raw_pairs", "value": raw, "quantity": "pairs", "unit": "pairs", "stage": "raw"},
            {"key": "rounded_pairs", "value": rounded, "quantity": "pairs", "unit": "pairs", "stage": "rounded"},
            {"key": "final_pairs", "value": final, "quantity": "pairs", "unit": "pairs", "stage": "final"},
            {"key": "final_total", "value": final * subjects_per_pair, "quantity": "participants", "unit": "person", "stage": "final"},
        ]
    return [
        {"key": "raw_total", "value": raw, "quantity": "participants", "unit": "person", "stage": "raw"},
        {"key": "rounded_total", "value": rounded, "quantity": "participants", "unit": "person", "stage": "rounded"},
        {"key": "final_total", "value": final, "quantity": "participants", "unit": "person", "stage": "final"},
    ]


def _evidence(method: str, equation: str, fixtures: list[str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    table = {"MARGIN-001":"Table 11.1", "MARGIN-003":"Table 11.2",
             "MARGIN-005":"Table 11.3", "MARGIN-013":"Table 11.4",
             "MARGIN-014":"Table 11.4"}.get(method)
    discrepancies = {
        "MARGIN-005": ["CH11-EQ11.8-FRECHET-BOUND"],
        "MARGIN-011": ["CH11-EQ11.8-FRECHET-BOUND"],
        "MARGIN-006": ["CH11-EX11.7-INPUT-RESULT-INCONSISTENCY"],
        "MARGIN-013": ["CH11-TABLE11.4-SMALL-DF-ROUNDING"],
        "MARGIN-014": ["CH11-TABLE11.4-SMALL-DF-ROUNDING"],
    }.get(method, [])
    fixed = list(fixtures or [])
    if table:
        fixed.append(f"validation/chapter11_tables.csv::{table}")
    return (
        {"chapter": 11, "equation_or_section": equation,
         "preferred_source": "医学研究のためのサンプルサイズ設計_20220330.pdf",
         "source_discrepancy_ids": discrepancies},
        {"scope": "procedure_implementation", "input_match_claim": False,
         "fixed_fixture_ids": fixed,
         "example_fixture_ids": [f"validation/chapter11_examples.yaml::procedure_id={method}.SAMPLE_SIZE"],
         "independent_audit_case_ids": [f"CH11-AUDIT-{method}-01..05"],
         "discrepancy_ids": discrepancies},
    )


def _base_result(method: str, equation: str, inputs: dict[str, Any], raw: float,
                 *, paired: bool = False, subjects_per_pair: int = 1,
                 extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isfinite(raw) or raw <= 0:
        raise ValueError("inputs do not produce a positive finite sample size")
    rounded = ceil(raw)
    source, evidence = _evidence(method, equation)
    result: dict[str, Any] = {
        "product": "samplesize200 Alpha", "version": VERSION,
        "release_stage": "alpha", "model_id": method,
        "operation": "sample_size", "procedure_id": f"{method}.SAMPLE_SIZE",
        "method_id": method, "formula_reference": equation, "inputs": inputs,
        "raw_total": raw * subjects_per_pair if paired else raw,
        "rounded_total": rounded * subjects_per_pair if paired else rounded,
        "final_total": rounded * subjects_per_pair if paired else rounded,
        "raw_group_control": None, "raw_group_treatment": None,
        "rounded_group_control": None, "rounded_group_treatment": None,
        "final_group_control": None, "final_group_treatment": None,
        "rounding_rule": "ceil the unrounded required sample size",
        "warnings": [], "source_provenance": source,
        "validation_evidence": evidence, "schema_status": "preview",
    }
    if paired:
        result.update({"raw_pairs": raw, "rounded_pairs": rounded, "final_pairs": rounded,
                       "subjects_per_pair": subjects_per_pair})
    else:
        result.update(allocation_rounding(raw, float(inputs.get("allocation_ratio", 1.0))))
    result["primary_result"] = {
        "key": "final_total", "value": result["final_total"],
        "quantity": "participants", "unit": "person", "stage": "final",
    }
    if paired:
        result["quantities"] = _quantities(raw, rounded, rounded, paired=True,
                                            subjects_per_pair=subjects_per_pair)
    else:
        result["quantities"] = [
            {"key":"raw_total","value":raw,"quantity":"participants","unit":"person","stage":"raw"},
            {"key":"rounded_total","value":result["rounded_total"],"quantity":"participants","unit":"person","stage":"rounded"},
            {"key":"raw_group_standard","value":result["raw_group_control"],"quantity":"participants","unit":"person","stage":"raw"},
            {"key":"raw_group_test","value":result["raw_group_treatment"],"quantity":"participants","unit":"person","stage":"raw"},
            {"key":"rounded_group_standard","value":result["rounded_group_control"],"quantity":"participants","unit":"person","stage":"rounded"},
            {"key":"rounded_group_test","value":result["rounded_group_treatment"],"quantity":"participants","unit":"person","stage":"rounded"},
            {"key":"final_group_standard","value":result["final_group_control"],"quantity":"participants","unit":"person","stage":"allocation_adjusted"},
            {"key":"final_group_test","value":result["final_group_treatment"],"quantity":"participants","unit":"person","stage":"allocation_adjusted"},
            {"key":"final_total","value":result["final_total"],"quantity":"participants","unit":"person","stage":"final"},
        ]
    if extra:
        result.update(extra)
    return result


def _ni_boundary(planned: float, margin: float, direction: str) -> tuple[float, float]:
    direction = _direction(direction)
    boundary = -margin if direction == "larger" else margin
    distance = planned - boundary if direction == "larger" else boundary - planned
    if distance <= 0:
        raise ValueError("planned effect must lie on the favorable side of the noninferiority boundary")
    return boundary, distance


def independent_mean_noninferiority(*, planned_standard: float, planned_test: float,
                                    standard_deviation: float, positive_margin: float,
                                    allocation_ratio: float = 1.0, alpha: float = 0.025,
                                    power: float = 0.80,
                                    favorable_direction: str = "larger") -> dict[str, Any]:
    """MARGIN-001, equation 11.3."""
    sd, margin, phi = (_positive("standard_deviation", standard_deviation),
                       _positive("positive_margin", positive_margin),
                       _positive("allocation_ratio", allocation_ratio))
    planned = float(planned_test) - float(planned_standard)
    boundary, distance = _ni_boundary(planned, margin, favorable_direction)
    za, zb = _inference(alpha, power)
    raw = (1 + phi) ** 2 / phi * (za + zb) ** 2 * sd ** 2 / distance ** 2
    return _base_result("MARGIN-001", "equation 11.3", {
        "planned_standard": planned_standard, "planned_test": planned_test,
        "standard_deviation": sd, "positive_margin": margin,
        "canonical_contrast": "test-standard", "canonical_planned_effect": planned,
        "source_contrast": "standard-test", "signed_null_boundary": boundary,
        "favorable_direction": _direction(favorable_direction),
        "allocation_ratio": phi, "allocation_ratio_definition": "test/standard",
        "alpha": alpha, "alpha_semantics": "one-sided", "power": power,
        "z_alpha": za, "z_power": zb,
    }, raw)


def paired_mean_noninferiority(*, planned_standard: float, planned_test: float,
                               paired_standard_deviation: float, positive_margin: float,
                               alpha: float = 0.025, power: float = 0.80,
                               favorable_direction: str = "larger",
                               subjects_per_pair: int = 1,
                               even_sequence: bool = False) -> dict[str, Any]:
    """MARGIN-002, equation 11.4."""
    sd, margin = (_positive("paired_standard_deviation", paired_standard_deviation),
                  _positive("positive_margin", positive_margin))
    if not isinstance(subjects_per_pair, int) or isinstance(subjects_per_pair, bool) or subjects_per_pair < 1:
        raise ValueError("subjects_per_pair must be a positive integer")
    planned = float(planned_test) - float(planned_standard)
    boundary, distance = _ni_boundary(planned, margin, favorable_direction)
    za, zb = _inference(alpha, power)
    raw = 2 * (za + zb) ** 2 * sd ** 2 / distance ** 2
    result = _base_result("MARGIN-002", "equation 11.4", {
        "planned_standard": planned_standard, "planned_test": planned_test,
        "paired_standard_deviation": sd, "positive_margin": margin,
        "canonical_contrast": "test-standard", "canonical_planned_effect": planned,
        "source_contrast": "standard-test", "signed_null_boundary": boundary,
        "favorable_direction": _direction(favorable_direction), "allocation_ratio": 1.0,
        "alpha": alpha, "alpha_semantics": "one-sided", "power": power,
        "z_alpha": za, "z_power": zb, "even_sequence": bool(even_sequence),
    }, raw, paired=True, subjects_per_pair=subjects_per_pair)
    if even_sequence and result["final_pairs"] % 2:
        final_pairs = result["final_pairs"] + 1
        result.update({"design_constrained_pairs": final_pairs, "final_pairs": final_pairs,
                       "final_total": final_pairs * subjects_per_pair,
                       "final_sequence_1": final_pairs//2, "final_sequence_2": final_pairs//2})
        result["primary_result"]["value"] = result["final_total"]
        result["quantities"] = _quantities(raw, ceil(raw), final_pairs, paired=True,
                                            subjects_per_pair=subjects_per_pair)
        result["rounding_rule"] = "ceil paired sample size and enforce an even two-sequence allocation"
    return result


def _constrained_proportions(p_standard: float, p_test: float, phi: float,
                             boundary: float) -> tuple[float, float, dict[str, Any]]:
    """Constrained binomial MLE under p_test-p_standard=boundary."""
    lower, upper = max(0.0, -boundary), min(1.0, 1.0 - boundary)
    if lower >= upper:
        raise ValueError("the signed risk-difference boundary has no feasible null proportions")
    eps = 1e-12
    lo, hi = lower + eps, upper - eps
    def nll(qs: float) -> float:
        qt = qs + boundary
        return -(p_standard * log(qs) + (1-p_standard) * log(1-qs)
                 + phi * (p_test * log(qt) + (1-p_test) * log(1-qt)))
    fit = minimize_scalar(nll, bounds=(lo, hi), method="bounded", options={"xatol": 1e-14})
    if not fit.success:
        raise ValueError(f"constrained null MLE did not converge: {fit.message}")
    qs, qt = float(fit.x), float(fit.x + boundary)
    return qs, qt, {"solver": "bounded scalar likelihood minimization", "converged": True,
                    "search_lower": lower, "search_upper": upper,
                    "absolute_tolerance": 1e-14, "function_evaluations": int(fit.nfev)}


def _independent_proportion_component(p_standard: float, p_test: float, boundary: float,
                                      phi: float, za: float, zb: float,
                                      *, farrington_manning: bool) -> tuple[float, dict[str, Any]]:
    distance = (p_test - p_standard) - boundary
    if distance == 0:
        raise ValueError("planned risk difference equals the null boundary")
    planned_var = phi * p_standard * (1-p_standard) + p_test * (1-p_test)
    if farrington_manning:
        qs, qt, solver = _constrained_proportions(p_standard, p_test, phi, boundary)
        null_var = phi * qs * (1-qs) + qt * (1-qt)
    else:
        qs, qt, solver, null_var = p_standard, p_test, {"solver": "none", "converged": True}, planned_var
    raw = (1+phi)/phi * (za*sqrt(null_var) + zb*sqrt(planned_var))**2 / distance**2
    return raw, {"constrained_standard_proportion": qs, "constrained_test_proportion": qt,
                 "null_variance_term": null_var, "planned_variance_term": planned_var,
                 "solver_metadata": solver}


def _independent_proportion_ni(method: str, *, standard_proportion: float,
                               test_proportion: float, positive_margin: float,
                               allocation_ratio: float = 1.0, alpha: float = 0.025,
                               power: float = 0.80,
                               favorable_direction: str = "larger", fm: bool) -> dict[str, Any]:
    ps, pt = _probability("standard_proportion", standard_proportion), _probability("test_proportion", test_proportion)
    margin, phi = _positive("positive_margin", positive_margin), _positive("allocation_ratio", allocation_ratio)
    planned = pt-ps
    boundary, distance = _ni_boundary(planned, margin, favorable_direction)
    if not -1 < boundary < 1:
        raise ValueError("risk-difference boundary must be in (-1, 1)")
    za, zb = _inference(alpha, power)
    raw, audit = _independent_proportion_component(ps, pt, boundary, phi, za, zb, farrington_manning=fm)
    return _base_result(method, "equation 11.5" if fm else "equation 11.6", {
        "standard_proportion": ps, "test_proportion": pt, "positive_margin": margin,
        "canonical_contrast": "test-standard", "canonical_planned_effect": planned,
        "source_contrast": "standard-test", "signed_null_boundary": boundary,
        "distance_from_boundary": distance, "favorable_direction": _direction(favorable_direction),
        "allocation_ratio": phi, "allocation_ratio_definition": "test/standard",
        "alpha": alpha, "alpha_semantics": "one-sided", "power": power,
        "z_alpha": za, "z_power": zb,
    }, raw, extra=audit)


def independent_proportion_noninferiority_fm(**kwargs: Any) -> dict[str, Any]:
    return _independent_proportion_ni("MARGIN-003", fm=True, **kwargs)


def independent_proportion_noninferiority_simple(**kwargs: Any) -> dict[str, Any]:
    return _independent_proportion_ni("MARGIN-004", fm=False, **kwargs)


def _paired_proportion_raw(ps: float, pt: float, pi11: float, margin: float,
                           za: float, zb: float) -> tuple[float, dict[str, float]]:
    delta = ps-pt
    a = ps-pi11
    b = 2*a-delta-margin
    c = a-delta
    d = a-delta-margin
    if min(a, b, c, d) <= 0:
        raise ValueError("paired joint probability and margin make equation 11.7 undefined")
    raw = (za*b*sqrt(c) + zb*(2*a-delta)*sqrt(d))**2 / (a*b*margin**2)
    return raw, {"source_delta_standard_minus_test": delta, "equation_11_7_a": a,
                 "equation_11_7_b": b, "equation_11_7_c": c, "equation_11_7_d": d}


def _paired_joint(ps: float, pt: float, margin: float, joint_success: float | None) -> tuple[float, str]:
    if joint_success is None:
        delta = ps-pt
        value = max(ps-delta-margin-(1-ps)/2, (ps-delta-margin)/2)
        source = "equation 11.8 conservative joint-success approximation"
    else:
        value, source = float(joint_success), "direct planned joint-success probability"
    lower, upper = max(0.0, ps+pt-1), min(ps, pt)
    if joint_success is not None and not lower <= value <= upper:
        raise ValueError("joint_success_probability is incompatible with the marginal proportions")
    if joint_success is None and not 0 <= value <= upper:
        raise ValueError("equation 11.8 does not produce a usable joint-success approximation")
    return value, source


def paired_proportion_noninferiority(*, standard_proportion: float, test_proportion: float,
                                     positive_margin: float, joint_success_probability: float | None = None,
                                     alpha: float = 0.025, power: float = 0.80,
                                     favorable_direction: str = "larger",
                                     subjects_per_pair: int = 1,
                                     even_sequence: bool = False) -> dict[str, Any]:
    ps, pt = _probability("standard_proportion", standard_proportion), _probability("test_proportion", test_proportion)
    margin = _positive("positive_margin", positive_margin)
    direction = _direction(favorable_direction)
    # Equation 11.7 is oriented as test no worse than standard.  Reverse labels
    # for a smaller-favorable outcome and retain both orientations.
    source_ps, source_pt = (ps, pt) if direction == "larger" else (pt, ps)
    pi11, pi11_source = _paired_joint(source_ps, source_pt, margin, joint_success_probability)
    za, zb = _inference(alpha, power)
    raw, audit = _paired_proportion_raw(source_ps, source_pt, pi11, margin, za, zb)
    boundary = -margin if direction == "larger" else margin
    result = _base_result("MARGIN-005", "equations 11.7 and 11.8", {
        "standard_proportion": ps, "test_proportion": pt,
        "joint_success_probability": pi11, "joint_success_source": pi11_source,
        "positive_margin": margin, "canonical_contrast": "test-standard",
        "canonical_planned_effect": pt-ps, "source_contrast": "standard-test",
        "signed_null_boundary": boundary, "favorable_direction": direction,
        "allocation_ratio": 1.0, "alpha": alpha, "alpha_semantics": "one-sided",
        "power": power, "z_alpha": za, "z_power": zb,
        "even_sequence": bool(even_sequence),
    }, raw, paired=True, subjects_per_pair=subjects_per_pair, extra=audit)
    if even_sequence and result["final_pairs"] % 2:
        final_pairs = result["final_pairs"] + 1
        result.update({"design_constrained_pairs": final_pairs, "final_pairs": final_pairs,
                       "final_total": final_pairs * subjects_per_pair,
                       "final_sequence_1": final_pairs//2, "final_sequence_2": final_pairs//2})
        result["primary_result"]["value"] = result["final_total"]
        result["quantities"] = _quantities(raw, ceil(raw), final_pairs, paired=True,
                                            subjects_per_pair=subjects_per_pair)
        result["rounding_rule"] = "ceil pairs; if requested, enforce an even two-sequence allocation"
    return result


def _g(hazard: float, censoring: float, accrual: float, followup: float) -> float:
    combined = hazard+censoring
    probability = hazard/combined * (1-(exp(-followup*combined)-exp(-(accrual+followup)*combined))/(accrual*combined))
    if probability <= 0:
        raise ValueError("event probability implied by follow-up inputs must be positive")
    return hazard**2/probability


def _hr_component(planned_hr: float, boundary: float, lambda_standard: float,
                  censoring: float, accrual: float, followup: float,
                  phi: float, za: float, zb: float) -> tuple[float, dict[str, float]]:
    log_distance = abs(log(boundary)-log(planned_hr))
    if log_distance == 0:
        raise ValueError("planned hazard ratio equals the null boundary")
    gs = _g(lambda_standard, censoring, accrual, followup)
    gt = _g(planned_hr*lambda_standard, censoring, accrual, followup)
    raw = (1+phi)/phi * (za+zb)**2/log_distance**2 * (phi*gs/lambda_standard**2 + phi*gt/(planned_hr*lambda_standard**2))
    return raw, {"g_standard": gs, "g_test": gt, "log_distance_from_boundary": log_distance}


def hazard_ratio_noninferiority(*, planned_hazard_ratio: float, positive_margin: float,
                                standard_hazard: float, censoring_hazard: float = 0.0,
                                accrual_time: float, followup_time: float,
                                allocation_ratio: float = 1.0, alpha: float = 0.025,
                                power: float = 0.80,
                                favorable_direction: str = "smaller") -> dict[str, Any]:
    hr, margin = _positive("planned_hazard_ratio", planned_hazard_ratio), _positive("positive_margin", positive_margin)
    direction = _direction(favorable_direction)
    boundary = margin if direction == "smaller" else 1/margin
    distance = boundary-hr if direction == "smaller" else hr-boundary
    if distance <= 0:
        raise ValueError("planned hazard ratio must lie on the favorable side of the boundary")
    hs, xi, a, f, phi = (_positive("standard_hazard", standard_hazard), float(censoring_hazard),
                         _positive("accrual_time", accrual_time), _positive("followup_time", followup_time),
                         _positive("allocation_ratio", allocation_ratio))
    if not isfinite(xi) or xi < 0:
        raise ValueError("censoring_hazard must be finite and nonnegative")
    za, zb = _inference(alpha, power)
    raw, audit = _hr_component(hr, boundary, hs, xi, a, f, phi, za, zb)
    return _base_result("MARGIN-006", "equations 11.9--11.11", {
        "planned_hazard_ratio": hr, "hazard_ratio_definition": "test/standard",
        "positive_margin": margin, "signed_null_boundary": boundary,
        "effect_scale": "ratio and log_ratio", "favorable_direction": direction,
        "standard_hazard": hs, "censoring_hazard": xi, "accrual_time": a, "followup_time": f,
        "allocation_ratio": phi, "allocation_ratio_definition": "test/standard",
        "alpha": alpha, "alpha_semantics": "one-sided", "power": power,
        "z_alpha": za, "z_power": zb,
    }, raw, extra=audit)


def _equivalence_result(method: str, equation: str, inputs: dict[str, Any], lower_raw: float,
                        upper_raw: float, *, paired: bool = False, subjects_per_pair: int = 1,
                        component_details: dict[str, Any] | None = None) -> dict[str, Any]:
    adopted = max(lower_raw, upper_raw)
    result = _base_result(method, equation, inputs, adopted, paired=paired,
                          subjects_per_pair=subjects_per_pair)
    result.update({"raw_lower_hypothesis": lower_raw, "raw_upper_hypothesis": upper_raw,
                   "adopted_hypothesis": "lower" if lower_raw >= upper_raw else "upper",
                   "hypothesis_component_required_sizes": {
                       "lower": {"raw": lower_raw, "rounded": ceil(lower_raw)},
                       "upper": {"raw": upper_raw, "rounded": ceil(upper_raw)},
                   }})
    if component_details:
        result["component_details"] = component_details
    return result


def independent_mean_equivalence(*, planned_standard: float, planned_test: float,
                                 standard_deviation: float, lower_boundary: float,
                                 upper_boundary: float, allocation_ratio: float = 1.0,
                                 alpha: float = 0.025, power: float = 0.80) -> dict[str, Any]:
    sd, phi = _positive("standard_deviation", standard_deviation), _positive("allocation_ratio", allocation_ratio)
    planned, lower, upper = float(planned_test)-float(planned_standard), float(lower_boundary), float(upper_boundary)
    if not lower < planned < upper:
        raise ValueError("planned mean difference must lie strictly inside the equivalence boundaries")
    component_power, beta_rule = _component_power(planned, lower, upper, _probability("power", power))
    za, zb = _inference(alpha, component_power)
    coefficient = (1+phi)**2/phi*(za+zb)**2*sd**2
    lr, ur = coefficient/(planned-lower)**2, coefficient/(upper-planned)**2
    return _equivalence_result("MARGIN-007", "section 11.4 using equation 11.3", {
        "planned_standard": planned_standard, "planned_test": planned_test,
        "standard_deviation": sd, "canonical_contrast": "test-standard",
        "canonical_planned_effect": planned, "lower_boundary": lower, "upper_boundary": upper,
        "alpha": alpha, "alpha_semantics": "per one-sided TOST hypothesis",
        "power": power, "component_power": component_power, "beta_allocation_rule": beta_rule,
        "allocation_ratio": phi, "allocation_ratio_definition": "test/standard",
        "z_alpha": za, "z_power_component": zb,
    }, lr, ur)


def paired_mean_equivalence(*, planned_standard: float, planned_test: float,
                            paired_standard_deviation: float, lower_boundary: float,
                            upper_boundary: float, alpha: float = 0.025,
                            power: float = 0.80, subjects_per_pair: int = 1) -> dict[str, Any]:
    sd = _positive("paired_standard_deviation", paired_standard_deviation)
    planned, lower, upper = float(planned_test)-float(planned_standard), float(lower_boundary), float(upper_boundary)
    if not lower < planned < upper:
        raise ValueError("planned paired mean difference must lie strictly inside the equivalence boundaries")
    component_power, beta_rule = _component_power(planned, lower, upper, _probability("power", power))
    za, zb = _inference(alpha, component_power)
    coefficient = 2*(za+zb)**2*sd**2
    return _equivalence_result("MARGIN-008", "section 11.4 using equation 11.4", {
        "planned_standard": planned_standard, "planned_test": planned_test,
        "paired_standard_deviation": sd, "canonical_contrast": "test-standard",
        "canonical_planned_effect": planned, "lower_boundary": lower, "upper_boundary": upper,
        "alpha": alpha, "alpha_semantics": "per one-sided TOST hypothesis",
        "power": power, "component_power": component_power, "beta_allocation_rule": beta_rule,
        "allocation_ratio": 1.0, "z_alpha": za, "z_power_component": zb,
    }, coefficient/(planned-lower)**2, coefficient/(upper-planned)**2,
        paired=True, subjects_per_pair=subjects_per_pair)


def _independent_proportion_equivalence(method: str, *, standard_proportion: float,
                                        test_proportion: float, lower_boundary: float,
                                        upper_boundary: float, allocation_ratio: float = 1.0,
                                        alpha: float = 0.025, power: float = 0.80,
                                        fm: bool) -> dict[str, Any]:
    ps, pt, phi = (_probability("standard_proportion", standard_proportion),
                   _probability("test_proportion", test_proportion),
                   _positive("allocation_ratio", allocation_ratio))
    planned, lower, upper = pt-ps, float(lower_boundary), float(upper_boundary)
    if not -1 < lower < planned < upper < 1:
        raise ValueError("planned risk difference must lie strictly inside feasible equivalence boundaries")
    component_power, beta_rule = _component_power(planned, lower, upper, _probability("power", power))
    za, zb = _inference(alpha, component_power)
    lr, ld = _independent_proportion_component(ps, pt, lower, phi, za, zb, farrington_manning=fm)
    ur, ud = _independent_proportion_component(ps, pt, upper, phi, za, zb, farrington_manning=fm)
    return _equivalence_result(method, f"section 11.4 using equation {'11.5' if fm else '11.6'}", {
        "standard_proportion": ps, "test_proportion": pt,
        "canonical_contrast": "test-standard", "canonical_planned_effect": planned,
        "lower_boundary": lower, "upper_boundary": upper,
        "alpha": alpha, "alpha_semantics": "per one-sided TOST hypothesis",
        "power": power, "component_power": component_power, "beta_allocation_rule": beta_rule,
        "allocation_ratio": phi, "allocation_ratio_definition": "test/standard",
        "z_alpha": za, "z_power_component": zb,
    }, lr, ur, component_details={"lower": ld, "upper": ud})


def independent_proportion_equivalence_fm(**kwargs: Any) -> dict[str, Any]:
    return _independent_proportion_equivalence("MARGIN-009", fm=True, **kwargs)


def independent_proportion_equivalence_simple(**kwargs: Any) -> dict[str, Any]:
    return _independent_proportion_equivalence("MARGIN-010", fm=False, **kwargs)


def paired_proportion_equivalence(*, standard_proportion: float, test_proportion: float,
                                  lower_boundary: float, upper_boundary: float,
                                  joint_success_probability: float | None = None,
                                  alpha: float = 0.025, power: float = 0.80,
                                  subjects_per_pair: int = 1) -> dict[str, Any]:
    ps, pt = _probability("standard_proportion", standard_proportion), _probability("test_proportion", test_proportion)
    planned, lower, upper = pt-ps, float(lower_boundary), float(upper_boundary)
    if not -1 < lower < planned < upper < 1 or not lower < 0 < upper:
        raise ValueError("paired equation 11.7 requires boundaries spanning zero and the plan inside them")
    component_power, beta_rule = _component_power(planned, lower, upper, _probability("power", power))
    za, zb = _inference(alpha, component_power)
    lower_margin, upper_margin = -lower, upper
    pi11_l, source_l = _paired_joint(ps, pt, lower_margin, joint_success_probability)
    lr, ld = _paired_proportion_raw(ps, pt, pi11_l, lower_margin, za, zb)
    pi11_u, source_u = _paired_joint(pt, ps, upper_margin, joint_success_probability)
    ur, ud = _paired_proportion_raw(pt, ps, pi11_u, upper_margin, za, zb)
    return _equivalence_result("MARGIN-011", "section 11.4 using equations 11.7 and 11.8", {
        "standard_proportion": ps, "test_proportion": pt,
        "joint_success_probability": joint_success_probability,
        "canonical_contrast": "test-standard", "canonical_planned_effect": planned,
        "lower_boundary": lower, "upper_boundary": upper,
        "alpha": alpha, "alpha_semantics": "per one-sided TOST hypothesis",
        "power": power, "component_power": component_power, "beta_allocation_rule": beta_rule,
        "allocation_ratio": 1.0, "z_alpha": za, "z_power_component": zb,
    }, lr, ur, paired=True, subjects_per_pair=subjects_per_pair,
        component_details={"lower": {**ld, "joint_success_source": source_l},
                           "upper": {**ud, "joint_success_source": source_u}})


def hazard_ratio_equivalence(*, planned_hazard_ratio: float, lower_boundary: float,
                             upper_boundary: float, standard_hazard: float,
                             censoring_hazard: float = 0.0, accrual_time: float,
                             followup_time: float, allocation_ratio: float = 1.0,
                             alpha: float = 0.025, power: float = 0.80) -> dict[str, Any]:
    hr, lower, upper = _positive("planned_hazard_ratio", planned_hazard_ratio), _positive("lower_boundary", lower_boundary), _positive("upper_boundary", upper_boundary)
    if not lower < hr < upper:
        raise ValueError("planned hazard ratio must lie strictly inside the equivalence boundaries")
    hs, xi, a, f, phi = (_positive("standard_hazard", standard_hazard), float(censoring_hazard),
                         _positive("accrual_time", accrual_time), _positive("followup_time", followup_time),
                         _positive("allocation_ratio", allocation_ratio))
    if not isfinite(xi) or xi < 0:
        raise ValueError("censoring_hazard must be finite and nonnegative")
    log_planned, log_lower, log_upper = log(hr), log(lower), log(upper)
    component_power, beta_rule = _component_power(log_planned, log_lower, log_upper, _probability("power", power))
    za, zb = _inference(alpha, component_power)
    lr, ld = _hr_component(hr, lower, hs, xi, a, f, phi, za, zb)
    ur, ud = _hr_component(hr, upper, hs, xi, a, f, phi, za, zb)
    return _equivalence_result("MARGIN-012", "section 11.4 using equations 11.9--11.11", {
        "planned_hazard_ratio": hr, "hazard_ratio_definition": "test/standard",
        "effect_scale": "ratio and log_ratio", "lower_boundary": lower, "upper_boundary": upper,
        "standard_hazard": hs, "censoring_hazard": xi, "accrual_time": a, "followup_time": f,
        "allocation_ratio": phi, "allocation_ratio_definition": "test/standard",
        "alpha": alpha, "alpha_semantics": "per one-sided TOST hypothesis",
        "power": power, "component_power": component_power, "beta_allocation_rule": beta_rule,
        "z_alpha": za, "z_power_component": zb,
    }, lr, ur, component_details={"lower": ld, "upper": ud})


def _be(*, method: str, planned_ratio: float, within_subject_log_sd: float | None,
        coefficient_of_variation: float | None, lower_boundary: float,
        upper_boundary: float, alpha: float, power: float,
        max_iterations: int) -> dict[str, Any]:
    ratio, lower, upper = (_positive("planned_ratio", planned_ratio),
                           _positive("lower_boundary", lower_boundary),
                           _positive("upper_boundary", upper_boundary))
    if not lower < ratio < upper:
        raise ValueError("planned_ratio must lie strictly inside the bioequivalence boundaries")
    if (within_subject_log_sd is None) == (coefficient_of_variation is None):
        raise ValueError("provide exactly one of within_subject_log_sd or coefficient_of_variation")
    if coefficient_of_variation is not None:
        cv = _positive("coefficient_of_variation", coefficient_of_variation)
        sigma = sqrt(log(1+cv**2))
    else:
        sigma, cv = _positive("within_subject_log_sd", float(within_subject_log_sd)), None
    alpha, power = _probability("alpha", alpha), _probability("power", power)
    za = _N.inv_cdf(1-alpha)
    symmetric = method == "MARGIN-013"
    if symmetric and abs(ratio-1) > 1e-12:
        raise ValueError("MARGIN-013 requires planned_ratio equal to 1")
    if not symmetric and abs(ratio-1) <= 1e-12:
        raise ValueError("MARGIN-014 requires planned_ratio different from 1")
    zpower = _N.inv_cdf(1-(1-power)/2) if symmetric else _N.inv_cdf(power)
    limiting = lower if ratio < 1 else upper
    distance = abs(log(limiting)-log(ratio))/sigma
    current_df = float("inf")
    history: list[dict[str, Any]] = []
    final = None
    convergence_reason = "fixed point"
    for iteration in range(1, max_iterations+1):
        critical = za if current_df == float("inf") else float(t.ppf(1-alpha, current_df))
        raw = 2*(critical+zpower)**2/distance**2
        candidate = max(4, ceil(raw))
        history.append({"iteration": iteration, "degrees_of_freedom": None if current_df == float("inf") else current_df,
                        "critical_value": critical, "raw_pairs": raw, "rounded_candidate": candidate})
        if final == candidate:
            break
        if len(history) >= 3 and candidate == history[-3]["rounded_candidate"]:
            final = max(candidate, int(history[-2]["rounded_candidate"]))
            current_df = final-2
            convergence_reason = "conservative resolution of a two-cycle in integer df iteration"
            critical = float(t.ppf(1-alpha, current_df))
            raw = 2*(critical+zpower)**2/distance**2
            break
        final, current_df = candidate, candidate-2
    else:
        raise ValueError("bioequivalence t-quantile iteration did not converge")
    raw = history[-1]["raw_pairs"]
    design_final = final if final % 2 == 0 else final + 1
    result = _base_result(method, "equations 11.13 and 11.15" if symmetric else "equations 11.14 and 11.15", {
        "planned_ratio": ratio, "ratio_definition": "test/reference",
        "within_subject_log_sd": sigma, "coefficient_of_variation": cv,
        "lower_boundary": lower, "upper_boundary": upper,
        "alpha": alpha, "alpha_semantics": "per one-sided TOST hypothesis",
        "power": power, "beta_allocation_rule": "beta/2 for planned ratio 1" if symmetric else "beta at the limiting boundary",
        "limiting_boundary": limiting, "allocation_ratio": 1.0,
    }, raw, paired=True, subjects_per_pair=1, extra={
        "converged": True, "convergence_reason": convergence_reason,
        "iterations": len(history), "iteration_history": history,
        "degrees_of_freedom": final-2, "raw_initial_infinite_df": history[0]["raw_pairs"],
        "raw_pairs": raw, "rounded_pairs": final, "design_constrained_pairs": design_final,
        "final_pairs": design_final, "final_total": design_final,
        "final_sequence_tr": design_final//2, "final_sequence_rt": design_final//2,
    })
    result["primary_result"]["value"] = design_final
    result["quantities"] = _quantities(raw, final, design_final, paired=True)
    result["rounding_rule"] = "iterate t critical value with df=N-2; ceil and enforce an even TR/RT sequence block"
    return result


def crossover_bioequivalence_ratio_one(*, planned_ratio: float = 1.0,
                                       within_subject_log_sd: float | None = None,
                                       coefficient_of_variation: float | None = None,
                                       lower_boundary: float = 0.80,
                                       upper_boundary: float = 1.25,
                                       alpha: float = 0.05, power: float = 0.90,
                                       max_iterations: int = 100) -> dict[str, Any]:
    return _be(method="MARGIN-013", planned_ratio=planned_ratio,
               within_subject_log_sd=within_subject_log_sd,
               coefficient_of_variation=coefficient_of_variation,
               lower_boundary=lower_boundary, upper_boundary=upper_boundary,
               alpha=alpha, power=power, max_iterations=max_iterations)


def crossover_bioequivalence_ratio_not_one(*, planned_ratio: float,
                                           within_subject_log_sd: float | None = None,
                                           coefficient_of_variation: float | None = None,
                                           lower_boundary: float = 0.80,
                                           upper_boundary: float = 1.25,
                                           alpha: float = 0.05, power: float = 0.90,
                                           max_iterations: int = 100) -> dict[str, Any]:
    return _be(method="MARGIN-014", planned_ratio=planned_ratio,
               within_subject_log_sd=within_subject_log_sd,
               coefficient_of_variation=coefficient_of_variation,
               lower_boundary=lower_boundary, upper_boundary=upper_boundary,
               alpha=alpha, power=power, max_iterations=max_iterations)


MARGIN_PROCEDURES: dict[str, Callable[..., dict[str, Any]]] = {
    "MARGIN-001.SAMPLE_SIZE": independent_mean_noninferiority,
    "MARGIN-002.SAMPLE_SIZE": paired_mean_noninferiority,
    "MARGIN-003.SAMPLE_SIZE": independent_proportion_noninferiority_fm,
    "MARGIN-004.SAMPLE_SIZE": independent_proportion_noninferiority_simple,
    "MARGIN-005.SAMPLE_SIZE": paired_proportion_noninferiority,
    "MARGIN-006.SAMPLE_SIZE": hazard_ratio_noninferiority,
    "MARGIN-007.SAMPLE_SIZE": independent_mean_equivalence,
    "MARGIN-008.SAMPLE_SIZE": paired_mean_equivalence,
    "MARGIN-009.SAMPLE_SIZE": independent_proportion_equivalence_fm,
    "MARGIN-010.SAMPLE_SIZE": independent_proportion_equivalence_simple,
    "MARGIN-011.SAMPLE_SIZE": paired_proportion_equivalence,
    "MARGIN-012.SAMPLE_SIZE": hazard_ratio_equivalence,
    "MARGIN-013.SAMPLE_SIZE": crossover_bioequivalence_ratio_one,
    "MARGIN-014.SAMPLE_SIZE": crossover_bioequivalence_ratio_not_one,
}
