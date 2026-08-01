"""Chapter 12 and 14 end-to-end sample-size procedures.

The public procedures in this module return the final feasible study scale.
Design effects, attrition inflation, and allocation schedules remain auditable
components rather than separately counted public procedures.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations
from math import ceil, isfinite, log, sqrt
from statistics import NormalDist
from typing import Any, Callable

from ._version import VERSION

_N = NormalDist()


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than 0")
    return value


def _probability(name: str, value: float, *, allow_zero: bool = False) -> float:
    value = float(value)
    lower_ok = value >= 0 if allow_zero else value > 0
    if not isfinite(value) or not lower_ok or value >= 1:
        interval = "[0, 1)" if allow_zero else "(0, 1)"
        raise ValueError(f"{name} must be a finite value in {interval}")
    return value


def _proportion(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 < value < 1:
        raise ValueError(f"{name} must be a finite proportion in (0, 1)")
    return value


def _integer(name: str, value: int, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _critical(alpha: float, power: float, sides: int) -> tuple[float, float]:
    alpha = _probability("alpha", alpha)
    power = _probability("power", power)
    if sides not in {1, 2}:
        raise ValueError("sides must be 1 or 2")
    return _N.inv_cdf(1 - alpha / sides), _N.inv_cdf(power)


def _allocation_block(phi: float) -> tuple[int, int]:
    phi = _positive("allocation_ratio", phi)
    fraction = Fraction(phi).limit_denominator(100)
    return fraction.denominator, fraction.numerator


def _round_up_to_block(value: int, block: int) -> int:
    """Return the smallest integer not below ``value`` divisible by ``block``."""
    return ceil(value / block) * block


def _resolve_fixed_analyzable_clusters(
    *,
    fixed_analyzable_clusters: int | None,
    fixed_total_clusters: int | None,
) -> tuple[int, dict[str, Any] | None]:
    """Resolve the 0.6.1 canonical name and the explicit 0.6.0 legacy mapping."""
    if fixed_analyzable_clusters is not None and fixed_total_clusters is not None:
        raise ValueError(
            "provide fixed_analyzable_clusters only; fixed_total_clusters is a legacy alias"
        )
    if fixed_analyzable_clusters is None and fixed_total_clusters is None:
        raise ValueError("fixed_analyzable_clusters is required")
    if fixed_analyzable_clusters is not None:
        return _integer("fixed_analyzable_clusters", fixed_analyzable_clusters, 2), None
    resolved = _integer("fixed_total_clusters", fixed_total_clusters, 2)
    return resolved, {
        "code": "LEGACY_INPUT_INTERPRETATION",
        "legacy_field": "fixed_total_clusters",
        "canonical_field": "fixed_analyzable_clusters",
        "interpretation": "clusters required to remain available for the primary analysis",
    }


def cluster_design_effect(*, cluster_size: int, icc: float,
                          cluster_size_cv: float = 0.0) -> dict[str, float | str]:
    """Equations 12.5 and 12.7; variable-size formula is the planning approximation."""
    m = _integer("cluster_size", cluster_size)
    rho = _probability("icc", icc, allow_zero=True)
    cv = float(cluster_size_cv)
    if not isfinite(cv) or cv < 0:
        raise ValueError("cluster_size_cv must be finite and >= 0")
    de = 1 + (((1 + cv * cv) * m) - 1) * rho
    return {
        "value": de,
        "equal_size_value": 1 + (m - 1) * rho,
        "method": "equation 12.5" if cv == 0 else "equation 12.7 planning approximation",
    }


def fixed_cluster_feasibility(*, individual_required_total: float,
                              fixed_total_clusters: int, icc: float) -> dict[str, Any]:
    """Internal component from equations 12.25 and 12.26."""
    n0 = _positive("individual_required_total", individual_required_total)
    k = _integer("fixed_total_clusters", fixed_total_clusters, 2)
    rho = _probability("icc", icc, allow_zero=True)
    m_prime = n0 / k
    minimum_clusters = n0 * rho
    denominator = 1 - m_prime * rho
    if denominator <= 0:
        raise ValueError(
            "fixed cluster count is not feasible: K must exceed N_individual * ICC"
        )
    raw_cluster_size = m_prime * (1 - rho) / denominator
    return {
        "component_id": "COMP-FIXED-CLUSTER-FEASIBILITY",
        "calculation_type": "component",
        "formula_reference": "equations 12.25 and 12.26",
        "raw_cluster_size": raw_cluster_size,
        "rounded_cluster_size": ceil(raw_cluster_size),
        "fixed_total_clusters": k,
        "minimum_feasible_clusters_raw": minimum_clusters,
        "final_total_participants": k * ceil(raw_cluster_size),
    }


def _fixed_cluster_required_size_result(
    *,
    method: str,
    outcome: str,
    formula: str,
    parent_raw_total: float,
    fixed_analyzable_clusters: int,
    icc: float,
    allocation_ratio: float,
    alpha: float,
    power: float,
    sides: int,
    inputs: dict[str, Any],
    individual_attrition_rate: float = 0.0,
    cluster_attrition_rate: float = 0.0,
    parent_details: dict[str, Any] | None = None,
    legacy_input_mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble a public required-cluster-size procedure around Eq 12.25/12.26."""
    n0 = _positive("parent_raw_total", parent_raw_total)
    k = _integer("fixed_analyzable_clusters", fixed_analyzable_clusters, 2)
    rho = _probability("icc", icc, allow_zero=True)
    phi = _positive("allocation_ratio", allocation_ratio)
    ind_attrition = _probability("individual_attrition_rate", individual_attrition_rate, allow_zero=True)
    cluster_attrition = _probability("cluster_attrition_rate", cluster_attrition_rate, allow_zero=True)
    control_block, treatment_block = _allocation_block(phi)
    block = control_block + treatment_block
    allocation_feasible = (k % block) == 0
    lower_feasible = (k // block) * block
    upper_feasible = _round_up_to_block(k, block)
    if lower_feasible < block:
        lower_feasible = None
    allocation_candidates = {
        "required_allocation_block": block,
        "nearest_lower_feasible_clusters": lower_feasible,
        "nearest_upper_feasible_clusters": upper_feasible,
        "nearest_lower_by_arm": None if lower_feasible is None else {
            "control": lower_feasible // block * control_block,
            "treatment": lower_feasible // block * treatment_block,
        },
        "nearest_upper_by_arm": {
            "control": upper_feasible // block * control_block,
            "treatment": upper_feasible // block * treatment_block,
        },
    }
    warnings: list[dict[str, Any]] = []
    if legacy_input_mapping is not None:
        warnings.append(dict(legacy_input_mapping))
    if not allocation_feasible:
        warnings.append({
            "code": "INFEASIBLE_DESIGN",
            "message": "fixed_analyzable_clusters is not divisible by the allocation block",
            **allocation_candidates,
        })

    m_prime = n0 / k
    minimum_clusters = n0 * rho
    denominator = 1 - m_prime * rho
    statistical_feasible = denominator > 0
    attrition_feasible = True
    reasons: list[dict[str, Any]] = []
    if not statistical_feasible:
        reason = {
            "code": "INFEASIBLE_DESIGN",
            "domain": "statistical",
            "message": "fixed_analyzable_clusters must exceed parent_raw_total * icc",
        }
        reasons.append(reason)
        warnings.append(reason)
    if not allocation_feasible:
        reasons.append({
            "code": "INFEASIBLE_DESIGN",
            "domain": "allocation",
            "message": "fixed_analyzable_clusters does not satisfy the allocation block",
            **allocation_candidates,
        })
    overall_feasible = statistical_feasible and allocation_feasible and attrition_feasible

    raw_randomized_clusters = k / (1 - cluster_attrition)
    rounded_randomized_clusters = ceil(raw_randomized_clusters)
    final_randomized_clusters = _round_up_to_block(rounded_randomized_clusters, block)
    analyzable_control = k // block * control_block if allocation_feasible else None
    analyzable_treatment = k // block * treatment_block if allocation_feasible else None
    randomized_control = final_randomized_clusters // block * control_block
    randomized_treatment = final_randomized_clusters // block * treatment_block

    quantities = [
        {"key": "raw_parent_individual_total", "value": n0, "quantity": "participants", "unit": "participant", "stage": "raw"},
        {"key": "minimum_feasible_clusters_raw", "value": minimum_clusters, "quantity": "clusters", "unit": "cluster", "stage": "raw"},
        {"key": "fixed_analyzable_clusters", "value": k, "quantity": "clusters", "unit": "cluster", "stage": "analysis"},
        {"key": "raw_randomized_clusters", "value": raw_randomized_clusters, "quantity": "clusters", "unit": "cluster", "stage": "raw"},
        {"key": "rounded_randomized_clusters", "value": rounded_randomized_clusters, "quantity": "clusters", "unit": "cluster", "stage": "rounded"},
    ]
    raw_cluster_size = None
    rounded_cluster_size = None
    raw_randomized_cluster_size = None
    final_randomized_cluster_size = None
    raw_design_effect = None
    final_design_effect = None
    analyzable_total_participants = None
    enrolled_total_participants = None
    if statistical_feasible:
        raw_cluster_size = m_prime * (1 - rho) / denominator
        rounded_cluster_size = ceil(raw_cluster_size)
        raw_randomized_cluster_size = rounded_cluster_size / (1 - ind_attrition)
        final_randomized_cluster_size = ceil(raw_randomized_cluster_size)
        raw_design_effect = 1 + (raw_cluster_size - 1) * rho
        final_design_effect = 1 + (rounded_cluster_size - 1) * rho
        quantities.extend([
            {"key": "raw_analyzable_participants_per_cluster", "value": raw_cluster_size, "quantity": "participants", "unit": "participant_per_cluster", "stage": "raw"},
            {"key": "final_analyzable_participants_per_cluster", "value": rounded_cluster_size, "quantity": "participants", "unit": "participant_per_cluster", "stage": "analysis"},
            {"key": "raw_randomized_participants_per_cluster", "value": raw_randomized_cluster_size, "quantity": "participants", "unit": "participant_per_cluster", "stage": "raw"},
            {"key": "raw_design_effect", "value": raw_design_effect, "quantity": "design_effect", "unit": "dimensionless", "stage": "raw"},
            {"key": "final_design_effect", "value": final_design_effect, "quantity": "design_effect", "unit": "dimensionless", "stage": "analysis"},
        ])
    if overall_feasible:
        analyzable_total_participants = k * rounded_cluster_size
        enrolled_total_participants = final_randomized_clusters * final_randomized_cluster_size
        quantities.extend([
            {"key": "analyzable_control_clusters", "value": analyzable_control, "quantity": "clusters", "unit": "cluster_per_arm", "stage": "analysis"},
            {"key": "analyzable_treatment_clusters", "value": analyzable_treatment, "quantity": "clusters", "unit": "cluster_per_arm", "stage": "analysis"},
            {"key": "final_randomized_clusters", "value": final_randomized_clusters, "quantity": "clusters", "unit": "cluster", "stage": "final"},
            {"key": "randomized_control_clusters", "value": randomized_control, "quantity": "clusters", "unit": "cluster_per_arm", "stage": "final"},
            {"key": "randomized_treatment_clusters", "value": randomized_treatment, "quantity": "clusters", "unit": "cluster_per_arm", "stage": "final"},
            {"key": "final_randomized_participants_per_cluster", "value": final_randomized_cluster_size, "quantity": "participants", "unit": "participant_per_cluster", "stage": "final"},
            {"key": "analyzable_total_participants", "value": analyzable_total_participants, "quantity": "participants", "unit": "participant", "stage": "analysis"},
            {"key": "enrolled_total_participants", "value": enrolled_total_participants, "quantity": "participants", "unit": "participant", "stage": "final"},
        ])
    feasibility = {
        "overall": overall_feasible,
        "statistical": statistical_feasible,
        "allocation": allocation_feasible,
        "attrition": attrition_feasible,
        "reasons": reasons,
    }
    primary = (
        next(q for q in quantities if q["key"] == "final_randomized_participants_per_cluster")
        if overall_feasible else
        {"key": "feasibility", "value": False, "quantity": "feasibility", "unit": "boolean", "stage": "final"}
    )
    final_design = None if not overall_feasible else {
        "fixed_analyzable_clusters": k,
        "analyzable_clusters_by_arm": {"control": analyzable_control, "treatment": analyzable_treatment},
        "final_randomized_clusters": final_randomized_clusters,
        "randomized_clusters_by_arm": {"control": randomized_control, "treatment": randomized_treatment},
        "final_analyzable_participants_per_cluster": rounded_cluster_size,
        "final_randomized_participants_per_cluster": final_randomized_cluster_size,
        "analyzable_total_participants": analyzable_total_participants,
        "enrolled_total_participants": enrolled_total_participants,
    }
    result = _envelope(
        method, formula, inputs, primary, quantities,
        [{"role": "parent_individual_sample_size", "component_id": "parent individual model", "produced_key": "raw_parent_individual_total"},
         {"role": "fixed_cluster_feasibility", "component_id": "COMP-FIXED-CLUSTER-FEASIBILITY",
          "consumed_key": "raw_parent_individual_total", "consumed_quantity": "participants",
          "consumed_stage": "raw", "produced_key": "raw_analyzable_participants_per_cluster"},
         {"role": "individual_attrition", "component_id": "COMP-INDIVIDUAL-ATTRITION", "applied_rate": ind_attrition},
         {"role": "cluster_attrition", "component_id": "COMP-CLUSTER-ATTRITION", "applied_rate": cluster_attrition,
          "produced_key": "rounded_randomized_clusters"},
         {"role": "allocation_finalization", "component_id": "COMP-CLUSTER-DIVISIBILITY",
          "consumed_key": "rounded_randomized_clusters", "consumed_quantity": "clusters",
          "consumed_unit": "cluster", "consumed_stage": "rounded",
          "produced_key": "final_randomized_clusters"}],
        chapter=12, examples=[], discrepancies=["CH12-FIXED-CLUSTER-PUBLIC-WRAPPER"],
        extra={
            "operation": "REQUIRED_CLUSTER_SIZE",
            "procedure_id": f"{method}.REQUIRED_CLUSTER_SIZE",
            "outcome": outcome,
            "feasibility": feasibility,
            "overall_feasible": overall_feasible,
            "parent_raw_total": n0,
            "raw_cluster_size": raw_cluster_size,
            "rounded_cluster_size": rounded_cluster_size,
            "final_participants_per_cluster": final_randomized_cluster_size if overall_feasible else None,
            "raw_analyzable_participants_per_cluster": raw_cluster_size,
            "final_analyzable_participants_per_cluster": rounded_cluster_size,
            "raw_randomized_participants_per_cluster": raw_randomized_cluster_size,
            "final_randomized_participants_per_cluster": final_randomized_cluster_size if overall_feasible else None,
            "fixed_analyzable_clusters": k,
            # 0.6.0 compatibility field; its interpretation is now explicit.
            "fixed_total_clusters": k,
            "raw_randomized_clusters": raw_randomized_clusters,
            "rounded_randomized_clusters": rounded_randomized_clusters,
            "final_randomized_clusters": final_randomized_clusters if overall_feasible else None,
            "recruited_total_clusters": final_randomized_clusters if overall_feasible else None,
            "analyzable_control_clusters": analyzable_control if overall_feasible else None,
            "analyzable_treatment_clusters": analyzable_treatment if overall_feasible else None,
            "randomized_control_clusters": randomized_control if overall_feasible else None,
            "randomized_treatment_clusters": randomized_treatment if overall_feasible else None,
            "final_control_clusters": randomized_control if overall_feasible else None,
            "final_treatment_clusters": randomized_treatment if overall_feasible else None,
            "analyzable_total_participants": analyzable_total_participants,
            "enrolled_total_participants": enrolled_total_participants,
            "final_total_participants": enrolled_total_participants,
            "final_design": final_design,
            "minimum_feasible_clusters_raw": minimum_clusters,
            "allocation_block": {"control": control_block, "treatment": treatment_block},
            "allocation_feasible": allocation_feasible,
            **allocation_candidates,
            "design_effect": {
                "formula": "1 + (m - 1) * ICC",
                "source": "Chapter 12, equation 12.5",
                "icc": rho,
                "raw": {"cluster_size": raw_cluster_size, "value": raw_design_effect, "stage": "raw"},
                "final": {"cluster_size": rounded_cluster_size, "value": final_design_effect, "stage": "analysis"},
            },
            "error_code": None if overall_feasible else "INFEASIBLE_DESIGN",
            "rounding_rule": "ceil analyzable participants per cluster; inflate and ceil individual attrition; inflate cluster attrition then round up to the complete allocation block",
            "warnings": warnings,
            "legacy_input_mapping": legacy_input_mapping,
            "validation_evidence": {
                "scope": "procedure_implementation",
                "input_match_claim": False,
                "parent_model_fixture": f"validation/fixed_cluster_provenance.yaml::{method}::PARENT_MODEL_VALIDATION",
                "component_fixture": "validation/fixed_cluster_provenance.yaml::EX12.11-FIXED-COMPONENT",
                "independent_recomputation_fixture": f"validation/fixed_cluster_cases.yaml::{method}",
                "end_to_end_book_example": None,
                "discrepancy_ids": ["CH12-FIXED-CLUSTER-PUBLIC-WRAPPER"],
            },
            **(parent_details or {}),
        },
    )
    return result


def fixed_cluster_continuous_required_size(
    *,
    planned_difference: float,
    standard_deviation: float,
    icc: float,
    fixed_analyzable_clusters: int | None = None,
    fixed_total_clusters: int | None = None,
    allocation_ratio: float = 1.0,
    alpha: float = 0.05,
    power: float = 0.80,
    sides: int = 2,
    individual_attrition_rate: float = 0.0,
    cluster_attrition_rate: float = 0.0,
) -> dict[str, Any]:
    """Outcome-complete public wrapper for Chapter 12 fixed cluster-count continuous designs."""
    delta = float(planned_difference)
    if not isfinite(delta) or delta == 0:
        raise ValueError("planned_difference must be finite and nonzero")
    sd = _positive("standard_deviation", standard_deviation)
    k, legacy_mapping = _resolve_fixed_analyzable_clusters(
        fixed_analyzable_clusters=fixed_analyzable_clusters,
        fixed_total_clusters=fixed_total_clusters,
    )
    raw_parent, za, zb = _guenther_raw(delta, sd, alpha, power, sides, allocation_ratio)
    inputs = {
        "planned_difference": delta, "standard_deviation": sd,
        "fixed_analyzable_clusters": k, "icc": icc,
        "allocation_ratio": allocation_ratio, "alpha": alpha, "power": power,
        "sides": sides, "individual_attrition_rate": individual_attrition_rate,
        "cluster_attrition_rate": cluster_attrition_rate,
    }
    return _fixed_cluster_required_size_result(
        method="CLUSTER-FIXED-CONTINUOUS", outcome="continuous",
        formula="equations 12.25 and 12.26 with parent equation 5.4",
        parent_raw_total=raw_parent, fixed_analyzable_clusters=k,
        icc=icc, allocation_ratio=allocation_ratio, alpha=alpha, power=power, sides=sides,
        inputs=inputs, individual_attrition_rate=individual_attrition_rate,
        cluster_attrition_rate=cluster_attrition_rate,
        parent_details={"parent_model_id": "TWO-009", "z_alpha": za, "z_power": zb},
        legacy_input_mapping=legacy_mapping,
    )


def fixed_cluster_binary_required_size(
    *,
    standard_proportion: float,
    treatment_proportion: float,
    icc: float,
    fixed_analyzable_clusters: int | None = None,
    fixed_total_clusters: int | None = None,
    allocation_ratio: float = 1.0,
    alpha: float = 0.05,
    power: float = 0.80,
    sides: int = 2,
    individual_attrition_rate: float = 0.0,
    cluster_attrition_rate: float = 0.0,
) -> dict[str, Any]:
    """Outcome-complete public wrapper for Chapter 12 fixed cluster-count binary designs."""
    ps = _proportion("standard_proportion", standard_proportion)
    pt = _proportion("treatment_proportion", treatment_proportion)
    if ps == pt:
        raise ValueError("standard_proportion and treatment_proportion must differ")
    k, legacy_mapping = _resolve_fixed_analyzable_clusters(
        fixed_analyzable_clusters=fixed_analyzable_clusters,
        fixed_total_clusters=fixed_total_clusters,
    )
    pooled = (ps + pt) / 2
    planning_sd = sqrt(pooled * (1 - pooled))
    raw_parent, za, zb = _guenther_raw(pt - ps, planning_sd, alpha, power, sides, allocation_ratio)
    inputs = {
        "standard_proportion": ps, "treatment_proportion": pt,
        "fixed_analyzable_clusters": k, "icc": icc,
        "allocation_ratio": allocation_ratio, "alpha": alpha, "power": power,
        "sides": sides, "individual_attrition_rate": individual_attrition_rate,
        "cluster_attrition_rate": cluster_attrition_rate,
    }
    return _fixed_cluster_required_size_result(
        method="CLUSTER-FIXED-BINARY", outcome="binary",
        formula="equations 12.25 and 12.26 with parent equations 12.10 and 12.12-12.14",
        parent_raw_total=raw_parent, fixed_analyzable_clusters=k,
        icc=icc, allocation_ratio=allocation_ratio, alpha=alpha, power=power, sides=sides,
        inputs=inputs, individual_attrition_rate=individual_attrition_rate,
        cluster_attrition_rate=cluster_attrition_rate,
        parent_details={"parent_model_id": "TWO-036", "pooled_proportion": pooled,
                        "planning_standard_deviation": planning_sd,
                        "z_alpha": za, "z_power": zb},
        legacy_input_mapping=legacy_mapping,
    )


def stepped_wedge_complete_design_effect(*, steps: int, cluster_size: int,
                                         icc: float, cluster_autocorrelation: float = 1.0,
                                         individual_autocorrelation: float | None = None) -> dict[str, Any]:
    """Internal equations 13.2-13.6 and 13.14-13.15 component.

    ``individual_autocorrelation=None`` selects the cross-sectional design;
    a supplied value selects the closed-cohort correlation definition.
    """
    s = _integer("steps", steps, 2)
    m = _integer("cluster_size", cluster_size)
    rho = _probability("icc", icc, allow_zero=True)
    omega = float(cluster_autocorrelation)
    if not isfinite(omega) or not 0 <= omega <= 1:
        raise ValueError("cluster_autocorrelation must be a finite value in [0, 1]")
    design_type = "cross_sectional"
    if individual_autocorrelation is None:
        r = m * rho * omega / (1 + (m - 1) * rho)
    else:
        pi = _probability("individual_autocorrelation", individual_autocorrelation, allow_zero=True)
        r = (m * rho * omega + (1 - rho) * pi) / (1 + (m - 1) * rho)
        design_type = "closed_cohort"
    a = s
    e = s * (s + 1) / 2
    f = s * (s + 1) * (2 * s + 1) / 6
    g = f
    denominator = 4 * (a * e - g + (e * e + s * a * e - s * g - a * f) * r)
    if denominator <= 0:
        raise ValueError("stepped-wedge information denominator must be positive")
    de_swd = a * a * (1 - r) * (1 + s * r) / denominator
    de_cluster = 1 + (m - 1) * rho
    de_full = de_swd * de_cluster
    return {
        "component_id": "COMP-SWD-INFORMATION",
        "calculation_type": "component",
        "formula_reference": "equations 13.2-13.6 and 13.14-13.15",
        "design_type": design_type,
        "steps": s,
        "periods": s + 1,
        "E": e,
        "F": f,
        "G": g,
        "working_correlation_r": r,
        "swd_design_effect": de_swd,
        "cluster_design_effect": de_cluster,
        "full_design_effect": de_full,
        "participant_multiplier": (s + 1) * de_full if design_type == "cross_sectional" else de_full,
    }


def _source(method: str, chapter: int, equations: list[str], examples: list[str],
            *, tables: list[str] | None = None,
            discrepancy_ids: list[str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    discrepancies = list(discrepancy_ids or [])
    source = {
        "chapter": chapter,
        "equation_or_section": ", ".join(equations),
        "preferred_source": "Sample_size_tables_for_clinical_studies4.pdf",
        "corroborating_source": "医学研究のためのサンプルサイズ設計_20220330.pdf",
        "source_discrepancy_ids": discrepancies,
    }
    evidence = {
        "scope": "procedure_implementation",
        "input_match_claim": False,
        "fixed_fixture_ids": [
            f"validation/chapter{chapter:02d}_tables.csv::{name}" for name in (tables or [])
        ],
        "example_fixture_ids": [
            f"validation/chapter{chapter:02d}_examples.yaml::EX{example}" for example in examples
        ],
        "independent_audit_case_ids": [f"AUDIT-{method}-01..05"],
        "discrepancy_ids": discrepancies,
    }
    return source, evidence


def _envelope(method: str, formula: str, inputs: dict[str, Any],
              primary: dict[str, Any], quantities: list[dict[str, Any]],
              lineage: list[dict[str, Any]], *, chapter: int,
              examples: list[str], tables: list[str] | None = None,
              discrepancies: list[str] | None = None,
              extra: dict[str, Any] | None = None) -> dict[str, Any]:
    source, evidence = _source(method, chapter, [formula], examples,
                               tables=tables, discrepancy_ids=discrepancies)
    result: dict[str, Any] = {
        "product": "samplesize200 Alpha",
        "version": VERSION,
        "release_stage": "alpha",
        "release_theme": "Fixed-Cluster Contract Patch",
        "model_id": method,
        "operation": "sample_size",
        "procedure_id": f"{method}.SAMPLE_SIZE",
        "method_id": method,
        "formula_reference": formula,
        "inputs": inputs,
        "canonicalized_inputs": dict(inputs),
        "primary_result": primary,
        "related_quantities": [q for q in quantities if q != primary],
        "quantities": quantities,
        "warnings": [],
        "source_provenance": source,
        "validation_evidence": evidence,
        "procedure_lineage": lineage,
        "schema_status": "preview",
        "final_public_api": False,
        "validation_status": "VALIDATED",
    }
    if extra:
        result.update(extra)
    return result


def _multi_quantities(raw: float, final: int, per_arm: list[int]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = [
        {"key": "raw_total_participants", "value": raw, "quantity": "participants", "unit": "participant", "stage": "raw"},
        {"key": "rounded_total_participants", "value": ceil(raw), "quantity": "participants", "unit": "participant", "stage": "rounded"},
    ]
    records.extend({"key": f"final_arm_{i+1}_participants", "value": n,
                    "quantity": "participants", "unit": "participant_per_arm", "stage": "allocation_adjusted"}
                   for i, n in enumerate(per_arm))
    records.append({"key": "final_total_participants", "value": final,
                    "quantity": "participants", "unit": "participant", "stage": "final"})
    return records


def _pairwise_binary_raw(p0: float, p1: float, alpha: float, power: float,
                         sides: int) -> float:
    za, zb = _critical(alpha, power, sides)
    pooled = (p0 + p1) / 2
    delta = p1 - p0
    if delta == 0:
        raise ValueError("every prespecified pair must have a nonzero planned difference")
    null_term = za * sqrt(2 * pooled * (1 - pooled))
    alt_term = zb * sqrt(p0 * (1 - p0) + p1 * (1 - p1))
    return 2 * (null_term + alt_term) ** 2 / delta ** 2


def multi_unstructured_binary(*, arm_proportions: list[float], alpha: float = 0.05,
                              power: float = 0.80, sides: int = 2,
                              multiplicity: str = "none") -> dict[str, Any]:
    """MULTI-001: Chapter 14 pairwise-maximum equal-arm design."""
    from .binary import two_sample_proportions

    if not isinstance(arm_proportions, list) or len(arm_proportions) < 3:
        raise ValueError("arm_proportions must contain at least three arms")
    values = [_proportion(f"arm_proportions[{i}]", p) for i, p in enumerate(arm_proportions)]
    comparison_count = len(values) * (len(values) - 1) // 2
    if multiplicity not in {"none", "bonferroni"}:
        raise ValueError("multiplicity must be 'none' or 'bonferroni'")
    adjusted_alpha = float(alpha) / comparison_count if multiplicity == "bonferroni" else float(alpha)
    rows = []
    for i, j in combinations(range(len(values)), 2):
        parent = two_sample_proportions(
            control_proportion=values[i], treatment_proportion=values[j],
            allocation_ratio=1.0, alpha=adjusted_alpha, power=power, sides=sides,
        )
        rows.append({
            "arm_i": i + 1, "arm_j": j + 1,
            "raw_pair_total": parent["raw_total"],
            "parent_method_id": parent["method_id"],
            "parent_source_provenance": parent.get("source_provenance"),
            "parent_validation_evidence": parent.get("validation_evidence"),
        })
    limiting = max(rows, key=lambda row: row["raw_pair_total"])
    raw_total = len(values) * limiting["raw_pair_total"] / 2
    per_arm_n = ceil(limiting["raw_pair_total"] / 2)
    per_arm = [per_arm_n] * len(values)
    final = sum(per_arm)
    quantities = _multi_quantities(raw_total, final, per_arm)
    primary = quantities[-1]
    return _envelope(
        "MULTI-001", "Chapter 14 unstructured-groups pairwise maximum",
        {"arm_proportions": values, "alpha": alpha, "adjusted_alpha": adjusted_alpha,
         "power": power, "sides": sides, "multiplicity": multiplicity,
         "comparison_count": comparison_count}, primary, quantities,
        [{"role": "pairwise_sample_size", "parent_method_id": "TWO-001",
          "arm_i": row["arm_i"], "arm_j": row["arm_j"],
          "execution": "validated parent engine",
          "produced_key": "raw_pair_total",
          "parent_source_provenance": row["parent_source_provenance"],
          "parent_validation_evidence": row["parent_validation_evidence"]}
         for row in rows] +
        [
         {"role": "multiplicity", "component_id": "COMP-BONFERRONI",
          "applied": multiplicity == "bonferroni"},
         {"role": "equal_arm_divisibility", "component_id": "COMP-CLUSTER-DIVISIBILITY",
          "produced_key": "final_total_participants"}],
        chapter=14, examples=["14.1"], discrepancies=["CH14-EX14.1-ARITHMETIC"],
        extra={"raw_total": raw_total, "rounded_total": ceil(raw_total), "final_total": final,
               "pairwise_results": rows, "limiting_pair": limiting,
               "final_group_sizes": per_arm, "rounding_rule": "ceil the limiting pair per arm, then assign that integer to every arm"},
    )


def multi_dose_response_continuous(*, doses: list[float], planned_slope: float,
                                   standard_deviation: float, alpha: float = 0.05,
                                   power: float = 0.80, sides: int = 2) -> dict[str, Any]:
    """MULTI-002: equations 14.1-14.6."""
    if not isinstance(doses, list) or len(doses) < 3:
        raise ValueError("doses must contain at least three dose levels")
    x = [float(v) for v in doses]
    if any(not isfinite(v) for v in x) or len(set(x)) != len(x):
        raise ValueError("doses must be distinct finite numbers")
    slope = float(planned_slope)
    if not isfinite(slope) or slope == 0:
        raise ValueError("planned_slope must be finite and nonzero")
    sd = _positive("standard_deviation", standard_deviation)
    za, zb = _critical(alpha, power, sides)
    mean_x = sum(x) / len(x)
    information = sum((v - mean_x) ** 2 for v in x)
    raw_total = len(x) / information * sd ** 2 / slope ** 2 * (za + zb) ** 2
    per_arm_n = ceil(raw_total / len(x))
    per_arm = [per_arm_n] * len(x)
    final = sum(per_arm)
    quantities = _multi_quantities(raw_total, final, per_arm)
    return _envelope(
        "MULTI-002", "equations 14.1-14.6",
        {"doses": x, "planned_slope": slope, "standard_deviation": sd,
         "alpha": alpha, "power": power, "sides": sides,
         "dose_mean": mean_x, "dose_information_D": information,
         "z_alpha": za, "z_power": zb}, quantities[-1], quantities,
        [{"role": "dose_information", "component_id": "COMP-DOSE-INFORMATION", "produced_key": "dose_information_D"},
         {"role": "equal_arm_divisibility", "component_id": "COMP-CLUSTER-DIVISIBILITY", "produced_key": "final_total_participants"}],
        chapter=14, examples=["14.2", "14.3"],
        extra={"raw_total": raw_total, "rounded_total": ceil(raw_total), "final_total": final,
               "final_group_sizes": per_arm, "rounding_rule": "ceil per-arm raw size and enforce equal dose-arm sizes"},
    )


def _shared_reference_round(raw_total: float, treatment_arms: int,
                            allocation_block: list[int] | None) -> tuple[list[int], int, list[int]]:
    q = _integer("number_of_treatment_arms", treatment_arms, 2)
    if allocation_block is None:
        ratio = sqrt(q)
        fraction = Fraction(ratio).limit_denominator(20)
        block = [fraction.numerator] + [fraction.denominator] * q
    else:
        if (not isinstance(allocation_block, list) or len(allocation_block) != q + 1
                or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in allocation_block)):
            raise ValueError("allocation_block must contain one positive integer for reference and one for each treatment arm")
        block = list(allocation_block)
    blocks = ceil(raw_total / sum(block))
    groups = [blocks * v for v in block]
    return groups, sum(groups), block


def multi_shared_reference_binary(*, reference_proportion: float,
                                  minimum_treatment_proportion: float,
                                  number_of_treatment_arms: int,
                                  alpha: float = 0.05, power: float = 0.80,
                                  allocation_block: list[int] | None = None) -> dict[str, Any]:
    """MULTI-003: equations 14.7 and 14.9-14.11."""
    from .binary import two_sample_proportions

    pref = _proportion("reference_proportion", reference_proportion)
    pt = _proportion("minimum_treatment_proportion", minimum_treatment_proportion)
    if pref == pt:
        raise ValueError("reference and treatment proportions must differ")
    q = _integer("number_of_treatment_arms", number_of_treatment_arms, 2)
    phi = 1 / sqrt(q)
    parent = two_sample_proportions(
        control_proportion=pref, treatment_proportion=pt,
        allocation_ratio=phi, alpha=alpha, power=power, sides=1,
    )
    n2 = parent["raw_total"]
    za = parent["inputs"]["z_alpha"]
    zb = parent["inputs"]["z_power"]
    raw_total = n2 / phi
    groups, final, block = _shared_reference_round(raw_total, q, allocation_block)
    quantities = _multi_quantities(raw_total, final, groups)
    return _envelope(
        "MULTI-003", "equations 14.7 and 14.9-14.11",
        {"reference_proportion": pref, "minimum_treatment_proportion": pt,
         "number_of_treatment_arms": q, "alpha": alpha, "alpha_semantics": "one-sided per treatment-reference comparison",
         "power": power, "phi": phi, "allocation_block": block,
         "z_alpha": za, "z_power": zb}, quantities[-1], quantities,
        [{"role": "shared_reference_binary", "parent_method_id": "TWO-001",
          "execution": "validated parent engine", "produced_key": "raw_two_group_total",
          "parent_source_provenance": parent.get("source_provenance"),
          "parent_validation_evidence": parent.get("validation_evidence")},
         {"role": "allocation_divisibility", "component_id": "COMP-CLUSTER-DIVISIBILITY", "produced_key": "final_total_participants"}],
        chapter=14, examples=["14.4", "14.5"],
        discrepancies=["CH14-SHARED-REFERENCE-G6", "CH14-EX14.5-BINARY-DIRECTION"],
        extra={"raw_two_group_total": n2, "raw_total": raw_total,
               "rounded_total": ceil(raw_total), "final_total": final,
               "final_reference_participants": groups[0], "final_treatment_participants": groups[1:],
               "final_group_sizes": groups, "rounding_rule": "round upward to a complete shared-reference allocation block"},
    )


def multi_shared_reference_continuous(*, minimum_mean_difference: float,
                                      standard_deviation: float,
                                      number_of_treatment_arms: int,
                                      alpha: float = 0.05, power: float = 0.80,
                                      allocation_block: list[int] | None = None) -> dict[str, Any]:
    """MULTI-004: equations 14.8-14.11."""
    from .continuous import two_sample_mean_guenther

    delta = _positive("absolute minimum_mean_difference", abs(float(minimum_mean_difference)))
    sd = _positive("standard_deviation", standard_deviation)
    q = _integer("number_of_treatment_arms", number_of_treatment_arms, 2)
    phi = 1 / sqrt(q)
    parent = two_sample_mean_guenther(
        standardized_effect=delta / sd, allocation_ratio=phi,
        alpha=alpha, power=power, sides=1,
    )
    n2 = parent["raw_total"]
    za = parent["inputs"]["z_alpha"]
    zb = parent["inputs"]["z_power"]
    raw_total = n2 / phi
    groups, final, block = _shared_reference_round(raw_total, q, allocation_block)
    quantities = _multi_quantities(raw_total, final, groups)
    return _envelope(
        "MULTI-004", "equations 14.8-14.11",
        {"minimum_mean_difference": delta, "standard_deviation": sd,
         "number_of_treatment_arms": q, "alpha": alpha,
         "alpha_semantics": "one-sided per treatment-reference comparison",
         "power": power, "phi": phi, "allocation_block": block,
         "z_alpha": za, "z_power": zb}, quantities[-1], quantities,
        [{"role": "shared_reference_continuous", "parent_method_id": "TWO-009",
          "execution": "validated parent engine", "produced_key": "raw_two_group_total",
          "parent_source_provenance": parent.get("source_provenance"),
          "parent_validation_evidence": parent.get("validation_evidence")},
         {"role": "allocation_divisibility", "component_id": "COMP-CLUSTER-DIVISIBILITY", "produced_key": "final_total_participants"}],
        chapter=14, examples=["14.5"], discrepancies=["CH14-SHARED-REFERENCE-G6"],
        extra={"raw_two_group_total": n2, "raw_total": raw_total,
               "rounded_total": ceil(raw_total), "final_total": final,
               "final_reference_participants": groups[0], "final_treatment_participants": groups[1:],
               "final_group_sizes": groups, "rounding_rule": "round upward to a complete shared-reference allocation block"},
    )


def _guenther_raw(delta: float, sd: float, alpha: float, power: float, sides: int,
                  phi: float = 1.0) -> tuple[float, float, float]:
    if delta == 0:
        raise ValueError("planned effect must be nonzero")
    za, zb = _critical(alpha, power, sides)
    raw = ((1 + phi) ** 2 / phi) * (za + zb) ** 2 * sd ** 2 / delta ** 2 + za ** 2 / 2
    return raw, za, zb


def multi_factorial_continuous(*, factor_a_effect: float, factor_b_effect: float,
                               standard_deviation: float, alpha_a: float = 0.05,
                               power_a: float = 0.90, alpha_b: float = 0.05,
                               power_b: float = 0.90, sides: int = 2) -> dict[str, Any]:
    """MULTI-005: Chapter 14 2x2 factorial main-effect design."""
    from .continuous import two_sample_mean_guenther

    sd = _positive("standard_deviation", standard_deviation)
    a = float(factor_a_effect)
    b = float(factor_b_effect)
    if not isfinite(a) or a == 0 or not isfinite(b) or b == 0:
        raise ValueError("both factor effects must be finite and nonzero")
    parent_a = two_sample_mean_guenther(
        standardized_effect=abs(a) / sd, allocation_ratio=1.0,
        alpha=alpha_a, power=power_a, sides=sides,
    )
    parent_b = two_sample_mean_guenther(
        standardized_effect=abs(b) / sd, allocation_ratio=1.0,
        alpha=alpha_b, power=power_b, sides=sides,
    )
    raw_a = parent_a["raw_total"]
    raw_b = parent_b["raw_total"]
    za_a, zb_a = parent_a["inputs"]["z_alpha"], parent_a["inputs"]["z_power"]
    za_b, zb_b = parent_b["inputs"]["z_alpha"], parent_b["inputs"]["z_power"]
    limiting = max(raw_a, raw_b)
    two_group_feasible = ceil(limiting / 2) * 2
    final = ceil(two_group_feasible / 4) * 4
    groups = [final // 4] * 4
    quantities = _multi_quantities(limiting, final, groups)
    return _envelope(
        "MULTI-005", "Chapter 14 factorial design with equation 5.4",
        {"factor_a_effect": a, "factor_b_effect": b, "standard_deviation": sd,
         "alpha_a": alpha_a, "power_a": power_a, "alpha_b": alpha_b,
         "power_b": power_b, "sides": sides,
         "factor_a_z_alpha": za_a, "factor_a_z_power": zb_a,
         "factor_b_z_alpha": za_b, "factor_b_z_power": zb_b}, quantities[-1], quantities,
        [{"role": "factor_a_main_effect", "parent_method_id": "TWO-009",
          "execution": "validated parent engine", "produced_key": "raw_factor_a_total",
          "parent_source_provenance": parent_a.get("source_provenance"),
          "parent_validation_evidence": parent_a.get("validation_evidence")},
         {"role": "factor_b_main_effect", "parent_method_id": "TWO-009",
          "execution": "validated parent engine", "produced_key": "raw_factor_b_total",
          "parent_source_provenance": parent_b.get("source_provenance"),
          "parent_validation_evidence": parent_b.get("validation_evidence")},
         {"role": "four_cell_divisibility", "component_id": "COMP-CLUSTER-DIVISIBILITY", "produced_key": "final_total_participants"}],
        chapter=14, examples=["14.6"],
        extra={"raw_factor_a_total": raw_a, "raw_factor_b_total": raw_b,
               "limiting_factor": "A" if raw_a >= raw_b else "B",
               "raw_total": limiting, "rounded_total": ceil(limiting),
               "two_group_feasible_total": two_group_feasible,
               "final_total": final, "final_group_sizes": groups,
               "rounding_rule": "make the limiting two-group total even, then round to a multiple of four"},
    )


def _cluster_allocation(raw_clusters: float, phi: float, cluster_attrition: float,
                        minimum_clusters: int | None = None,
                        *, force_even: bool = False) -> dict[str, Any]:
    if not isfinite(raw_clusters) or raw_clusters <= 0:
        raise ValueError("raw required clusters must be positive and finite")
    attrition = _probability("cluster_attrition", cluster_attrition, allow_zero=True)
    adjusted = raw_clusters / (1 - attrition)
    standard_block, treatment_block = _allocation_block(phi)
    block_total = standard_block + treatment_block
    if force_even:
        standard_block = treatment_block = 1
        block_total = 2
    target = adjusted
    if minimum_clusters is not None:
        target = max(target, _integer("minimum_clusters", minimum_clusters, 2))
    blocks = ceil(target / block_total)
    return {
        "raw_clusters": raw_clusters,
        "cluster_attrition_adjusted_raw_clusters": adjusted,
        "allocation_block_standard_clusters": standard_block,
        "allocation_block_treatment_clusters": treatment_block,
        "final_standard_clusters": blocks * standard_block,
        "final_treatment_clusters": blocks * treatment_block,
        "final_total_clusters": blocks * block_total,
    }


def _cluster_quantities(raw_participants: float, allocation: dict[str, Any],
                        recruited_per_cluster: int, *, periods: int = 1,
                        same_participants_across_periods: bool = True) -> list[dict[str, Any]]:
    final_clusters = int(allocation["final_total_clusters"])
    final_participants = final_clusters * recruited_per_cluster
    observations = final_participants * periods
    quantities = [
        {"key": "raw_required_participants", "value": raw_participants, "quantity": "participants", "unit": "participant", "stage": "raw"},
        {"key": "raw_required_clusters", "value": allocation["raw_clusters"], "quantity": "clusters", "unit": "cluster", "stage": "raw"},
        {"key": "cluster_attrition_adjusted_raw_clusters", "value": allocation["cluster_attrition_adjusted_raw_clusters"], "quantity": "clusters", "unit": "cluster", "stage": "design_constrained"},
        {"key": "final_standard_clusters", "value": allocation["final_standard_clusters"], "quantity": "clusters", "unit": "cluster_per_arm", "stage": "allocation_adjusted"},
        {"key": "final_treatment_clusters", "value": allocation["final_treatment_clusters"], "quantity": "clusters", "unit": "cluster_per_arm", "stage": "allocation_adjusted"},
        {"key": "final_total_clusters", "value": final_clusters, "quantity": "clusters", "unit": "cluster", "stage": "final"},
        {"key": "final_participants_per_cluster", "value": recruited_per_cluster, "quantity": "participants", "unit": "participant_per_cluster", "stage": "design_constrained"},
        {"key": "final_total_participants", "value": final_participants, "quantity": "participants", "unit": "participant", "stage": "final"},
    ]
    if periods > 1:
        quantities.append({"key": "final_total_participant_observations", "value": observations,
                           "quantity": "participant_observations", "unit": "participant_observation", "stage": "final"})
        if not same_participants_across_periods:
            quantities[-2]["value"] = observations
    return quantities


def _cluster_result(method: str, formula: str, inputs: dict[str, Any],
                    raw_participants: float, raw_clusters: float,
                    *, chapter_examples: list[str], tables: list[str] | None = None,
                    discrepancies: list[str] | None = None,
                    individual_attrition: float = 0.0, cluster_attrition: float = 0.0,
                    minimum_clusters: int | None = None, force_even: bool = False,
                    periods: int = 1, same_participants_across_periods: bool = True,
                    extra: dict[str, Any] | None = None) -> dict[str, Any]:
    m = _integer("analysis_cluster_size", int(inputs["analysis_cluster_size"]))
    ind_attr = _probability("individual_attrition", individual_attrition, allow_zero=True)
    recruited_m = ceil(m / (1 - ind_attr))
    allocation = _cluster_allocation(raw_clusters, float(inputs.get("allocation_ratio", 1.0)),
                                     cluster_attrition, minimum_clusters, force_even=force_even)
    quantities = _cluster_quantities(raw_participants, allocation, recruited_m,
                                     periods=periods,
                                     same_participants_across_periods=same_participants_across_periods)
    primary = next(q for q in quantities if q["key"] == "final_total_clusters")
    final_participants = next(q["value"] for q in quantities if q["key"] == "final_total_participants")
    payload = {
        "raw_total": raw_participants,
        "rounded_total": ceil(raw_participants),
        "final_total": final_participants,
        "raw_required_participants": raw_participants,
        "raw_required_clusters": raw_clusters,
        **allocation,
        "analysis_participants_per_cluster": m,
        "recruited_participants_per_cluster": recruited_m,
        "final_total_participants": final_participants,
        "rounding_rule": "inflate cluster and individual attrition separately, then round clusters to a complete allocation block",
    }
    if periods > 1:
        payload["final_total_participant_observations"] = next(
            q["value"] for q in quantities if q["key"] == "final_total_participant_observations"
        )
    if extra:
        payload.update(extra)
    result = _envelope(
        method, formula, inputs, primary, quantities,
        [{"role": "individual_equivalent_or_cluster_summary", "component_id": "COMP-QUANTILE-NORMAL", "produced_key": "raw_required_participants"},
         {"role": "cluster_design", "component_id": "COMP-CLUSTER-DESIGN-EFFECT", "produced_key": "raw_required_clusters"},
         {"role": "individual_attrition", "component_id": "COMP-INDIVIDUAL-ATTRITION", "produced_key": "recruited_participants_per_cluster"},
         {"role": "cluster_attrition", "component_id": "COMP-CLUSTER-ATTRITION", "produced_key": "cluster_attrition_adjusted_raw_clusters"},
         {"role": "cluster_allocation", "component_id": "COMP-CLUSTER-DIVISIBILITY", "produced_key": "final_total_clusters"}],
        chapter=12, examples=chapter_examples, tables=tables,
        discrepancies=discrepancies, extra=payload,
    )
    if float(inputs.get("cluster_size_cv", 0.0)) > 0.7:
        result["warnings"].append("cluster_size_cv exceeds the range described as usual in Chapter 12; perform sensitivity analysis")
    return result


def cluster_parallel_continuous_individual(*, planned_difference: float,
                                           standard_deviation: float,
                                           analysis_cluster_size: int, icc: float,
                                           cluster_size_cv: float = 0.0,
                                           allocation_ratio: float = 1.0,
                                           alpha: float = 0.05, power: float = 0.80,
                                           sides: int = 2, individual_attrition: float = 0.0,
                                           cluster_attrition: float = 0.0,
                                           minimum_clusters: int | None = None) -> dict[str, Any]:
    """TWO-034: equations 12.5-12.10, individual-level continuous analysis."""
    delta = float(planned_difference)
    sd = _positive("standard_deviation", standard_deviation)
    phi = _positive("allocation_ratio", allocation_ratio)
    base, za, zb = _guenther_raw(delta, sd, alpha, power, sides, phi)
    de = cluster_design_effect(cluster_size=analysis_cluster_size, icc=icc,
                               cluster_size_cv=cluster_size_cv)
    raw_participants = base * float(de["value"])
    raw_clusters = raw_participants / analysis_cluster_size
    inputs = {"planned_difference": delta, "standard_deviation": sd,
              "analysis_cluster_size": analysis_cluster_size, "icc": icc,
              "cluster_size_cv": cluster_size_cv, "allocation_ratio": phi,
              "alpha": alpha, "power": power, "sides": sides,
              "individual_attrition": individual_attrition,
              "cluster_attrition": cluster_attrition, "minimum_clusters": minimum_clusters}
    return _cluster_result("TWO-034", "equations 12.5-12.10", inputs,
                           raw_participants, raw_clusters, chapter_examples=["12.1", "12.2"],
                           tables=["Table 12.1"], individual_attrition=individual_attrition,
                           cluster_attrition=cluster_attrition, minimum_clusters=minimum_clusters,
                           extra={"individual_randomized_raw_total": base, "design_effect": de,
                                  "z_alpha": za, "z_power": zb})


def cluster_parallel_continuous_aggregate(*, planned_difference: float,
                                          standard_deviation: float,
                                          analysis_cluster_size: int, icc: float,
                                          allocation_ratio: float = 1.0,
                                          alpha: float = 0.05, power: float = 0.80,
                                          sides: int = 2, individual_attrition: float = 0.0,
                                          cluster_attrition: float = 0.0,
                                          minimum_clusters: int | None = None) -> dict[str, Any]:
    """TWO-035: equations 12.1 and 12.11, cluster-level continuous analysis."""
    sd = _positive("standard_deviation", standard_deviation)
    phi = _positive("allocation_ratio", allocation_ratio)
    de = cluster_design_effect(cluster_size=analysis_cluster_size, icc=icc)
    cluster_mean_sd = sd * sqrt(float(de["value"]) / analysis_cluster_size)
    raw_clusters, za, zb = _guenther_raw(float(planned_difference), cluster_mean_sd,
                                        alpha, power, sides, phi)
    raw_participants = raw_clusters * analysis_cluster_size
    inputs = {"planned_difference": planned_difference, "standard_deviation": sd,
              "analysis_cluster_size": analysis_cluster_size, "icc": icc,
              "allocation_ratio": phi, "alpha": alpha, "power": power, "sides": sides,
              "individual_attrition": individual_attrition,
              "cluster_attrition": cluster_attrition, "minimum_clusters": minimum_clusters}
    return _cluster_result("TWO-035", "equations 12.1 and 12.11", inputs,
                           raw_participants, raw_clusters, chapter_examples=["12.3"],
                           tables=["Table 12.1"], individual_attrition=individual_attrition,
                           cluster_attrition=cluster_attrition, minimum_clusters=minimum_clusters,
                           extra={"cluster_mean_standard_deviation": cluster_mean_sd,
                                  "design_effect": de, "z_alpha": za, "z_power": zb})


def cluster_parallel_binary_individual(*, standard_proportion: float,
                                       treatment_proportion: float,
                                       analysis_cluster_size: int, icc: float,
                                       cluster_size_cv: float = 0.0,
                                       allocation_ratio: float = 1.0,
                                       alpha: float = 0.05, power: float = 0.80,
                                       sides: int = 2, individual_attrition: float = 0.0,
                                       cluster_attrition: float = 0.0,
                                       minimum_clusters: int | None = None) -> dict[str, Any]:
    """TWO-036: equations 12.10 and 12.12-12.14."""
    ps = _proportion("standard_proportion", standard_proportion)
    pt = _proportion("treatment_proportion", treatment_proportion)
    phi = _positive("allocation_ratio", allocation_ratio)
    pooled = (ps + pt) / 2
    # Chapter 12 Example 12.4 uses the stated pooled approximation in 12.12.
    planning_sd = sqrt(pooled * (1 - pooled))
    base, za, zb = _guenther_raw(pt - ps, planning_sd, alpha, power, sides, phi)
    de = cluster_design_effect(cluster_size=analysis_cluster_size, icc=icc,
                               cluster_size_cv=cluster_size_cv)
    raw_participants = base * float(de["value"])
    raw_clusters = raw_participants / analysis_cluster_size
    inputs = {"standard_proportion": ps, "treatment_proportion": pt,
              "analysis_cluster_size": analysis_cluster_size, "icc": icc,
              "cluster_size_cv": cluster_size_cv, "allocation_ratio": phi,
              "alpha": alpha, "power": power, "sides": sides,
              "individual_attrition": individual_attrition,
              "cluster_attrition": cluster_attrition, "minimum_clusters": minimum_clusters}
    return _cluster_result("TWO-036", "equations 12.10 and 12.12-12.14", inputs,
                           raw_participants, raw_clusters, chapter_examples=["12.4"],
                           tables=["Table 12.1"], individual_attrition=individual_attrition,
                           cluster_attrition=cluster_attrition, minimum_clusters=minimum_clusters,
                           extra={"individual_randomized_raw_total": base,
                                  "pooled_proportion": pooled,
                                  "planning_standard_deviation": planning_sd,
                                  "design_effect": de, "z_alpha": za, "z_power": zb})


def cluster_parallel_binary_aggregate(*, standard_proportion: float,
                                      treatment_proportion: float,
                                      cluster_proportion_sd: float,
                                      analysis_cluster_size: int,
                                      allocation_ratio: float = 1.0,
                                      alpha: float = 0.05, power: float = 0.80,
                                      sides: int = 2, individual_attrition: float = 0.0,
                                      cluster_attrition: float = 0.0,
                                      minimum_clusters: int | None = None) -> dict[str, Any]:
    """TWO-037: equations 12.1, 12.13 and 12.15."""
    ps = _proportion("standard_proportion", standard_proportion)
    pt = _proportion("treatment_proportion", treatment_proportion)
    sd = _positive("cluster_proportion_sd", cluster_proportion_sd)
    phi = _positive("allocation_ratio", allocation_ratio)
    raw_clusters, za, zb = _guenther_raw(pt - ps, sd, alpha, power, sides, phi)
    raw_participants = raw_clusters * analysis_cluster_size
    inputs = {"standard_proportion": ps, "treatment_proportion": pt,
              "cluster_proportion_sd": sd, "analysis_cluster_size": analysis_cluster_size,
              "allocation_ratio": phi, "alpha": alpha, "power": power, "sides": sides,
              "individual_attrition": individual_attrition,
              "cluster_attrition": cluster_attrition, "minimum_clusters": minimum_clusters}
    return _cluster_result("TWO-037", "equations 12.1, 12.13 and 12.15", inputs,
                           raw_participants, raw_clusters, chapter_examples=["12.5"],
                           individual_attrition=individual_attrition,
                           cluster_attrition=cluster_attrition, minimum_clusters=minimum_clusters,
                           extra={"z_alpha": za, "z_power": zb})


def cluster_parallel_ordinal(*, average_category_proportions: list[float],
                             planned_odds_ratio: float, analysis_cluster_size: int,
                             icc: float, cluster_size_cv: float = 0.0,
                             allocation_ratio: float = 1.0, alpha: float = 0.05,
                             power: float = 0.80, sides: int = 2,
                             individual_attrition: float = 0.0,
                             cluster_attrition: float = 0.0,
                             minimum_clusters: int | None = None) -> dict[str, Any]:
    """TWO-038: equations 12.16 and 12.17."""
    if not isinstance(average_category_proportions, list) or len(average_category_proportions) < 3:
        raise ValueError("average_category_proportions must have at least three categories")
    probs = [float(v) for v in average_category_proportions]
    if any(not isfinite(v) or v <= 0 or v >= 1 for v in probs) or abs(sum(probs) - 1) > 1e-9:
        raise ValueError("average_category_proportions must be positive and sum to 1")
    odds_ratio = _positive("planned_odds_ratio", planned_odds_ratio)
    if odds_ratio == 1:
        raise ValueError("planned_odds_ratio must differ from 1")
    phi = _positive("allocation_ratio", allocation_ratio)
    za, zb = _critical(alpha, power, sides)
    gamma = 3 / (1 - sum(p ** 3 for p in probs))
    de = cluster_design_effect(cluster_size=analysis_cluster_size, icc=icc,
                               cluster_size_cv=cluster_size_cv)
    raw_participants = float(de["value"]) * gamma * (1 + phi) ** 2 / phi * (za + zb) ** 2 / log(odds_ratio) ** 2
    raw_clusters = raw_participants / analysis_cluster_size
    inputs = {"average_category_proportions": probs, "planned_odds_ratio": odds_ratio,
              "analysis_cluster_size": analysis_cluster_size, "icc": icc,
              "cluster_size_cv": cluster_size_cv, "allocation_ratio": phi,
              "alpha": alpha, "power": power, "sides": sides,
              "individual_attrition": individual_attrition,
              "cluster_attrition": cluster_attrition, "minimum_clusters": minimum_clusters}
    return _cluster_result("TWO-038", "equations 12.16 and 12.17", inputs,
                           raw_participants, raw_clusters, chapter_examples=["12.6"],
                           individual_attrition=individual_attrition,
                           cluster_attrition=cluster_attrition, minimum_clusters=minimum_clusters,
                           extra={"gamma": gamma, "design_effect": de,
                                  "z_alpha": za, "z_power": zb})


def cluster_parallel_rates(*, standard_rate: float, treatment_rate: float,
                           standard_rate_cv: float, treatment_rate_cv: float,
                           analysis_cluster_size: int, followup_time: float,
                           allocation_ratio: float = 1.0, alpha: float = 0.05,
                           power: float = 0.80, sides: int = 2,
                           individual_attrition: float = 0.0,
                           cluster_attrition: float = 0.0,
                           minimum_clusters: int | None = None) -> dict[str, Any]:
    """TWO-039: equations 12.18 and 12.19."""
    ls = _positive("standard_rate", standard_rate)
    lt = _positive("treatment_rate", treatment_rate)
    if ls == lt:
        raise ValueError("standard_rate and treatment_rate must differ")
    cvs = float(standard_rate_cv); cvt = float(treatment_rate_cv)
    if any(not isfinite(v) or v < 0 for v in (cvs, cvt)):
        raise ValueError("rate CV values must be finite and >= 0")
    m = _integer("analysis_cluster_size", analysis_cluster_size)
    followup = _positive("followup_time", followup_time)
    phi = _positive("allocation_ratio", allocation_ratio)
    za, zb = _critical(alpha, power, sides)
    raw_clusters = (1 + phi) * (
        (ls + phi * lt) / (m * followup * phi)
        + cvs ** 2 * ls ** 2 + cvt ** 2 * lt ** 2
    ) * (za + zb) ** 2 / (ls - lt) ** 2 + za ** 2 / 2
    raw_participants = raw_clusters * m
    inputs = {"standard_rate": ls, "treatment_rate": lt,
              "standard_rate_cv": cvs, "treatment_rate_cv": cvt,
              "analysis_cluster_size": m, "followup_time": followup,
              "allocation_ratio": phi, "alpha": alpha, "power": power,
              "sides": sides, "individual_attrition": individual_attrition,
              "cluster_attrition": cluster_attrition, "minimum_clusters": minimum_clusters}
    result = _cluster_result("TWO-039", "equations 12.18 and 12.19", inputs,
                             raw_participants, raw_clusters, chapter_examples=["12.7"],
                             individual_attrition=individual_attrition,
                             cluster_attrition=cluster_attrition, minimum_clusters=minimum_clusters,
                             extra={"z_alpha": za, "z_power": zb})
    result["final_total_person_time"] = result["final_total_participants"] * followup
    result["quantities"].append({"key": "final_total_person_time", "value": result["final_total_person_time"],
                                 "quantity": "person_time", "unit": "person_time", "stage": "final"})
    result["related_quantities"] = [q for q in result["quantities"] if q != result["primary_result"]]
    return result


def cluster_parallel_survival(*, standard_event_free_probability: float,
                              treatment_event_free_probability: float,
                              analysis_cluster_size: int, icc: float,
                              cluster_size_cv: float = 0.0,
                              allocation_ratio: float = 1.0,
                              alpha: float = 0.05, power: float = 0.80,
                              sides: int = 2, individual_attrition: float = 0.0,
                              cluster_attrition: float = 0.0,
                              minimum_clusters: int | None = None) -> dict[str, Any]:
    """TWO-040: equations 12.20 and 12.21."""
    gs = _proportion("standard_event_free_probability", standard_event_free_probability)
    gt = _proportion("treatment_event_free_probability", treatment_event_free_probability)
    hr = log(gt) / log(gs)
    if hr == 1:
        raise ValueError("event-free probabilities imply HR=1 and no finite sample size")
    phi = _positive("allocation_ratio", allocation_ratio)
    za, zb = _critical(alpha, power, sides)
    de = cluster_design_effect(cluster_size=analysis_cluster_size, icc=icc,
                               cluster_size_cv=cluster_size_cv)
    raw_participants = float(de["value"]) * (1 + phi) / phi * (
        (1 + phi * hr) / (1 - hr)
    ) ** 2 * (za + zb) ** 2 / ((1 - gs) + phi * (1 - gt))
    raw_clusters = raw_participants / analysis_cluster_size
    inputs = {"standard_event_free_probability": gs,
              "treatment_event_free_probability": gt,
              "analysis_cluster_size": analysis_cluster_size, "icc": icc,
              "cluster_size_cv": cluster_size_cv, "allocation_ratio": phi,
              "alpha": alpha, "power": power, "sides": sides,
              "individual_attrition": individual_attrition,
              "cluster_attrition": cluster_attrition, "minimum_clusters": minimum_clusters}
    return _cluster_result("TWO-040", "equations 12.20 and 12.21", inputs,
                           raw_participants, raw_clusters, chapter_examples=["12.8"],
                           discrepancies=["CH12-SURVIVAL-EVENT-FREE-DIRECTION"],
                           individual_attrition=individual_attrition,
                           cluster_attrition=cluster_attrition, minimum_clusters=minimum_clusters,
                           extra={"planned_hazard_ratio": hr, "design_effect": de,
                                  "z_alpha": za, "z_power": zb})


def cluster_matched_continuous(*, planned_difference: float,
                               paired_cluster_summary_sd: float,
                               analysis_cluster_size: int, icc: float,
                               alpha: float = 0.05, power: float = 0.80,
                               sides: int = 2, individual_attrition: float = 0.0,
                               cluster_attrition: float = 0.0,
                               minimum_pairs: int | None = None) -> dict[str, Any]:
    """TWO-041: equation 12.22."""
    delta = float(planned_difference)
    if not isfinite(delta) or delta == 0:
        raise ValueError("planned_difference must be finite and nonzero")
    sd = _positive("paired_cluster_summary_sd", paired_cluster_summary_sd)
    de = cluster_design_effect(cluster_size=analysis_cluster_size, icc=icc)
    za, zb = _critical(alpha, power, sides)
    raw_pairs = float(de["value"]) * (
        2 * (za + zb) ** 2 / (delta / sd) ** 2 + za ** 2 / 2
    )
    attrition = _probability("cluster_attrition", cluster_attrition, allow_zero=True)
    adjusted_pairs = raw_pairs / (1 - attrition)
    if minimum_pairs is not None:
        adjusted_pairs = max(adjusted_pairs, _integer("minimum_pairs", minimum_pairs))
    final_pairs = ceil(adjusted_pairs)
    final_clusters = 2 * final_pairs
    ind_attr = _probability("individual_attrition", individual_attrition, allow_zero=True)
    recruited_m = ceil(_integer("analysis_cluster_size", analysis_cluster_size) / (1 - ind_attr))
    final_participants = final_clusters * recruited_m
    quantities = [
        {"key": "raw_cluster_pairs", "value": raw_pairs, "quantity": "cluster_pairs", "unit": "cluster_pair", "stage": "raw"},
        {"key": "cluster_attrition_adjusted_pairs", "value": adjusted_pairs, "quantity": "cluster_pairs", "unit": "cluster_pair", "stage": "design_constrained"},
        {"key": "final_cluster_pairs", "value": final_pairs, "quantity": "cluster_pairs", "unit": "cluster_pair", "stage": "final"},
        {"key": "final_total_clusters", "value": final_clusters, "quantity": "clusters", "unit": "cluster", "stage": "final"},
        {"key": "final_participants_per_cluster", "value": recruited_m, "quantity": "participants", "unit": "participant_per_cluster", "stage": "design_constrained"},
        {"key": "final_total_participants", "value": final_participants, "quantity": "participants", "unit": "participant", "stage": "final"},
    ]
    inputs = {"planned_difference": delta, "paired_cluster_summary_sd": sd,
              "analysis_cluster_size": analysis_cluster_size, "icc": icc,
              "allocation_ratio": 1.0, "alpha": alpha, "power": power, "sides": sides,
              "individual_attrition": individual_attrition,
              "cluster_attrition": cluster_attrition, "minimum_pairs": minimum_pairs}
    return _envelope(
        "TWO-041", "equation 12.22", inputs,
        next(q for q in quantities if q["key"] == "final_total_clusters"), quantities,
        [{"role": "matched_cluster_pairs", "component_id": "COMP-MATCHED-CLUSTER-PAIR", "produced_key": "raw_cluster_pairs"},
         {"role": "pair_divisibility", "component_id": "COMP-CLUSTER-DIVISIBILITY", "produced_key": "final_total_clusters"}],
        chapter=12, examples=["12.9"], discrepancies=["CH12-MATCHED-EQUATION-REFERENCE"],
        extra={"raw_total": raw_pairs * 2 * analysis_cluster_size,
               "rounded_total": ceil(raw_pairs) * 2 * analysis_cluster_size,
               "final_total": final_participants, "raw_cluster_pairs": raw_pairs,
               "final_cluster_pairs": final_pairs, "final_total_clusters": final_clusters,
               "final_total_participants": final_participants, "design_effect": de,
               "z_alpha": za, "z_power": zb,
               "rounding_rule": "inflate pair loss, ceil cluster pairs, and retain two clusters per pair"},
    )


def cluster_crossover_continuous(*, planned_difference: float,
                                 standard_deviation: float,
                                 analysis_cluster_size: int,
                                 within_period_cluster_correlation: float,
                                 between_period_individual_correlation: float,
                                 alpha: float = 0.05, power: float = 0.80,
                                 sides: int = 2, individual_attrition: float = 0.0,
                                 cluster_attrition: float = 0.0,
                                 minimum_clusters: int | None = None) -> dict[str, Any]:
    """TWO-042: equations 12.23 and 12.24."""
    delta = float(planned_difference)
    sd = _positive("standard_deviation", standard_deviation)
    if not isfinite(delta) or delta == 0:
        raise ValueError("planned_difference must be finite and nonzero")
    m = _integer("analysis_cluster_size", analysis_cluster_size)
    eta = _probability("within_period_cluster_correlation", within_period_cluster_correlation, allow_zero=True)
    omega = _probability("between_period_individual_correlation", between_period_individual_correlation, allow_zero=True)
    de = 1 + (m - 1) * eta - m * omega
    if de <= 0:
        raise ValueError("cluster-crossover design effect must be positive")
    za, zb = _critical(alpha, power, sides)
    raw_participants = de * (2 * (za + zb) ** 2 / (delta / sd) ** 2 + za ** 2 / 2)
    raw_clusters = raw_participants / m
    inputs = {"planned_difference": delta, "standard_deviation": sd,
              "analysis_cluster_size": m,
              "within_period_cluster_correlation": eta,
              "between_period_individual_correlation": omega,
              "allocation_ratio": 1.0, "alpha": alpha, "power": power,
              "sides": sides, "individual_attrition": individual_attrition,
              "cluster_attrition": cluster_attrition, "minimum_clusters": minimum_clusters}
    return _cluster_result(
        "TWO-042", "equations 12.23 and 12.24", inputs,
        raw_participants, raw_clusters, chapter_examples=["12.10"],
        tables=["Table 12.2"], discrepancies=["CH12-CROSSOVER-DE-TYPO"],
        individual_attrition=individual_attrition, cluster_attrition=cluster_attrition,
        minimum_clusters=minimum_clusters, force_even=True, periods=2,
        same_participants_across_periods=True,
        extra={"cluster_crossover_design_effect": de, "number_of_sequences": 2,
               "number_of_periods": 2, "z_alpha": za, "z_power": zb},
    )


MULTI_CLUSTER_PROCEDURES: dict[str, Callable[..., dict[str, Any]]] = {
    "MULTI-001.SAMPLE_SIZE": multi_unstructured_binary,
    "MULTI-002.SAMPLE_SIZE": multi_dose_response_continuous,
    "MULTI-003.SAMPLE_SIZE": multi_shared_reference_binary,
    "MULTI-004.SAMPLE_SIZE": multi_shared_reference_continuous,
    "MULTI-005.SAMPLE_SIZE": multi_factorial_continuous,
    "TWO-034.SAMPLE_SIZE": cluster_parallel_continuous_individual,
    "TWO-035.SAMPLE_SIZE": cluster_parallel_continuous_aggregate,
    "TWO-036.SAMPLE_SIZE": cluster_parallel_binary_individual,
    "TWO-037.SAMPLE_SIZE": cluster_parallel_binary_aggregate,
    "TWO-038.SAMPLE_SIZE": cluster_parallel_ordinal,
    "TWO-039.SAMPLE_SIZE": cluster_parallel_rates,
    "TWO-040.SAMPLE_SIZE": cluster_parallel_survival,
    "TWO-041.SAMPLE_SIZE": cluster_matched_continuous,
    "TWO-042.SAMPLE_SIZE": cluster_crossover_continuous,
    "CLUSTER-FIXED-CONTINUOUS.REQUIRED_CLUSTER_SIZE": fixed_cluster_continuous_required_size,
    "CLUSTER-FIXED-BINARY.REQUIRED_CLUSTER_SIZE": fixed_cluster_binary_required_size,
}
