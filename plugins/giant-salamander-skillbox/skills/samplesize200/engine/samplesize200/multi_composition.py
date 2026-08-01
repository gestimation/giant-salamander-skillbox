"""Outcome-agnostic multi-arm compositions over validated two-group engines.

This module contains no outcome sample-size formula.  Each public function
calls an existing contracted two-group engine and only performs prespecified
pair enumeration, limiting-requirement selection, and design integerization.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations
from math import ceil, isfinite, sqrt
from typing import Any, Callable, Sequence

from .schema_contract import consume_quantity


ParentBuilder = Callable[..., dict[str, Any]]


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than 0")
    return value


def _probability(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be a finite probability in [0, 1]")
    return value


def _event_probability(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 < value <= 1:
        raise ValueError(f"{name} must be a finite probability in (0, 1]")
    return value


def _count(name: str, value: int, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _numeric_list(name: str, values: Sequence[float], minimum_length: int = 3) -> list[float]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{name} must be an array")
    result = [float(value) for value in values]
    if len(result) < minimum_length or any(not isfinite(value) for value in result):
        raise ValueError(f"{name} must contain at least {minimum_length} finite values")
    return result


def _category_distribution(name: str, values: Sequence[float]) -> list[float]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{name} must be an array")
    probabilities = [_probability(f"{name}[{j}]", value) for j, value in enumerate(values)]
    if len(probabilities) < 2 or abs(sum(probabilities) - 1.0) > 1e-8:
        raise ValueError(f"{name} must contain at least two probabilities summing to 1")
    return probabilities


def _category_arms(name: str, values: Sequence[Sequence[float]]) -> list[list[float]]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or len(values) < 3:
        raise ValueError(f"{name} must contain at least three arm distributions")
    arms: list[list[float]] = []
    category_count: int | None = None
    for index, arm in enumerate(values):
        probabilities = _category_distribution(f"{name}[{index}]", arm)
        if category_count is None:
            category_count = len(probabilities)
        elif len(probabilities) != category_count:
            raise ValueError(f"all {name} distributions must have the same number of categories")
        arms.append(probabilities)
    return arms


def _parent_requirement(parent: dict[str, Any], expected_method: str) -> dict[str, Any]:
    raw = consume_quantity(
        parent, allowed_parent_methods={expected_method}, key="raw_total",
        quantity="participants", unit="participants", stage="raw",
    )
    final_control = consume_quantity(
        parent, allowed_parent_methods={expected_method}, key="final_group_control",
        quantity="participants", unit="participants", stage="allocation_adjusted",
    )
    final_treatment = consume_quantity(
        parent, allowed_parent_methods={expected_method}, key="final_group_treatment",
        quantity="participants", unit="participants", stage="allocation_adjusted",
    )
    final_total = consume_quantity(
        parent, allowed_parent_methods={expected_method}, key="final_total",
        quantity="participants", unit="participants", stage="final",
    )
    return {
        "parent_method_id": expected_method,
        "parent_inputs": dict(parent.get("inputs", {})),
        "raw_total": float(raw["value"]),
        "final_group_control": int(final_control["value"]),
        "final_group_treatment": int(final_treatment["value"]),
        "final_total": int(final_total["value"]),
        "parent_warnings": list(parent.get("warnings", [])),
        "parent_source_provenance": parent.get("source_provenance"),
        "parent_validation_evidence": parent.get("validation_evidence"),
    }


def _quantities(raw_total: float, final_groups: Sequence[int]) -> list[dict[str, Any]]:
    final_total = sum(final_groups)
    records: list[dict[str, Any]] = [
        {"key": "raw_total", "value": raw_total, "quantity": "participants", "unit": "participants", "stage": "raw"},
        {"key": "rounded_total", "value": ceil(raw_total), "quantity": "participants", "unit": "participants", "stage": "rounded"},
    ]
    records.extend(
        {"key": f"final_group_{index + 1}", "value": value,
         "quantity": "participants", "unit": "participants", "stage": "allocation_adjusted"}
        for index, value in enumerate(final_groups)
    )
    records.append(
        {"key": "final_total", "value": final_total,
         "quantity": "participants", "unit": "participants", "stage": "final"}
    )
    return records


def _composition_result(*, method_id: str, formula_reference: str,
                        inputs: dict[str, Any], raw_total: float,
                        final_groups: Sequence[int], lineage: list[dict[str, Any]],
                        extra: dict[str, Any]) -> dict[str, Any]:
    groups = [int(value) for value in final_groups]
    quantities = _quantities(raw_total, groups)
    parent_sources = [item.get("parent_source_provenance") for item in lineage if item.get("parent_source_provenance")]
    parent_evidence = [item.get("parent_validation_evidence") for item in lineage if item.get("parent_validation_evidence")]
    result: dict[str, Any] = {
        "method_id": method_id,
        "formula_reference": formula_reference,
        "inputs": inputs,
        "raw_total": raw_total,
        "rounded_total": ceil(raw_total),
        "final_total": sum(groups),
        "final_group_sizes": groups,
        "quantities": quantities,
        "warnings": [],
        "source_provenance": {
            "design_source": "Chapter 14 multi-arm reconstruction",
            "calculation_source": "validated two-group parent engine",
            "parent_sources": parent_sources,
        },
        "validation_evidence": {
            "scope": "composition logic and inherited validated parent calculations",
            "input_match_claim": False,
            "parent_validation_evidence": parent_evidence,
        },
        "procedure_lineage": lineage,
        "implementation_kind": "wrapper",
    }
    result.update(extra)
    return result


def _all_pair_max(*, method_id: str, arm_count: int, alpha: float, power: float,
                  sides: int, multiplicity: str, build_parent: ParentBuilder,
                  expected_parent: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if multiplicity not in {"none", "bonferroni"}:
        raise ValueError("multiplicity must be 'none' or 'bonferroni'")
    comparison_count = arm_count * (arm_count - 1) // 2
    adjusted_alpha = float(alpha) / comparison_count if multiplicity == "bonferroni" else float(alpha)
    rows: list[dict[str, Any]] = []
    lineage: list[dict[str, Any]] = []
    for left, right in combinations(range(arm_count), 2):
        parent = build_parent(left, right, adjusted_alpha, power, sides)
        requirement = _parent_requirement(parent, expected_parent)
        if requirement["final_group_control"] != requirement["final_group_treatment"]:
            raise ValueError("all-pair parent must return equal groups when allocation_ratio=1")
        row = {
            "arm_i": left + 1,
            "arm_j": right + 1,
            "raw_pair_total": requirement["raw_total"],
            "final_pair_total": requirement["final_total"],
            "final_per_arm": requirement["final_group_control"],
            **requirement,
        }
        rows.append(row)
        lineage.append({
            "role": "pairwise_parent_calculation",
            "arm_i": left + 1, "arm_j": right + 1,
            "parent_method_id": expected_parent,
            "consumed_keys": sorted(requirement["parent_inputs"]),
            "produced_key": "raw_pair_total",
            "parent_source_provenance": requirement["parent_source_provenance"],
            "parent_validation_evidence": requirement["parent_validation_evidence"],
        })
    limiting = max(rows, key=lambda item: item["raw_pair_total"])
    finalizing = max(rows, key=lambda item: item["final_per_arm"])
    final_per_arm = int(finalizing["final_per_arm"])
    raw_total = arm_count * float(limiting["raw_pair_total"]) / 2.0
    final_groups = [final_per_arm] * arm_count
    lineage.extend([
        {"role": "multiplicity", "component_id": "COMP-BONFERRONI",
         "applied": multiplicity == "bonferroni", "comparison_count": comparison_count},
        {"role": "equal_arm_reconstruction", "component_id": "COMP-MULTI-EQUAL-ARM",
         "produced_key": "final_total"},
    ])
    return _composition_result(
        method_id=method_id,
        formula_reference=f"all-pair maximum composition over {expected_parent}",
        inputs={**inputs, "alpha": alpha, "adjusted_alpha": adjusted_alpha,
                "power": power, "sides": sides, "multiplicity": multiplicity,
                "comparison_count": comparison_count, "allocation_ratio": 1.0},
        raw_total=raw_total, final_groups=final_groups, lineage=lineage,
        extra={
            "pairwise_results": rows,
            "limiting_pair": {key: limiting[key] for key in ("arm_i", "arm_j", "raw_pair_total")},
            "finalizing_pair": {key: finalizing[key] for key in ("arm_i", "arm_j", "final_per_arm")},
            "final_participants_per_arm": final_per_arm,
            "rounding_rule": "ceil each validated equal-allocation parent per arm; use the maximum for every arm",
        },
    )


def _shared_block(number_of_treatment_arms: int,
                  allocation_block: list[int] | None) -> tuple[list[int], float, float]:
    q = _count("number_of_treatment_arms", number_of_treatment_arms, 2)
    target_phi = 1.0 / sqrt(q)
    if allocation_block is None:
        root = Fraction(sqrt(q)).limit_denominator(20)
        block = [root.numerator] + [root.denominator] * q
        calculation_phi = target_phi
    else:
        if (not isinstance(allocation_block, list) or len(allocation_block) != q + 1
                or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0
                       for value in allocation_block)):
            raise ValueError("allocation_block must contain one positive integer for reference and one per treatment")
        if len(set(allocation_block[1:])) != 1:
            raise ValueError("all treatment entries in allocation_block must be equal")
        block = list(allocation_block)
        calculation_phi = block[1] / block[0]
    return block, target_phi, calculation_phi


def _shared_reference(*, method_id: str, number_of_treatment_arms: int,
                      allocation_block: list[int] | None, alpha: float, power: float,
                      build_parent: Callable[[float, float, float], dict[str, Any]],
                      expected_parent: str, inputs: dict[str, Any]) -> dict[str, Any]:
    q = _count("number_of_treatment_arms", number_of_treatment_arms, 2)
    block, target_phi, phi = _shared_block(q, allocation_block)
    final_phi = block[1] / block[0]
    parent = build_parent(phi, alpha, power)
    requirement = _parent_requirement(parent, expected_parent)
    raw_pair = requirement["raw_total"]
    raw_reference = raw_pair / (1.0 + phi)
    raw_treatment = phi * raw_reference
    blocks = ceil(max(raw_reference / block[0], raw_treatment / block[1]))
    groups = [blocks * value for value in block]
    raw_total = raw_reference + q * raw_treatment
    lineage = [{
        "role": "limiting_treatment_reference_parent",
        "parent_method_id": expected_parent,
        "consumed_keys": sorted(requirement["parent_inputs"]),
        "produced_key": "raw_two_group_total",
        "parent_source_provenance": requirement["parent_source_provenance"],
        "parent_validation_evidence": requirement["parent_validation_evidence"],
    }, {
        "role": "shared_reference_reconstruction",
        "component_id": "COMP-SHARED-REFERENCE-RECONSTRUCTION",
        "consumed_key": "raw_two_group_total", "produced_key": "final_total",
    }]
    result = _composition_result(
        method_id=method_id,
        formula_reference=f"shared-reference composition over {expected_parent}",
        inputs={**inputs, "number_of_treatment_arms": q, "alpha": alpha,
                "alpha_semantics": "one-sided per treatment-reference comparison",
                "power": power, "sides": 1, "target_allocation_ratio": target_phi,
                "calculation_allocation_ratio": phi,
                "final_allocation_ratio": final_phi, "allocation_block": block},
        raw_total=raw_total, final_groups=groups, lineage=lineage,
        extra={
            "raw_two_group_total": raw_pair,
            "raw_reference_participants": raw_reference,
            "raw_treatment_participants_per_arm": raw_treatment,
            "final_reference_participants": groups[0],
            "final_treatment_participants": groups[1:],
            "rounding_rule": "round upward to a complete shared-reference allocation block",
            "parent_requirement": requirement,
        },
    )
    if allocation_block is None and abs(final_phi - target_phi) > 1e-8:
        result["warnings"].append({
            "code": "INTEGER_BLOCK_APPROXIMATION",
            "message": "the final integer allocation block approximates the square-root target; each arm is rounded upward from the target-ratio parent requirement",
            "target_allocation_ratio": target_phi,
            "final_allocation_ratio": final_phi,
        })
    elif abs(phi - target_phi) > 1e-8:
        result["warnings"].append({
            "code": "ALLOCATION_BLOCK_APPROXIMATION",
            "message": "the integer allocation block differs from the square-root target; the parent calculation uses the explicit block ratio",
            "target_allocation_ratio": target_phi,
            "calculation_allocation_ratio": phi,
        })
    return result


def _compatible(left: float | Sequence[float], right: float | Sequence[float]) -> bool:
    if isinstance(left, Sequence) and not isinstance(left, (str, bytes)):
        if not isinstance(right, Sequence) or isinstance(right, (str, bytes)) or len(left) != len(right):
            return False
        return all(abs(float(a) - float(b)) <= 1e-8 for a, b in zip(left, right))
    return abs(float(left) - float(right)) <= 1e-8


def _factorial(*, method_id: str, parent_a: dict[str, Any], parent_b: dict[str, Any],
               expected_parent: str, inputs: dict[str, Any],
               compatibility_a: float | Sequence[float],
               compatibility_b: float | Sequence[float]) -> dict[str, Any]:
    if not _compatible(compatibility_a, compatibility_b):
        raise ValueError("INCOMPATIBLE_FACTOR_MARGINS: A and B margins do not describe one balanced 2x2 population")
    requirement_a = _parent_requirement(parent_a, expected_parent)
    requirement_b = _parent_requirement(parent_b, expected_parent)
    raw_a = requirement_a["raw_total"]
    raw_b = requirement_b["raw_total"]
    limiting_raw = max(raw_a, raw_b)
    parent_feasible = max(requirement_a["final_total"], requirement_b["final_total"])
    final_total = ceil(parent_feasible / 4) * 4
    groups = [final_total // 4] * 4
    lineage = []
    for factor, requirement in (("A", requirement_a), ("B", requirement_b)):
        lineage.append({
            "role": f"factor_{factor.lower()}_main_effect",
            "factor": factor, "parent_method_id": expected_parent,
            "consumed_keys": sorted(requirement["parent_inputs"]),
            "produced_key": f"raw_factor_{factor.lower()}_total",
            "parent_source_provenance": requirement["parent_source_provenance"],
            "parent_validation_evidence": requirement["parent_validation_evidence"],
        })
    lineage.append({
        "role": "four_cell_divisibility", "component_id": "COMP-FOUR-CELL-DIVISIBILITY",
        "consumed_key": "parent_feasible_total", "produced_key": "final_total",
    })
    return _composition_result(
        method_id=method_id,
        formula_reference=f"balanced 2x2 factorial main-effect composition over {expected_parent}",
        inputs={**inputs, "allocation_ratio": 1.0,
                "factor_a_compatibility_margin": compatibility_a,
                "factor_b_compatibility_margin": compatibility_b},
        raw_total=limiting_raw, final_groups=groups, lineage=lineage,
        extra={
            "raw_factor_a_total": raw_a, "raw_factor_b_total": raw_b,
            "factor_a_parent_final_total": requirement_a["final_total"],
            "factor_b_parent_final_total": requirement_b["final_total"],
            "parent_feasible_total": parent_feasible,
            "limiting_factor": "A" if raw_a >= raw_b else "B",
            "factor_requirements": {"A": requirement_a, "B": requirement_b},
            "final_cell_sizes": {"A0B0": groups[0], "A0B1": groups[1],
                                 "A1B0": groups[2], "A1B1": groups[3]},
            "rounding_rule": "honor both parent final totals, then round upward to four equal cells",
        },
    )


def multi_all_pair_continuous(*, arm_means: Sequence[float], standard_deviation: float,
                              alpha: float = 0.05, power: float = 0.80,
                              sides: int = 2, multiplicity: str = "none") -> dict[str, Any]:
    from .continuous import two_sample_mean_guenther
    means = _numeric_list("arm_means", arm_means)
    if len(set(means)) != len(means):
        raise ValueError("all arm_means must differ because every pair is prespecified")
    sd = _positive("standard_deviation", standard_deviation)
    return _all_pair_max(
        method_id="MULTI-007", arm_count=len(means), alpha=alpha, power=power,
        sides=sides, multiplicity=multiplicity, expected_parent="TWO-009",
        inputs={"arm_means": means, "standard_deviation": sd},
        build_parent=lambda i, j, a, p, s: two_sample_mean_guenther(
            standardized_effect=abs(means[j] - means[i]) / sd,
            allocation_ratio=1.0, alpha=a, power=p, sides=s),
    )


def multi_all_pair_ordinal(*, arm_category_proportions: Sequence[Sequence[float]],
                           alpha: float = 0.05, power: float = 0.80,
                           sides: int = 2, multiplicity: str = "none") -> dict[str, Any]:
    from .ordinal import mann_whitney_nonproportional
    arms = _category_arms("arm_category_proportions", arm_category_proportions)
    return _all_pair_max(
        method_id="MULTI-008", arm_count=len(arms), alpha=alpha, power=power,
        sides=sides, multiplicity=multiplicity, expected_parent="TWO-007",
        inputs={"arm_category_proportions": arms},
        build_parent=lambda i, j, a, p, s: mann_whitney_nonproportional(
            standard_proportions=arms[i], treatment_proportions=arms[j],
            allocation_ratio=1.0, alpha=a, power=p, sides=s),
    )


def multi_all_pair_poisson(*, arm_rates: Sequence[float], exposure_per_subject: float = 1.0,
                           alpha: float = 0.05, power: float = 0.80,
                           sides: int = 2, multiplicity: str = "none") -> dict[str, Any]:
    from .rates import two_group_poisson_rates
    rates = [_positive(f"arm_rates[{i}]", value) for i, value in enumerate(_numeric_list("arm_rates", arm_rates))]
    if len(set(rates)) != len(rates):
        raise ValueError("all arm_rates must differ because every pair is prespecified")
    exposure = _positive("exposure_per_subject", exposure_per_subject)
    return _all_pair_max(
        method_id="MULTI-009", arm_count=len(rates), alpha=alpha, power=power,
        sides=sides, multiplicity=multiplicity, expected_parent="TWO-013",
        inputs={"arm_rates": rates, "exposure_per_subject": exposure},
        build_parent=lambda i, j, a, p, s: two_group_poisson_rates(
            standard_rate=rates[i], treatment_rate=rates[j], allocation_ratio=1.0,
            exposure_per_subject=exposure, alpha=a, power=p, sides=s,
            number_of_reactions=1),
    )


def multi_all_pair_negative_binomial(*, arm_rates: Sequence[float], overdispersion: float,
                                     mean_exposure: float, alpha: float = 0.05,
                                     power: float = 0.80, sides: int = 2,
                                     multiplicity: str = "none") -> dict[str, Any]:
    from .rates import two_group_negative_binomial_rates
    rates = [_positive(f"arm_rates[{i}]", value) for i, value in enumerate(_numeric_list("arm_rates", arm_rates))]
    if len(set(rates)) != len(rates):
        raise ValueError("all arm_rates must differ because every pair is prespecified")
    dispersion = float(overdispersion)
    if not isfinite(dispersion) or dispersion < 0:
        raise ValueError("overdispersion must be finite and >= 0")
    exposure = _positive("mean_exposure", mean_exposure)
    return _all_pair_max(
        method_id="MULTI-010", arm_count=len(rates), alpha=alpha, power=power,
        sides=sides, multiplicity=multiplicity, expected_parent="TWO-014",
        inputs={"arm_rates": rates, "overdispersion": dispersion, "mean_exposure": exposure},
        build_parent=lambda i, j, a, p, s: two_group_negative_binomial_rates(
            standard_rate=rates[i], treatment_rate=rates[j], overdispersion=dispersion,
            mean_exposure=exposure, allocation_ratio=1.0,
            alpha=a, power=p, sides=s, number_of_reactions=1),
    )


def multi_shared_reference_ordinal(*, reference_proportions: Sequence[float],
                                   least_favorable_odds_ratio: float,
                                   number_of_treatment_arms: int,
                                   alpha: float = 0.05, power: float = 0.80,
                                   allocation_block: list[int] | None = None) -> dict[str, Any]:
    from .ordinal import proportional_odds
    reference = _category_distribution("reference_proportions", reference_proportions)
    odds_ratio = _positive("least_favorable_odds_ratio", least_favorable_odds_ratio)
    if odds_ratio == 1:
        raise ValueError("least_favorable_odds_ratio must differ from 1")
    return _shared_reference(
        method_id="MULTI-011", number_of_treatment_arms=number_of_treatment_arms,
        allocation_block=allocation_block, alpha=alpha, power=power,
        expected_parent="TWO-004",
        inputs={"reference_proportions": reference,
                "least_favorable_odds_ratio": odds_ratio},
        build_parent=lambda phi, a, p: proportional_odds(
            control_proportions=reference, odds_ratio=odds_ratio,
            allocation_ratio=phi, alpha=a, power=p, sides=1),
    )


def multi_shared_reference_poisson(*, reference_rate: float,
                                   number_of_treatment_arms: int,
                                   least_favorable_treatment_rate: float | None = None,
                                   least_favorable_rate_ratio: float | None = None,
                                   exposure_per_subject: float = 1.0,
                                   alpha: float = 0.05, power: float = 0.80,
                                   allocation_block: list[int] | None = None) -> dict[str, Any]:
    from .rates import two_group_poisson_rates
    reference = _positive("reference_rate", reference_rate)
    exposure = _positive("exposure_per_subject", exposure_per_subject)
    return _shared_reference(
        method_id="MULTI-012", number_of_treatment_arms=number_of_treatment_arms,
        allocation_block=allocation_block, alpha=alpha, power=power,
        expected_parent="TWO-013",
        inputs={"reference_rate": reference,
                "least_favorable_treatment_rate": least_favorable_treatment_rate,
                "least_favorable_rate_ratio": least_favorable_rate_ratio,
                "exposure_per_subject": exposure},
        build_parent=lambda phi, a, p: two_group_poisson_rates(
            standard_rate=reference, treatment_rate=least_favorable_treatment_rate,
            rate_ratio=least_favorable_rate_ratio, allocation_ratio=phi,
            exposure_per_subject=exposure, alpha=a, power=p, sides=1,
            number_of_reactions=1),
    )


def multi_shared_reference_negative_binomial(*, reference_rate: float,
                                             least_favorable_treatment_rate: float,
                                             number_of_treatment_arms: int,
                                             overdispersion: float, mean_exposure: float,
                                             alpha: float = 0.05, power: float = 0.80,
                                             allocation_block: list[int] | None = None) -> dict[str, Any]:
    from .rates import two_group_negative_binomial_rates
    reference = _positive("reference_rate", reference_rate)
    treatment = _positive("least_favorable_treatment_rate", least_favorable_treatment_rate)
    dispersion = float(overdispersion)
    if not isfinite(dispersion) or dispersion < 0:
        raise ValueError("overdispersion must be finite and >= 0")
    exposure = _positive("mean_exposure", mean_exposure)
    return _shared_reference(
        method_id="MULTI-013", number_of_treatment_arms=number_of_treatment_arms,
        allocation_block=allocation_block, alpha=alpha, power=power,
        expected_parent="TWO-014",
        inputs={"reference_rate": reference,
                "least_favorable_treatment_rate": treatment,
                "overdispersion": dispersion, "mean_exposure": exposure},
        build_parent=lambda phi, a, p: two_group_negative_binomial_rates(
            standard_rate=reference, treatment_rate=treatment,
            overdispersion=dispersion, mean_exposure=exposure,
            allocation_ratio=phi, alpha=a, power=p, sides=1,
            number_of_reactions=1),
    )


def multi_factorial_binary_proportions(*,
                                       factor_a_control_proportion: float,
                                       factor_a_treatment_proportion: float,
                                       factor_b_control_proportion: float,
                                       factor_b_treatment_proportion: float,
                                       alpha_a: float = 0.05, power_a: float = 0.90,
                                       alpha_b: float = 0.05, power_b: float = 0.90,
                                       sides: int = 2) -> dict[str, Any]:
    from .binary import two_sample_proportions
    values = {name: _probability(name, value) for name, value in {
        "factor_a_control_proportion": factor_a_control_proportion,
        "factor_a_treatment_proportion": factor_a_treatment_proportion,
        "factor_b_control_proportion": factor_b_control_proportion,
        "factor_b_treatment_proportion": factor_b_treatment_proportion,
    }.items()}
    parent_a = two_sample_proportions(
        control_proportion=values["factor_a_control_proportion"],
        treatment_proportion=values["factor_a_treatment_proportion"], allocation_ratio=1.0,
        alpha=alpha_a, power=power_a, sides=sides)
    parent_b = two_sample_proportions(
        control_proportion=values["factor_b_control_proportion"],
        treatment_proportion=values["factor_b_treatment_proportion"], allocation_ratio=1.0,
        alpha=alpha_b, power=power_b, sides=sides)
    return _factorial(
        method_id="MULTI-014", parent_a=parent_a, parent_b=parent_b,
        expected_parent="TWO-001",
        inputs={**values, "alpha_a": alpha_a, "power_a": power_a,
                "alpha_b": alpha_b, "power_b": power_b, "sides": sides},
        compatibility_a=(values["factor_a_control_proportion"] + values["factor_a_treatment_proportion"]) / 2,
        compatibility_b=(values["factor_b_control_proportion"] + values["factor_b_treatment_proportion"]) / 2,
    )


def multi_factorial_binary_odds_ratio(*,
                                      factor_a_control_proportion: float,
                                      factor_a_odds_ratio: float,
                                      factor_b_control_proportion: float,
                                      factor_b_odds_ratio: float,
                                      alpha_a: float = 0.05, power_a: float = 0.90,
                                      alpha_b: float = 0.05, power_b: float = 0.90,
                                      sides: int = 2) -> dict[str, Any]:
    from .binary import two_sample_odds_ratio
    a_control = _probability("factor_a_control_proportion", factor_a_control_proportion)
    b_control = _probability("factor_b_control_proportion", factor_b_control_proportion)
    parent_a = two_sample_odds_ratio(
        control_proportion=a_control, odds_ratio=factor_a_odds_ratio,
        allocation_ratio=1.0, alpha=alpha_a, power=power_a, sides=sides)
    parent_b = two_sample_odds_ratio(
        control_proportion=b_control, odds_ratio=factor_b_odds_ratio,
        allocation_ratio=1.0, alpha=alpha_b, power=power_b, sides=sides)
    a_treatment = float(parent_a["inputs"]["treatment_proportion"])
    b_treatment = float(parent_b["inputs"]["treatment_proportion"])
    return _factorial(
        method_id="MULTI-015", parent_a=parent_a, parent_b=parent_b,
        expected_parent="TWO-002",
        inputs={"factor_a_control_proportion": a_control,
                "factor_a_odds_ratio": factor_a_odds_ratio,
                "factor_b_control_proportion": b_control,
                "factor_b_odds_ratio": factor_b_odds_ratio,
                "alpha_a": alpha_a, "power_a": power_a,
                "alpha_b": alpha_b, "power_b": power_b, "sides": sides},
        compatibility_a=(a_control + a_treatment) / 2,
        compatibility_b=(b_control + b_treatment) / 2,
    )


def multi_factorial_ordinal(*,
                            factor_a_control_proportions: Sequence[float],
                            factor_a_odds_ratio: float,
                            factor_b_control_proportions: Sequence[float],
                            factor_b_odds_ratio: float,
                            alpha_a: float = 0.05, power_a: float = 0.90,
                            alpha_b: float = 0.05, power_b: float = 0.90,
                            sides: int = 2) -> dict[str, Any]:
    from .ordinal import proportional_odds
    a_control = _category_distribution("factor_a_control_proportions", factor_a_control_proportions)
    b_control = _category_distribution("factor_b_control_proportions", factor_b_control_proportions)
    if len(a_control) != len(b_control):
        raise ValueError("factor A and B ordinal distributions must have the same categories")
    parent_a = proportional_odds(
        control_proportions=a_control, odds_ratio=factor_a_odds_ratio,
        allocation_ratio=1.0, alpha=alpha_a, power=power_a, sides=sides)
    parent_b = proportional_odds(
        control_proportions=b_control, odds_ratio=factor_b_odds_ratio,
        allocation_ratio=1.0, alpha=alpha_b, power=power_b, sides=sides)
    a_treatment = parent_a["derived_treatment_proportions"]
    b_treatment = parent_b["derived_treatment_proportions"]
    return _factorial(
        method_id="MULTI-016", parent_a=parent_a, parent_b=parent_b,
        expected_parent="TWO-004",
        inputs={"factor_a_control_proportions": a_control,
                "factor_a_odds_ratio": factor_a_odds_ratio,
                "factor_b_control_proportions": b_control,
                "factor_b_odds_ratio": factor_b_odds_ratio,
                "alpha_a": alpha_a, "power_a": power_a,
                "alpha_b": alpha_b, "power_b": power_b, "sides": sides},
        compatibility_a=[(left + right) / 2 for left, right in zip(a_control, a_treatment)],
        compatibility_b=[(left + right) / 2 for left, right in zip(b_control, b_treatment)],
    )


def multi_factorial_poisson(*,
                            factor_a_standard_rate: float,
                            factor_b_standard_rate: float,
                            factor_a_treatment_rate: float | None = None,
                            factor_a_rate_ratio: float | None = None,
                            factor_b_treatment_rate: float | None = None,
                            factor_b_rate_ratio: float | None = None,
                            exposure_per_subject: float = 1.0,
                            alpha_a: float = 0.05, power_a: float = 0.90,
                            alpha_b: float = 0.05, power_b: float = 0.90,
                            sides: int = 2) -> dict[str, Any]:
    from .rates import two_group_poisson_rates
    a_standard = _positive("factor_a_standard_rate", factor_a_standard_rate)
    b_standard = _positive("factor_b_standard_rate", factor_b_standard_rate)
    exposure = _positive("exposure_per_subject", exposure_per_subject)
    parent_a = two_group_poisson_rates(
        standard_rate=a_standard, treatment_rate=factor_a_treatment_rate,
        rate_ratio=factor_a_rate_ratio, allocation_ratio=1.0,
        exposure_per_subject=exposure, alpha=alpha_a, power=power_a,
        sides=sides, number_of_reactions=1)
    parent_b = two_group_poisson_rates(
        standard_rate=b_standard, treatment_rate=factor_b_treatment_rate,
        rate_ratio=factor_b_rate_ratio, allocation_ratio=1.0,
        exposure_per_subject=exposure, alpha=alpha_b, power=power_b,
        sides=sides, number_of_reactions=1)
    a_treatment = float(parent_a["inputs"]["treatment_rate"])
    b_treatment = float(parent_b["inputs"]["treatment_rate"])
    return _factorial(
        method_id="MULTI-017", parent_a=parent_a, parent_b=parent_b,
        expected_parent="TWO-013",
        inputs={"factor_a_standard_rate": a_standard,
                "factor_a_treatment_rate": factor_a_treatment_rate,
                "factor_a_rate_ratio": factor_a_rate_ratio,
                "factor_b_standard_rate": b_standard,
                "factor_b_treatment_rate": factor_b_treatment_rate,
                "factor_b_rate_ratio": factor_b_rate_ratio,
                "exposure_per_subject": exposure,
                "alpha_a": alpha_a, "power_a": power_a,
                "alpha_b": alpha_b, "power_b": power_b, "sides": sides},
        compatibility_a=(a_standard + a_treatment) / 2,
        compatibility_b=(b_standard + b_treatment) / 2,
    )


def multi_factorial_negative_binomial(*,
                                      factor_a_standard_rate: float,
                                      factor_a_treatment_rate: float,
                                      factor_b_standard_rate: float,
                                      factor_b_treatment_rate: float,
                                      overdispersion: float, mean_exposure: float,
                                      alpha_a: float = 0.05, power_a: float = 0.90,
                                      alpha_b: float = 0.05, power_b: float = 0.90,
                                      sides: int = 2) -> dict[str, Any]:
    from .rates import two_group_negative_binomial_rates
    rates = {name: _positive(name, value) for name, value in {
        "factor_a_standard_rate": factor_a_standard_rate,
        "factor_a_treatment_rate": factor_a_treatment_rate,
        "factor_b_standard_rate": factor_b_standard_rate,
        "factor_b_treatment_rate": factor_b_treatment_rate,
    }.items()}
    dispersion = float(overdispersion)
    if not isfinite(dispersion) or dispersion < 0:
        raise ValueError("overdispersion must be finite and >= 0")
    exposure = _positive("mean_exposure", mean_exposure)
    parent_a = two_group_negative_binomial_rates(
        standard_rate=rates["factor_a_standard_rate"],
        treatment_rate=rates["factor_a_treatment_rate"],
        overdispersion=dispersion, mean_exposure=exposure,
        allocation_ratio=1.0, alpha=alpha_a, power=power_a,
        sides=sides, number_of_reactions=1)
    parent_b = two_group_negative_binomial_rates(
        standard_rate=rates["factor_b_standard_rate"],
        treatment_rate=rates["factor_b_treatment_rate"],
        overdispersion=dispersion, mean_exposure=exposure,
        allocation_ratio=1.0, alpha=alpha_b, power=power_b,
        sides=sides, number_of_reactions=1)
    return _factorial(
        method_id="MULTI-018", parent_a=parent_a, parent_b=parent_b,
        expected_parent="TWO-014",
        inputs={**rates, "overdispersion": dispersion, "mean_exposure": exposure,
                "alpha_a": alpha_a, "power_a": power_a,
                "alpha_b": alpha_b, "power_b": power_b, "sides": sides},
        compatibility_a=(rates["factor_a_standard_rate"] + rates["factor_a_treatment_rate"]) / 2,
        compatibility_b=(rates["factor_b_standard_rate"] + rates["factor_b_treatment_rate"]) / 2,
    )


def _survival_participant_parent(*, event_function: Callable[..., dict[str, Any]],
                                 parent_method_id: str, hazard_ratio: float,
                                 standard_event_probability: float,
                                 treatment_event_probability: float,
                                 allocation_ratio: float, alpha: float,
                                 power: float, sides: int) -> dict[str, Any]:
    """Execute the validated event kernel and TWO-019 participant conversion."""
    from .survival import events_to_participants

    ratio = _positive("hazard_ratio", hazard_ratio)
    if ratio == 1:
        raise ValueError("hazard_ratio must differ from 1")
    standard = _event_probability("standard_event_probability", standard_event_probability)
    treatment = _event_probability("treatment_event_probability", treatment_event_probability)
    phi = _positive("allocation_ratio", allocation_ratio)
    events = event_function(
        hazard_ratio=ratio, allocation_ratio=phi,
        alpha=alpha, power=power, sides=sides)
    participants = events_to_participants(
        parent_result=events,
        standard_event_probability=standard,
        treatment_event_probability=treatment,
        allocation_ratio=phi)
    conversion_source = participants.get("source_provenance")
    conversion_evidence = participants.get("validation_evidence")
    participants["method_id"] = parent_method_id
    participants["formula_reference"] = (
        f"{events['formula_reference']} plus TWO-019 equation 7.8")
    participants["inputs"] = {
        **events["inputs"],
        "standard_event_probability": standard,
        "treatment_event_probability": treatment,
        "event_to_participant_component": "TWO-019",
    }
    participants["source_provenance"] = {
        "event_kernel": events.get("source_provenance"),
        "participant_conversion": conversion_source,
    }
    participants["validation_evidence"] = {
        "scope": "validated event kernel plus validated TWO-019 participant conversion",
        "event_kernel": events.get("validation_evidence"),
        "participant_conversion": conversion_evidence,
    }
    participants["survival_parent_lineage"] = [
        {"role": "required_events", "parent_method_id": parent_method_id,
         "produced_key": "rounded_events"},
        {"role": "events_to_participants", "component_id": "TWO-019",
         "consumed_key": "rounded_events", "produced_key": "final_total"},
    ]
    return participants


def _multi_all_pair_survival(*, method_id: str,
                             event_function: Callable[..., dict[str, Any]],
                             parent_method_id: str,
                             arm_hazard_multipliers: Sequence[float],
                             arm_event_probabilities: Sequence[float],
                             alpha: float, power: float, sides: int,
                             multiplicity: str) -> dict[str, Any]:
    hazards = [_positive(f"arm_hazard_multipliers[{index}]", value)
               for index, value in enumerate(
                   _numeric_list("arm_hazard_multipliers", arm_hazard_multipliers))]
    if len(set(hazards)) != len(hazards):
        raise ValueError("all arm_hazard_multipliers must differ because every pair is prespecified")
    if (isinstance(arm_event_probabilities, (str, bytes))
            or not isinstance(arm_event_probabilities, Sequence)
            or len(arm_event_probabilities) != len(hazards)):
        raise ValueError("arm_event_probabilities must contain one value per arm")
    probabilities = [
        _event_probability(f"arm_event_probabilities[{index}]", value)
        for index, value in enumerate(arm_event_probabilities)]
    return _all_pair_max(
        method_id=method_id, arm_count=len(hazards), alpha=alpha, power=power,
        sides=sides, multiplicity=multiplicity, expected_parent=parent_method_id,
        inputs={"arm_hazard_multipliers": hazards,
                "arm_event_probabilities": probabilities,
                "event_method": parent_method_id,
                "event_to_participant_component": "TWO-019"},
        build_parent=lambda i, j, a, p, s: _survival_participant_parent(
            event_function=event_function, parent_method_id=parent_method_id,
            hazard_ratio=hazards[j] / hazards[i],
            standard_event_probability=probabilities[i],
            treatment_event_probability=probabilities[j],
            allocation_ratio=1.0, alpha=a, power=p, sides=s),
    )


def multi_all_pair_survival_schoenfeld(*,
                                       arm_hazard_multipliers: Sequence[float],
                                       arm_event_probabilities: Sequence[float],
                                       alpha: float = 0.05, power: float = 0.80,
                                       sides: int = 2,
                                       multiplicity: str = "none") -> dict[str, Any]:
    from .survival import schoenfeld_events
    return _multi_all_pair_survival(
        method_id="MULTI-019", event_function=schoenfeld_events,
        parent_method_id="TWO-017",
        arm_hazard_multipliers=arm_hazard_multipliers,
        arm_event_probabilities=arm_event_probabilities,
        alpha=alpha, power=power, sides=sides, multiplicity=multiplicity)


def multi_all_pair_survival_freedman(*,
                                     arm_hazard_multipliers: Sequence[float],
                                     arm_event_probabilities: Sequence[float],
                                     alpha: float = 0.05, power: float = 0.80,
                                     sides: int = 2,
                                     multiplicity: str = "none") -> dict[str, Any]:
    from .survival import freedman_events
    return _multi_all_pair_survival(
        method_id="MULTI-020", event_function=freedman_events,
        parent_method_id="TWO-018",
        arm_hazard_multipliers=arm_hazard_multipliers,
        arm_event_probabilities=arm_event_probabilities,
        alpha=alpha, power=power, sides=sides, multiplicity=multiplicity)


def _multi_shared_reference_survival(*, method_id: str,
                                     event_function: Callable[..., dict[str, Any]],
                                     parent_method_id: str,
                                     least_favorable_hazard_ratio: float,
                                     reference_event_probability: float,
                                     least_favorable_treatment_event_probability: float,
                                     number_of_treatment_arms: int,
                                     alpha: float, power: float,
                                     allocation_block: list[int] | None) -> dict[str, Any]:
    ratio = _positive("least_favorable_hazard_ratio", least_favorable_hazard_ratio)
    if ratio == 1:
        raise ValueError("least_favorable_hazard_ratio must differ from 1")
    reference = _event_probability("reference_event_probability", reference_event_probability)
    treatment = _event_probability(
        "least_favorable_treatment_event_probability",
        least_favorable_treatment_event_probability)
    return _shared_reference(
        method_id=method_id, number_of_treatment_arms=number_of_treatment_arms,
        allocation_block=allocation_block, alpha=alpha, power=power,
        expected_parent=parent_method_id,
        inputs={"least_favorable_hazard_ratio": ratio,
                "reference_event_probability": reference,
                "least_favorable_treatment_event_probability": treatment,
                "event_method": parent_method_id,
                "event_to_participant_component": "TWO-019"},
        build_parent=lambda phi, a, p: _survival_participant_parent(
            event_function=event_function, parent_method_id=parent_method_id,
            hazard_ratio=ratio,
            standard_event_probability=reference,
            treatment_event_probability=treatment,
            allocation_ratio=phi, alpha=a, power=p, sides=1),
    )


def multi_shared_reference_survival_schoenfeld(*,
                                               least_favorable_hazard_ratio: float,
                                               reference_event_probability: float,
                                               least_favorable_treatment_event_probability: float,
                                               number_of_treatment_arms: int,
                                               alpha: float = 0.05,
                                               power: float = 0.80,
                                               allocation_block: list[int] | None = None) -> dict[str, Any]:
    from .survival import schoenfeld_events
    return _multi_shared_reference_survival(
        method_id="MULTI-021", event_function=schoenfeld_events,
        parent_method_id="TWO-017",
        least_favorable_hazard_ratio=least_favorable_hazard_ratio,
        reference_event_probability=reference_event_probability,
        least_favorable_treatment_event_probability=least_favorable_treatment_event_probability,
        number_of_treatment_arms=number_of_treatment_arms,
        alpha=alpha, power=power, allocation_block=allocation_block)


def multi_shared_reference_survival_freedman(*,
                                             least_favorable_hazard_ratio: float,
                                             reference_event_probability: float,
                                             least_favorable_treatment_event_probability: float,
                                             number_of_treatment_arms: int,
                                             alpha: float = 0.05,
                                             power: float = 0.80,
                                             allocation_block: list[int] | None = None) -> dict[str, Any]:
    from .survival import freedman_events
    return _multi_shared_reference_survival(
        method_id="MULTI-022", event_function=freedman_events,
        parent_method_id="TWO-018",
        least_favorable_hazard_ratio=least_favorable_hazard_ratio,
        reference_event_probability=reference_event_probability,
        least_favorable_treatment_event_probability=least_favorable_treatment_event_probability,
        number_of_treatment_arms=number_of_treatment_arms,
        alpha=alpha, power=power, allocation_block=allocation_block)


def _multi_factorial_survival(*, method_id: str,
                              event_function: Callable[..., dict[str, Any]],
                              parent_method_id: str,
                              factor_a_hazard_ratio: float,
                              factor_a_standard_event_probability: float,
                              factor_a_treatment_event_probability: float,
                              factor_b_hazard_ratio: float,
                              factor_b_standard_event_probability: float,
                              factor_b_treatment_event_probability: float,
                              alpha_a: float, power_a: float,
                              alpha_b: float, power_b: float,
                              sides: int) -> dict[str, Any]:
    values = {name: _event_probability(name, value) for name, value in {
        "factor_a_standard_event_probability": factor_a_standard_event_probability,
        "factor_a_treatment_event_probability": factor_a_treatment_event_probability,
        "factor_b_standard_event_probability": factor_b_standard_event_probability,
        "factor_b_treatment_event_probability": factor_b_treatment_event_probability,
    }.items()}
    ratio_a = _positive("factor_a_hazard_ratio", factor_a_hazard_ratio)
    ratio_b = _positive("factor_b_hazard_ratio", factor_b_hazard_ratio)
    if ratio_a == 1 or ratio_b == 1:
        raise ValueError("factor hazard ratios must differ from 1")
    parent_a = _survival_participant_parent(
        event_function=event_function, parent_method_id=parent_method_id,
        hazard_ratio=ratio_a,
        standard_event_probability=values["factor_a_standard_event_probability"],
        treatment_event_probability=values["factor_a_treatment_event_probability"],
        allocation_ratio=1.0, alpha=alpha_a, power=power_a, sides=sides)
    parent_b = _survival_participant_parent(
        event_function=event_function, parent_method_id=parent_method_id,
        hazard_ratio=ratio_b,
        standard_event_probability=values["factor_b_standard_event_probability"],
        treatment_event_probability=values["factor_b_treatment_event_probability"],
        allocation_ratio=1.0, alpha=alpha_b, power=power_b, sides=sides)
    return _factorial(
        method_id=method_id, parent_a=parent_a, parent_b=parent_b,
        expected_parent=parent_method_id,
        inputs={**values, "factor_a_hazard_ratio": ratio_a,
                "factor_b_hazard_ratio": ratio_b,
                "event_method": parent_method_id,
                "event_to_participant_component": "TWO-019",
                "alpha_a": alpha_a, "power_a": power_a,
                "alpha_b": alpha_b, "power_b": power_b, "sides": sides},
        compatibility_a=(
            values["factor_a_standard_event_probability"]
            + values["factor_a_treatment_event_probability"]) / 2,
        compatibility_b=(
            values["factor_b_standard_event_probability"]
            + values["factor_b_treatment_event_probability"]) / 2,
    )


def multi_factorial_survival_schoenfeld(*,
                                        factor_a_hazard_ratio: float,
                                        factor_a_standard_event_probability: float,
                                        factor_a_treatment_event_probability: float,
                                        factor_b_hazard_ratio: float,
                                        factor_b_standard_event_probability: float,
                                        factor_b_treatment_event_probability: float,
                                        alpha_a: float = 0.05, power_a: float = 0.90,
                                        alpha_b: float = 0.05, power_b: float = 0.90,
                                        sides: int = 2) -> dict[str, Any]:
    from .survival import schoenfeld_events
    return _multi_factorial_survival(
        method_id="MULTI-023", event_function=schoenfeld_events,
        parent_method_id="TWO-017",
        factor_a_hazard_ratio=factor_a_hazard_ratio,
        factor_a_standard_event_probability=factor_a_standard_event_probability,
        factor_a_treatment_event_probability=factor_a_treatment_event_probability,
        factor_b_hazard_ratio=factor_b_hazard_ratio,
        factor_b_standard_event_probability=factor_b_standard_event_probability,
        factor_b_treatment_event_probability=factor_b_treatment_event_probability,
        alpha_a=alpha_a, power_a=power_a, alpha_b=alpha_b, power_b=power_b,
        sides=sides)


def multi_factorial_survival_freedman(*,
                                      factor_a_hazard_ratio: float,
                                      factor_a_standard_event_probability: float,
                                      factor_a_treatment_event_probability: float,
                                      factor_b_hazard_ratio: float,
                                      factor_b_standard_event_probability: float,
                                      factor_b_treatment_event_probability: float,
                                      alpha_a: float = 0.05, power_a: float = 0.90,
                                      alpha_b: float = 0.05, power_b: float = 0.90,
                                      sides: int = 2) -> dict[str, Any]:
    from .survival import freedman_events
    return _multi_factorial_survival(
        method_id="MULTI-024", event_function=freedman_events,
        parent_method_id="TWO-018",
        factor_a_hazard_ratio=factor_a_hazard_ratio,
        factor_a_standard_event_probability=factor_a_standard_event_probability,
        factor_a_treatment_event_probability=factor_a_treatment_event_probability,
        factor_b_hazard_ratio=factor_b_hazard_ratio,
        factor_b_standard_event_probability=factor_b_standard_event_probability,
        factor_b_treatment_event_probability=factor_b_treatment_event_probability,
        alpha_a=alpha_a, power_a=power_a, alpha_b=alpha_b, power_b=power_b,
        sides=sides)


def _open_probability(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 < value < 1:
        raise ValueError(f"{name} must be a finite probability in (0, 1)")
    return value


def _censoring_probability(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 <= value < 1:
        raise ValueError(f"{name} must be a finite probability in [0, 1)")
    return value


def _parallel_values(name: str, values: Sequence[float], count: int,
                     validator: Callable[[str, float], float]) -> list[float]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or len(values) != count:
        raise ValueError(f"{name} must contain one value per arm")
    return [validator(f"{name}[{index}]", value) for index, value in enumerate(values)]


def _competing_hazard_arms(name: str, values: Sequence[Sequence[float]],
                           count: int) -> list[list[float]]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or len(values) != count:
        raise ValueError(f"{name} must contain one array per arm")
    result: list[list[float]] = []
    for arm_index, row in enumerate(values):
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise ValueError(f"{name}[{arm_index}] must be an array")
        result.append([
            _positive(f"{name}[{arm_index}][{cause_index}]", value)
            for cause_index, value in enumerate(row)
        ])
    return result


def multi_all_pair_competing_cause_specific(*,
                                             arm_interest_hazards: Sequence[float],
                                             arm_competing_hazards: Sequence[Sequence[float]],
                                             accrual_duration: float,
                                             additional_followup: float,
                                             alpha: float = 0.05,
                                             power: float = 0.80,
                                             sides: int = 2,
                                             multiplicity: str = "none") -> dict[str, Any]:
    from .competing import cause_specific_hazard_competing_risk
    interest = [
        _positive(f"arm_interest_hazards[{index}]", value)
        for index, value in enumerate(_numeric_list("arm_interest_hazards", arm_interest_hazards))
    ]
    if len(set(interest)) != len(interest):
        raise ValueError("all arm_interest_hazards must differ because every pair is prespecified")
    competing = _competing_hazard_arms("arm_competing_hazards", arm_competing_hazards, len(interest))
    accrual = _positive("accrual_duration", accrual_duration)
    followup = _positive("additional_followup", additional_followup)
    return _all_pair_max(
        method_id="MULTI-025", arm_count=len(interest), alpha=alpha, power=power,
        sides=sides, multiplicity=multiplicity, expected_parent="TWO-020",
        inputs={"arm_interest_hazards": interest, "arm_competing_hazards": competing,
                "accrual_duration": accrual, "additional_followup": followup},
        build_parent=lambda i, j, a, p, s: cause_specific_hazard_competing_risk(
            cause_specific_hazard_ratio=interest[j] / interest[i],
            standard_interest_hazard=interest[i], standard_competing_hazards=competing[i],
            treatment_interest_hazard=interest[j], treatment_competing_hazards=competing[j],
            accrual_duration=accrual, additional_followup=followup,
            allocation_ratio=1.0, alpha=a, power=p, sides=s),
    )


def multi_all_pair_competing_fixed_censoring(*,
                                              arm_interest_cifs: Sequence[float],
                                              arm_censoring_probabilities: Sequence[float],
                                              alpha: float = 0.05,
                                              power: float = 0.80,
                                              sides: int = 2,
                                              multiplicity: str = "none") -> dict[str, Any]:
    from .competing import subdistribution_fixed_censoring
    cifs = [
        _open_probability(f"arm_interest_cifs[{index}]", value)
        for index, value in enumerate(_numeric_list("arm_interest_cifs", arm_interest_cifs))
    ]
    if len(set(cifs)) != len(cifs):
        raise ValueError("all arm_interest_cifs must differ because every pair is prespecified")
    censoring = _parallel_values(
        "arm_censoring_probabilities", arm_censoring_probabilities, len(cifs),
        _censoring_probability)
    return _all_pair_max(
        method_id="MULTI-026", arm_count=len(cifs), alpha=alpha, power=power,
        sides=sides, multiplicity=multiplicity, expected_parent="TWO-021",
        inputs={"arm_interest_cifs": cifs, "arm_censoring_probabilities": censoring,
                "effect_input_path": "derived_pairwise_from_CIFs"},
        build_parent=lambda i, j, a, p, s: subdistribution_fixed_censoring(
            standard_interest_cif=cifs[i], treatment_interest_cif=cifs[j],
            standard_censoring_probability=censoring[i],
            treatment_censoring_probability=censoring[j],
            allocation_ratio=1.0, alpha=a, power=p, sides=s),
    )


def multi_all_pair_competing_accrual(*,
                                      arm_interest_cifs: Sequence[float],
                                      reference_time: float,
                                      accrual_duration: float,
                                      additional_followup: float,
                                      alpha: float = 0.05,
                                      power: float = 0.80,
                                      sides: int = 2,
                                      multiplicity: str = "none") -> dict[str, Any]:
    from .competing import subdistribution_accrual_integration
    cifs = [
        _open_probability(f"arm_interest_cifs[{index}]", value)
        for index, value in enumerate(_numeric_list("arm_interest_cifs", arm_interest_cifs))
    ]
    if len(set(cifs)) != len(cifs):
        raise ValueError("all arm_interest_cifs must differ because every pair is prespecified")
    reference = _positive("reference_time", reference_time)
    accrual = _positive("accrual_duration", accrual_duration)
    followup = _positive("additional_followup", additional_followup)
    return _all_pair_max(
        method_id="MULTI-027", arm_count=len(cifs), alpha=alpha, power=power,
        sides=sides, multiplicity=multiplicity, expected_parent="TWO-022",
        inputs={"arm_interest_cifs": cifs, "reference_time": reference,
                "accrual_duration": accrual, "additional_followup": followup,
                "effect_input_path": "derived_pairwise_from_CIFs"},
        build_parent=lambda i, j, a, p, s: subdistribution_accrual_integration(
            standard_interest_cif=cifs[i], treatment_interest_cif=cifs[j],
            reference_time=reference, accrual_duration=accrual,
            additional_followup=followup, allocation_ratio=1.0,
            alpha=a, power=p, sides=s),
    )


def multi_shared_reference_competing_cause_specific(*,
                                                     reference_interest_hazard: float,
                                                     reference_competing_hazards: Sequence[float],
                                                     least_favorable_treatment_interest_hazard: float,
                                                     least_favorable_treatment_competing_hazards: Sequence[float],
                                                     accrual_duration: float,
                                                     additional_followup: float,
                                                     number_of_treatment_arms: int,
                                                     alpha: float = 0.05,
                                                     power: float = 0.80,
                                                     allocation_block: list[int] | None = None) -> dict[str, Any]:
    from .competing import cause_specific_hazard_competing_risk
    reference = _positive("reference_interest_hazard", reference_interest_hazard)
    treatment = _positive(
        "least_favorable_treatment_interest_hazard",
        least_favorable_treatment_interest_hazard)
    if reference == treatment:
        raise ValueError("reference and treatment interest hazards must differ")
    reference_competing = [
        _positive(f"reference_competing_hazards[{index}]", value)
        for index, value in enumerate(reference_competing_hazards)
    ]
    treatment_competing = [
        _positive(f"least_favorable_treatment_competing_hazards[{index}]", value)
        for index, value in enumerate(least_favorable_treatment_competing_hazards)
    ]
    accrual = _positive("accrual_duration", accrual_duration)
    followup = _positive("additional_followup", additional_followup)
    return _shared_reference(
        method_id="MULTI-028", number_of_treatment_arms=number_of_treatment_arms,
        allocation_block=allocation_block, alpha=alpha, power=power,
        expected_parent="TWO-020",
        inputs={"reference_interest_hazard": reference,
                "reference_competing_hazards": reference_competing,
                "least_favorable_treatment_interest_hazard": treatment,
                "least_favorable_treatment_competing_hazards": treatment_competing,
                "accrual_duration": accrual, "additional_followup": followup,
                "effect_input_path": "derived_from_interest_hazards"},
        build_parent=lambda phi, a, p: cause_specific_hazard_competing_risk(
            cause_specific_hazard_ratio=treatment / reference,
            standard_interest_hazard=reference,
            standard_competing_hazards=reference_competing,
            treatment_interest_hazard=treatment,
            treatment_competing_hazards=treatment_competing,
            accrual_duration=accrual, additional_followup=followup,
            allocation_ratio=phi, alpha=a, power=p, sides=1),
    )


def multi_shared_reference_competing_fixed_censoring(*,
                                                      reference_interest_cif: float,
                                                      least_favorable_treatment_interest_cif: float,
                                                      reference_censoring_probability: float,
                                                      least_favorable_treatment_censoring_probability: float,
                                                      number_of_treatment_arms: int,
                                                      alpha: float = 0.05,
                                                      power: float = 0.80,
                                                      allocation_block: list[int] | None = None) -> dict[str, Any]:
    from .competing import subdistribution_fixed_censoring
    reference = _open_probability("reference_interest_cif", reference_interest_cif)
    treatment = _open_probability(
        "least_favorable_treatment_interest_cif",
        least_favorable_treatment_interest_cif)
    if reference == treatment:
        raise ValueError("reference and treatment interest CIFs must differ")
    reference_censoring = _censoring_probability(
        "reference_censoring_probability", reference_censoring_probability)
    treatment_censoring = _censoring_probability(
        "least_favorable_treatment_censoring_probability",
        least_favorable_treatment_censoring_probability)
    return _shared_reference(
        method_id="MULTI-029", number_of_treatment_arms=number_of_treatment_arms,
        allocation_block=allocation_block, alpha=alpha, power=power,
        expected_parent="TWO-021",
        inputs={"reference_interest_cif": reference,
                "least_favorable_treatment_interest_cif": treatment,
                "reference_censoring_probability": reference_censoring,
                "least_favorable_treatment_censoring_probability": treatment_censoring,
                "effect_input_path": "derived_from_CIFs"},
        build_parent=lambda phi, a, p: subdistribution_fixed_censoring(
            standard_interest_cif=reference, treatment_interest_cif=treatment,
            standard_censoring_probability=reference_censoring,
            treatment_censoring_probability=treatment_censoring,
            allocation_ratio=phi, alpha=a, power=p, sides=1),
    )


def multi_shared_reference_competing_accrual(*,
                                              reference_interest_cif: float,
                                              least_favorable_treatment_interest_cif: float,
                                              reference_time: float,
                                              accrual_duration: float,
                                              additional_followup: float,
                                              number_of_treatment_arms: int,
                                              alpha: float = 0.05,
                                              power: float = 0.80,
                                              allocation_block: list[int] | None = None) -> dict[str, Any]:
    from .competing import subdistribution_accrual_integration
    reference_cif = _open_probability("reference_interest_cif", reference_interest_cif)
    treatment_cif = _open_probability(
        "least_favorable_treatment_interest_cif",
        least_favorable_treatment_interest_cif)
    if reference_cif == treatment_cif:
        raise ValueError("reference and treatment interest CIFs must differ")
    reference = _positive("reference_time", reference_time)
    accrual = _positive("accrual_duration", accrual_duration)
    followup = _positive("additional_followup", additional_followup)
    return _shared_reference(
        method_id="MULTI-030", number_of_treatment_arms=number_of_treatment_arms,
        allocation_block=allocation_block, alpha=alpha, power=power,
        expected_parent="TWO-022",
        inputs={"reference_interest_cif": reference_cif,
                "least_favorable_treatment_interest_cif": treatment_cif,
                "reference_time": reference, "accrual_duration": accrual,
                "additional_followup": followup,
                "effect_input_path": "derived_from_CIFs"},
        build_parent=lambda phi, a, p: subdistribution_accrual_integration(
            standard_interest_cif=reference_cif, treatment_interest_cif=treatment_cif,
            reference_time=reference, accrual_duration=accrual,
            additional_followup=followup, allocation_ratio=phi,
            alpha=a, power=p, sides=1),
    )


def _parent_average_interest_event_probability(parent: dict[str, Any]) -> float:
    return (
        float(parent["standard_interest_event_probability"])
        + float(parent["treatment_interest_event_probability"])
    ) / 2


def multi_factorial_competing_cause_specific(*,
                                             factor_a_standard_interest_hazard: float,
                                             factor_a_standard_competing_hazards: Sequence[float],
                                             factor_a_treatment_interest_hazard: float,
                                             factor_a_treatment_competing_hazards: Sequence[float],
                                             factor_b_standard_interest_hazard: float,
                                             factor_b_standard_competing_hazards: Sequence[float],
                                             factor_b_treatment_interest_hazard: float,
                                             factor_b_treatment_competing_hazards: Sequence[float],
                                             accrual_duration: float,
                                             additional_followup: float,
                                             alpha_a: float = 0.05,
                                             power_a: float = 0.90,
                                             alpha_b: float = 0.05,
                                             power_b: float = 0.90,
                                             sides: int = 2) -> dict[str, Any]:
    from .competing import cause_specific_hazard_competing_risk
    hazards = {name: _positive(name, value) for name, value in {
        "factor_a_standard_interest_hazard": factor_a_standard_interest_hazard,
        "factor_a_treatment_interest_hazard": factor_a_treatment_interest_hazard,
        "factor_b_standard_interest_hazard": factor_b_standard_interest_hazard,
        "factor_b_treatment_interest_hazard": factor_b_treatment_interest_hazard,
    }.items()}
    if (hazards["factor_a_standard_interest_hazard"] == hazards["factor_a_treatment_interest_hazard"]
            or hazards["factor_b_standard_interest_hazard"] == hazards["factor_b_treatment_interest_hazard"]):
        raise ValueError("factor standard and treatment interest hazards must differ")
    competing_inputs = {
        "factor_a_standard_competing_hazards": factor_a_standard_competing_hazards,
        "factor_a_treatment_competing_hazards": factor_a_treatment_competing_hazards,
        "factor_b_standard_competing_hazards": factor_b_standard_competing_hazards,
        "factor_b_treatment_competing_hazards": factor_b_treatment_competing_hazards,
    }
    competing = {
        name: [_positive(f"{name}[{index}]", value) for index, value in enumerate(values)]
        for name, values in competing_inputs.items()
    }
    accrual = _positive("accrual_duration", accrual_duration)
    followup = _positive("additional_followup", additional_followup)

    def parent(factor: str, alpha: float, power: float) -> dict[str, Any]:
        standard = hazards[f"factor_{factor}_standard_interest_hazard"]
        treatment = hazards[f"factor_{factor}_treatment_interest_hazard"]
        return cause_specific_hazard_competing_risk(
            cause_specific_hazard_ratio=treatment / standard,
            standard_interest_hazard=standard,
            standard_competing_hazards=competing[f"factor_{factor}_standard_competing_hazards"],
            treatment_interest_hazard=treatment,
            treatment_competing_hazards=competing[f"factor_{factor}_treatment_competing_hazards"],
            accrual_duration=accrual, additional_followup=followup,
            allocation_ratio=1.0, alpha=alpha, power=power, sides=sides)

    parent_a = parent("a", alpha_a, power_a)
    parent_b = parent("b", alpha_b, power_b)
    return _factorial(
        method_id="MULTI-031", parent_a=parent_a, parent_b=parent_b,
        expected_parent="TWO-020",
        inputs={**hazards, **competing, "accrual_duration": accrual,
                "additional_followup": followup, "alpha_a": alpha_a,
                "power_a": power_a, "alpha_b": alpha_b, "power_b": power_b,
                "sides": sides, "effect_input_path": "derived_from_interest_hazards"},
        compatibility_a=_parent_average_interest_event_probability(parent_a),
        compatibility_b=_parent_average_interest_event_probability(parent_b),
    )


def multi_factorial_competing_fixed_censoring(*,
                                              factor_a_standard_interest_cif: float,
                                              factor_a_treatment_interest_cif: float,
                                              factor_a_standard_censoring_probability: float,
                                              factor_a_treatment_censoring_probability: float,
                                              factor_b_standard_interest_cif: float,
                                              factor_b_treatment_interest_cif: float,
                                              factor_b_standard_censoring_probability: float,
                                              factor_b_treatment_censoring_probability: float,
                                              alpha_a: float = 0.05,
                                              power_a: float = 0.90,
                                              alpha_b: float = 0.05,
                                              power_b: float = 0.90,
                                              sides: int = 2) -> dict[str, Any]:
    from .competing import subdistribution_fixed_censoring
    cifs = {name: _open_probability(name, value) for name, value in {
        "factor_a_standard_interest_cif": factor_a_standard_interest_cif,
        "factor_a_treatment_interest_cif": factor_a_treatment_interest_cif,
        "factor_b_standard_interest_cif": factor_b_standard_interest_cif,
        "factor_b_treatment_interest_cif": factor_b_treatment_interest_cif,
    }.items()}
    if (cifs["factor_a_standard_interest_cif"] == cifs["factor_a_treatment_interest_cif"]
            or cifs["factor_b_standard_interest_cif"] == cifs["factor_b_treatment_interest_cif"]):
        raise ValueError("factor standard and treatment interest CIFs must differ")
    censoring = {name: _censoring_probability(name, value) for name, value in {
        "factor_a_standard_censoring_probability": factor_a_standard_censoring_probability,
        "factor_a_treatment_censoring_probability": factor_a_treatment_censoring_probability,
        "factor_b_standard_censoring_probability": factor_b_standard_censoring_probability,
        "factor_b_treatment_censoring_probability": factor_b_treatment_censoring_probability,
    }.items()}

    def parent(factor: str, alpha: float, power: float) -> dict[str, Any]:
        return subdistribution_fixed_censoring(
            standard_interest_cif=cifs[f"factor_{factor}_standard_interest_cif"],
            treatment_interest_cif=cifs[f"factor_{factor}_treatment_interest_cif"],
            standard_censoring_probability=censoring[f"factor_{factor}_standard_censoring_probability"],
            treatment_censoring_probability=censoring[f"factor_{factor}_treatment_censoring_probability"],
            allocation_ratio=1.0, alpha=alpha, power=power, sides=sides)

    parent_a = parent("a", alpha_a, power_a)
    parent_b = parent("b", alpha_b, power_b)
    return _factorial(
        method_id="MULTI-032", parent_a=parent_a, parent_b=parent_b,
        expected_parent="TWO-021",
        inputs={**cifs, **censoring, "alpha_a": alpha_a, "power_a": power_a,
                "alpha_b": alpha_b, "power_b": power_b, "sides": sides,
                "effect_input_path": "derived_from_CIFs"},
        compatibility_a=_parent_average_interest_event_probability(parent_a),
        compatibility_b=_parent_average_interest_event_probability(parent_b),
    )


def multi_factorial_competing_accrual(*,
                                      factor_a_standard_interest_cif: float,
                                      factor_a_treatment_interest_cif: float,
                                      factor_b_standard_interest_cif: float,
                                      factor_b_treatment_interest_cif: float,
                                      reference_time: float,
                                      accrual_duration: float,
                                      additional_followup: float,
                                      alpha_a: float = 0.05,
                                      power_a: float = 0.90,
                                      alpha_b: float = 0.05,
                                      power_b: float = 0.90,
                                      sides: int = 2) -> dict[str, Any]:
    from .competing import subdistribution_accrual_integration
    cifs = {name: _open_probability(name, value) for name, value in {
        "factor_a_standard_interest_cif": factor_a_standard_interest_cif,
        "factor_a_treatment_interest_cif": factor_a_treatment_interest_cif,
        "factor_b_standard_interest_cif": factor_b_standard_interest_cif,
        "factor_b_treatment_interest_cif": factor_b_treatment_interest_cif,
    }.items()}
    if (cifs["factor_a_standard_interest_cif"] == cifs["factor_a_treatment_interest_cif"]
            or cifs["factor_b_standard_interest_cif"] == cifs["factor_b_treatment_interest_cif"]):
        raise ValueError("factor standard and treatment interest CIFs must differ")
    reference = _positive("reference_time", reference_time)
    accrual = _positive("accrual_duration", accrual_duration)
    followup = _positive("additional_followup", additional_followup)

    def parent(factor: str, alpha: float, power: float) -> dict[str, Any]:
        return subdistribution_accrual_integration(
            standard_interest_cif=cifs[f"factor_{factor}_standard_interest_cif"],
            treatment_interest_cif=cifs[f"factor_{factor}_treatment_interest_cif"],
            reference_time=reference, accrual_duration=accrual,
            additional_followup=followup, allocation_ratio=1.0,
            alpha=alpha, power=power, sides=sides)

    parent_a = parent("a", alpha_a, power_a)
    parent_b = parent("b", alpha_b, power_b)
    return _factorial(
        method_id="MULTI-033", parent_a=parent_a, parent_b=parent_b,
        expected_parent="TWO-022",
        inputs={**cifs, "reference_time": reference, "accrual_duration": accrual,
                "additional_followup": followup, "alpha_a": alpha_a,
                "power_a": power_a, "alpha_b": alpha_b, "power_b": power_b,
                "sides": sides, "effect_input_path": "derived_from_CIFs"},
        compatibility_a=_parent_average_interest_event_probability(parent_a),
        compatibility_b=_parent_average_interest_event_probability(parent_b),
    )


MULTI_COMPOSITION_PROCEDURES: dict[str, Callable[..., dict[str, Any]]] = {
    "MULTI-007.SAMPLE_SIZE": multi_all_pair_continuous,
    "MULTI-008.SAMPLE_SIZE": multi_all_pair_ordinal,
    "MULTI-009.SAMPLE_SIZE": multi_all_pair_poisson,
    "MULTI-010.SAMPLE_SIZE": multi_all_pair_negative_binomial,
    "MULTI-011.SAMPLE_SIZE": multi_shared_reference_ordinal,
    "MULTI-012.SAMPLE_SIZE": multi_shared_reference_poisson,
    "MULTI-013.SAMPLE_SIZE": multi_shared_reference_negative_binomial,
    "MULTI-014.SAMPLE_SIZE": multi_factorial_binary_proportions,
    "MULTI-015.SAMPLE_SIZE": multi_factorial_binary_odds_ratio,
    "MULTI-016.SAMPLE_SIZE": multi_factorial_ordinal,
    "MULTI-017.SAMPLE_SIZE": multi_factorial_poisson,
    "MULTI-018.SAMPLE_SIZE": multi_factorial_negative_binomial,
    "MULTI-019.SAMPLE_SIZE": multi_all_pair_survival_schoenfeld,
    "MULTI-020.SAMPLE_SIZE": multi_all_pair_survival_freedman,
    "MULTI-021.SAMPLE_SIZE": multi_shared_reference_survival_schoenfeld,
    "MULTI-022.SAMPLE_SIZE": multi_shared_reference_survival_freedman,
    "MULTI-023.SAMPLE_SIZE": multi_factorial_survival_schoenfeld,
    "MULTI-024.SAMPLE_SIZE": multi_factorial_survival_freedman,
    "MULTI-025.SAMPLE_SIZE": multi_all_pair_competing_cause_specific,
    "MULTI-026.SAMPLE_SIZE": multi_all_pair_competing_fixed_censoring,
    "MULTI-027.SAMPLE_SIZE": multi_all_pair_competing_accrual,
    "MULTI-028.SAMPLE_SIZE": multi_shared_reference_competing_cause_specific,
    "MULTI-029.SAMPLE_SIZE": multi_shared_reference_competing_fixed_censoring,
    "MULTI-030.SAMPLE_SIZE": multi_shared_reference_competing_accrual,
    "MULTI-031.SAMPLE_SIZE": multi_factorial_competing_cause_specific,
    "MULTI-032.SAMPLE_SIZE": multi_factorial_competing_fixed_censoring,
    "MULTI-033.SAMPLE_SIZE": multi_factorial_competing_accrual,
}
