"""Chapter 8 paired binary, ordinal, and continuous calculations."""

from __future__ import annotations

from math import ceil, isclose, isfinite, sqrt
from typing import Any, Sequence

from scipy.optimize import brentq
from scipy.stats import nct, t

from .distributions import critical_values
from .schema_contract import contracted, consume_quantity, correction_lineage


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than 0")
    return value


def _probability(name: str, value: float, *, strict: bool = True) -> float:
    value = float(value)
    valid = 0 < value < 1 if strict else 0 <= value <= 1
    if not isfinite(value) or not valid:
        interval = "(0, 1)" if strict else "[0, 1]"
        raise ValueError(f"{name} must be a finite probability in {interval}")
    return value


def _pair_result(method_id: str, reference: str, inputs: dict[str, Any], raw_pairs: float,
                 *, subjects_per_pair: int = 1, even_sequence: bool = False,
                 extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isfinite(raw_pairs) or raw_pairs <= 0:
        raise ValueError("inputs do not produce a positive finite pair count")
    if isinstance(subjects_per_pair, bool) or not isinstance(subjects_per_pair, int) or subjects_per_pair < 1:
        raise ValueError("subjects_per_pair must be a positive integer")
    rounded_pairs = ceil(raw_pairs)
    final_pairs = rounded_pairs + (1 if even_sequence and rounded_pairs % 2 else 0)
    result: dict[str, Any] = {
        "method_id": method_id,
        "formula_reference": reference,
        "inputs": inputs,
        "raw_total": raw_pairs * subjects_per_pair,
        "raw_pairs": raw_pairs,
        "rounded_pairs": rounded_pairs,
        "constraint_adjusted_pairs": final_pairs,
        "final_pairs": final_pairs,
        "raw_group_control": None,
        "raw_group_treatment": None,
        "rounded_total": rounded_pairs * subjects_per_pair,
        "rounded_group_control": None,
        "rounded_group_treatment": None,
        "final_group_control": None,
        "final_group_treatment": None,
        "final_cases": None,
        "final_controls": None,
        "final_total": final_pairs * subjects_per_pair,
        "subjects_per_pair": subjects_per_pair,
        "rounding_rule": "ceil raw pairs" + ("; then require an even number of sequence assignments" if even_sequence else ""),
        "warnings": [],
        "provenance": None,
    }
    if extra:
        result.update(extra)
    return result


def _discordant_odds(value: float) -> float:
    value = _positive("discordant_odds_ratio", value)
    if value == 1:
        raise ValueError("discordant_odds_ratio must differ from 1 for a finite sample size")
    return value


def mcnemar_direct(*, discordant_odds_ratio: float, discordant_fraction: float,
                   alpha: float = 0.05, power: float = 0.80, sides: int = 2,
                   subjects_per_pair: int = 1, even_sequence: bool = False) -> dict[str, Any]:
    """TWO-023: Connett-Smith-McHugh direct approximation, equation 8.1."""
    psi = _discordant_odds(discordant_odds_ratio)
    fraction = _probability("discordant_fraction", discordant_fraction, strict=False)
    if fraction == 0:
        raise ValueError("discordant_fraction must be greater than 0 for a finite sample size")
    z_alpha, z_power = critical_values(alpha, power, sides)
    radical = (psi + 1) ** 2 - (psi - 1) ** 2 * fraction
    raw_pairs = (z_alpha * (psi + 1) + z_power * sqrt(radical)) ** 2 / (
        (psi - 1) ** 2 * fraction
    )
    return _pair_result("TWO-023", "equation 8.1", {
        "discordant_odds_ratio": psi, "discordant_fraction": fraction,
        "alpha": alpha, "power": power, "sides": sides,
        "subjects_per_pair": subjects_per_pair, "even_sequence": even_sequence,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw_pairs, subjects_per_pair=subjects_per_pair, even_sequence=even_sequence)


def _required_discordant(psi: float, alpha: float, power: float, sides: int) -> tuple[float, float, float]:
    z_alpha, z_power = critical_values(alpha, power, sides)
    raw = (z_alpha * (psi + 1) + 2 * z_power * sqrt(psi)) ** 2 / (psi - 1) ** 2
    return raw, z_alpha, z_power


def discordant_count_conversion(*, discordant_odds_ratio: float, discordant_fraction: float,
                                alpha: float = 0.05, power: float = 0.80,
                                sides: int = 2, subjects_per_pair: int = 1,
                                even_sequence: bool = False) -> dict[str, Any]:
    """TWO-024: equations 8.2--8.4, preserving both raw and staged rounding."""
    psi = _discordant_odds(discordant_odds_ratio)
    fraction = _probability("discordant_fraction", discordant_fraction)
    raw_discordant, z_alpha, z_power = _required_discordant(psi, alpha, power, sides)
    rounded_discordant = ceil(raw_discordant)
    raw_pairs = raw_discordant / fraction
    staged_pairs = rounded_discordant / fraction
    result = _pair_result("TWO-024", "equations 8.2, 8.3 and 8.4", {
        "discordant_odds_ratio": psi, "discordant_fraction": fraction,
        "alpha": alpha, "power": power, "sides": sides,
        "subjects_per_pair": subjects_per_pair, "even_sequence": even_sequence,
        "z_alpha": z_alpha, "z_power": z_power,
    }, staged_pairs, subjects_per_pair=subjects_per_pair, even_sequence=even_sequence, extra={
        "raw_required_discordant_pairs": raw_discordant,
        "rounded_required_discordant_pairs": rounded_discordant,
        "raw_pairs_without_intermediate_rounding": raw_pairs,
        "raw_pairs_after_discordant_ceiling": staged_pairs,
    })
    result["rounding_rule"] = (
        "ceil equation 8.2 discordant pairs; divide by discordant_fraction; ceil pairs"
        + ("; then require even sequence assignments" if even_sequence else "")
    )
    return result


def matched_case_control_correction(*, equal_pair_count: float | None = None,
                                    controls_per_case: int,
                                    parent_result: dict[str, Any] | None = None,
                                    parent_result_key: str = "final_pairs",
                                    parent_stage: str = "final") -> dict[str, Any]:
    """TWO-025: equation 8.5, 1:C matched case-control correction."""
    if parent_result is not None:
        consumed = consume_quantity(
            parent_result, allowed_parent_methods={"TWO-023", "TWO-024"},
            key=parent_result_key, quantity="pairs", unit="pairs", stage=parent_stage,
        )
        parent_value = float(consumed["value"])
        if equal_pair_count is not None and abs(float(equal_pair_count) - parent_value) > 1e-12:
            raise ValueError("equal_pair_count conflicts with the consumed parent quantity")
        equal = _positive("equal_pair_count", parent_value)
    else:
        if equal_pair_count is None:
            raise ValueError("provide equal_pair_count or a typed parent_result")
        equal = _positive("equal_pair_count", equal_pair_count)
        consumed = {
            "key": "equal_pair_count", "value": equal, "quantity": "pairs",
            "unit": "pairs", "stage": "raw",
        }
    if isinstance(controls_per_case, bool) or not isinstance(controls_per_case, int) or controls_per_case < 1:
        raise ValueError("controls_per_case must be a positive integer")
    controls = controls_per_case
    raw_units = equal * (1 + controls) / (2 * controls)
    rounded_units = ceil(raw_units)
    final_cases = rounded_units
    final_controls = controls * rounded_units
    result = {
        "method_id": "TWO-025", "formula_reference": "equation 8.5",
        "inputs": {"equal_pair_count": equal, "controls_per_case": controls},
        "raw_equal_pairs": equal, "raw_matched_units": raw_units,
        "raw_pairs": raw_units, "rounded_pairs": rounded_units,
        "constraint_adjusted_pairs": rounded_units, "final_pairs": rounded_units,
        "raw_cases": raw_units, "raw_controls": controls * raw_units,
        "raw_total": (1 + controls) * raw_units,
        "rounded_total": (1 + controls) * rounded_units,
        "final_cases": final_cases, "final_controls": final_controls,
        "final_total": final_cases + final_controls,
        "raw_group_control": controls * raw_units,
        "raw_group_treatment": raw_units,
        "rounded_group_control": final_controls,
        "rounded_group_treatment": final_cases,
        "final_group_control": final_controls,
        "final_group_treatment": final_cases,
        "rounding_rule": "ceil matched units, then apply the exact 1:C matching block",
        "warnings": [], "provenance": None,
    }
    if parent_result is not None:
        result["lineage"] = correction_lineage(
            parent_result=parent_result,
            consumed=consumed,
            transformation="equation 8.5 conversion from equal matched pairs to a 1:C matched design",
            child_outputs=[
                {"key": "final_cases", "quantity": "participants", "unit": "participants", "stage": "final"},
                {"key": "final_controls", "quantity": "participants", "unit": "participants", "stage": "final"},
                {"key": "final_total", "quantity": "participants", "unit": "participants", "stage": "final"},
            ],
        )
    else:
        result["lineage"] = {
            "calculation_type": "correction",
            "parent_method_id": "EXTERNAL-EQUAL-PAIR-COUNT",
            "consumed_result": consumed,
            "parent_primary_inputs": {"equal_pair_count": equal},
            "parent_inference": {},
            "transformation": "equation 8.5 conversion from equal matched pairs to a 1:C matched design",
            "child_outputs": [
                {"key": "final_total", "quantity": "participants", "unit": "participants", "stage": "final"}
            ],
            "parent_source_provenance": None,
            "parent_validation_evidence": None,
            "warnings": ["legacy scalar parent path; use parent_result for reproducible lineage"],
        }
    return result


def _effect_from_scores(scores: Sequence[float], probabilities: Sequence[float]) -> tuple[float, float, float]:
    score_values = [float(value) for value in scores]
    probability_values = [float(value) for value in probabilities]
    if len(score_values) < 2 or len(score_values) != len(probability_values):
        raise ValueError("difference_scores and conditional_probabilities must have equal length of at least 2")
    if any(not isfinite(value) for value in score_values):
        raise ValueError("difference_scores must be finite")
    if any(not isfinite(value) or value < 0 or value > 1 for value in probability_values):
        raise ValueError("conditional_probabilities must be probabilities in [0, 1]")
    if not isclose(sum(probability_values), 1.0, rel_tol=0.0, abs_tol=1e-8):
        raise ValueError("conditional_probabilities must sum to 1")
    eta = sum(probability * score for probability, score in zip(probability_values, score_values))
    variance = sum(probability * score ** 2 for probability, score in zip(probability_values, score_values)) - eta ** 2
    if variance <= 0 or eta == 0:
        raise ValueError("scores and probabilities must produce nonzero mean and positive variance")
    sigma = sqrt(variance)
    return abs(eta / sigma), eta, sigma


def paired_ordinal_signed_rank(*, standardized_effect: float | None = None,
                               difference_scores: Sequence[float] | None = None,
                               conditional_probabilities: Sequence[float] | None = None,
                               alpha: float = 0.05, power: float = 0.80,
                               sides: int = 2, subjects_per_pair: int = 1,
                               even_sequence: bool = False) -> dict[str, Any]:
    """TWO-026: equations 8.6--8.9."""
    if standardized_effect is not None:
        if difference_scores is not None or conditional_probabilities is not None:
            raise ValueError("provide standardized_effect or score probabilities, not both")
        effect = abs(_positive("standardized_effect", standardized_effect))
        eta = sigma = None
    else:
        if difference_scores is None or conditional_probabilities is None:
            raise ValueError("difference_scores and conditional_probabilities are required together")
        effect, eta, sigma = _effect_from_scores(difference_scores, conditional_probabilities)
    z_alpha, z_power = critical_values(alpha, power, sides)
    raw_pairs = 2 * (z_alpha + z_power) ** 2 / effect ** 2 + 0.5 * z_alpha ** 2
    return _pair_result("TWO-026", "equations 8.6, 8.7, 8.8 and 8.9", {
        "standardized_effect": effect,
        "difference_scores": list(difference_scores) if difference_scores is not None else None,
        "conditional_probabilities": list(conditional_probabilities) if conditional_probabilities is not None else None,
        "alpha": alpha, "power": power, "sides": sides,
        "subjects_per_pair": subjects_per_pair, "even_sequence": even_sequence,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw_pairs, subjects_per_pair=subjects_per_pair, even_sequence=even_sequence, extra={
        "eta_plan": eta, "sigma_discordant": sigma,
    })


def _binary_inputs(positive_differences: float, negative_differences: float,
                   total_pairs: float) -> tuple[float, float]:
    positive = _positive("positive_differences", positive_differences)
    negative = _positive("negative_differences", negative_differences)
    total = _positive("total_pairs", total_pairs)
    if positive + negative > total + 1e-12:
        raise ValueError("positive_differences + negative_differences cannot exceed total_pairs")
    return _discordant_odds(positive / negative), (positive + negative) / total


def paired_ordinal_binary(*, positive_differences: float, negative_differences: float,
                          total_pairs: float, alpha: float = 0.05,
                          power: float = 0.80, sides: int = 2,
                          subjects_per_pair: int = 1,
                          even_sequence: bool = False) -> dict[str, Any]:
    """TWO-027: binary reduction followed by equations 8.2 and 8.4."""
    psi, fraction = _binary_inputs(positive_differences, negative_differences, total_pairs)
    base = discordant_count_conversion(
        discordant_odds_ratio=psi, discordant_fraction=fraction, alpha=alpha,
        power=power, sides=sides, subjects_per_pair=subjects_per_pair,
        even_sequence=even_sequence,
    )
    base["method_id"] = "TWO-027"
    base["formula_reference"] = "binary reduction with equations 8.2 and 8.4"
    base["inputs"].update({
        "positive_differences": positive_differences,
        "negative_differences": negative_differences,
        "total_pairs": total_pairs,
    })
    return base


def paired_ordinal_compromise(*, positive_differences: float, negative_differences: float,
                              total_pairs: float, alpha: float = 0.05,
                              power: float = 0.80, sides: int = 2,
                              subjects_per_pair: int = 1,
                              even_sequence: bool = False) -> dict[str, Any]:
    """TWO-028: arithmetic compromise between discordant and binary pair counts."""
    psi, fraction = _binary_inputs(positive_differences, negative_differences, total_pairs)
    raw_discordant, z_alpha, z_power = _required_discordant(psi, alpha, power, sides)
    raw_binary_pairs = raw_discordant / fraction
    raw_pairs = (raw_discordant + raw_binary_pairs) / 2
    return _pair_result("TWO-028", "Chapter 8 ordinal pragmatic compromise", {
        "positive_differences": positive_differences,
        "negative_differences": negative_differences,
        "total_pairs": total_pairs,
        "discordant_odds_ratio": psi, "discordant_fraction": fraction,
        "alpha": alpha, "power": power, "sides": sides,
        "subjects_per_pair": subjects_per_pair, "even_sequence": even_sequence,
        "z_alpha": z_alpha, "z_power": z_power,
    }, raw_pairs, subjects_per_pair=subjects_per_pair, even_sequence=even_sequence, extra={
        "raw_required_discordant_pairs": raw_discordant,
        "raw_binary_pair_estimate": raw_binary_pairs,
    })


def paired_continuous_normal(*, standardized_effect: float, alpha: float = 0.05,
                             power: float = 0.80, sides: int = 2,
                             subjects_per_pair: int = 1,
                             even_sequence: bool = False) -> dict[str, Any]:
    """TWO-029: equation 8.12 normal/Guenther approximation."""
    effect = abs(_positive("standardized_effect", standardized_effect))
    z_alpha, z_power = critical_values(alpha, power, sides)
    raw_pairs = 2 * (z_alpha + z_power) ** 2 / effect ** 2 + 0.5 * z_alpha ** 2
    return _pair_result("TWO-029", "equation 8.12", {
        "standardized_effect": effect, "alpha": alpha, "power": power,
        "sides": sides, "subjects_per_pair": subjects_per_pair,
        "even_sequence": even_sequence, "z_alpha": z_alpha, "z_power": z_power,
    }, raw_pairs, subjects_per_pair=subjects_per_pair, even_sequence=even_sequence)


def _paired_t_power(pair_count: float, effect: float, alpha: float, sides: int) -> float:
    degrees = pair_count - 1
    if degrees <= 0:
        return 0.0
    noncentrality = effect * sqrt(pair_count / 2)
    if sides == 2:
        critical = t.ppf(1 - alpha / 2, degrees)
        return float(nct.cdf(-critical, degrees, noncentrality) + nct.sf(critical, degrees, noncentrality))
    critical = t.ppf(1 - alpha, degrees)
    return float(nct.sf(critical, degrees, noncentrality))


def paired_continuous_t(*, standardized_effect: float, alpha: float = 0.05,
                        power: float = 0.80, sides: int = 2,
                        subjects_per_pair: int = 1,
                        even_sequence: bool = False,
                        search_limit: int = 1_000_000_000) -> dict[str, Any]:
    """TWO-030: invert noncentral-t power with df=N_pairs-1."""
    effect = abs(_positive("standardized_effect", standardized_effect))
    critical_values(alpha, power, sides)
    if isinstance(search_limit, bool) or not isinstance(search_limit, int) or search_limit < 2:
        raise ValueError("search_limit must be an integer of at least 2")
    lower, upper = 2.0, 4.0
    evaluations = 1
    while _paired_t_power(upper, effect, alpha, sides) < power:
        upper *= 2
        evaluations += 1
        if upper > search_limit:
            raise ValueError("target power requires pairs beyond search_limit")
    raw_pairs = brentq(
        lambda count: _paired_t_power(count, effect, alpha, sides) - power,
        lower, upper, xtol=1e-10,
    )
    rounded = ceil(raw_pairs)
    candidate = rounded + (1 if even_sequence and rounded % 2 else 0)
    while _paired_t_power(candidate, effect, alpha, sides) < power:
        candidate += 2 if even_sequence else 1
        evaluations += 1
    result = _pair_result("TWO-030", "noncentral-t inversion following equation 8.12", {
        "standardized_effect": effect, "alpha": alpha, "power": power,
        "sides": sides, "subjects_per_pair": subjects_per_pair,
        "even_sequence": even_sequence, "search_limit": search_limit,
    }, raw_pairs, subjects_per_pair=subjects_per_pair, even_sequence=even_sequence, extra={
        "search_lower": 2.0, "search_upper": upper, "root_tolerance": 1e-10,
        "converged": True, "function_evaluations_at_least": evaluations,
        "degrees_of_freedom": candidate - 1,
        "noncentrality": effect * sqrt(candidate / 2),
        "achieved_power": _paired_t_power(candidate, effect, alpha, sides),
        "previous_feasible_power": _paired_t_power(candidate - (2 if even_sequence else 1), effect, alpha, sides),
    })
    result["constraint_adjusted_pairs"] = candidate
    result["final_pairs"] = candidate
    result["final_total"] = candidate * subjects_per_pair
    result["rounding_rule"] = "continuous noncentral-t root; smallest integer" + (" even" if even_sequence else "") + " pair count attaining target power"
    return result


mcnemar_direct = contracted(mcnemar_direct)
discordant_count_conversion = contracted(discordant_count_conversion)
matched_case_control_correction = contracted(matched_case_control_correction)
paired_ordinal_signed_rank = contracted(paired_ordinal_signed_rank)
paired_ordinal_binary = contracted(paired_ordinal_binary)
paired_ordinal_compromise = contracted(paired_ordinal_compromise)
paired_continuous_normal = contracted(paired_continuous_normal)
paired_continuous_t = contracted(paired_continuous_t)
