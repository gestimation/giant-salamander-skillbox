from __future__ import annotations

from typing import Any

from run_engine import run


RULE_ID = "THREE_GROUP_ALL_PAIRWISE_REPEATED_BONFERRONI"


def applicable(spec: dict[str, Any]) -> bool:
    return (
        spec.get("number_of_groups") == 3
        and spec.get("comparison_scope") == "all_pairwise"
        and spec.get("repeated_measures") is True
        and str(spec.get("multiplicity_strategy") or spec.get("multiplicity") or "").lower() == "bonferroni"
    )


def run_three_group_pairwise(inputs: dict[str, Any], *, familywise_alpha: float,
                             power: float, output_mode: str = "concise",
                             recompute_hash: bool = True) -> dict[str, Any]:
    comparison_count = 3
    per_comparison_alpha = float(familywise_alpha) / comparison_count
    effect = inputs.get("standardized_effect")
    base_inputs = dict(inputs)
    if effect is not None:
        base_inputs.pop("standardized_effect")
        base_inputs.setdefault("planned_mean_difference", float(effect))
        base_inputs.setdefault("planned_sd", 1.0)
    base_inputs.setdefault("pre_measurements", 0)
    base_inputs.update({"alpha": per_comparison_alpha, "power": power, "sides": 2})
    parent = run(
        "TWO-C-009", base_inputs, calculation_target="required_sample_size",
        output_mode="qc", recompute_hash=recompute_hash,
    )
    if parent.get("status") != "CALCULATED":
        return parent
    engine = parent["engine_output"]
    per_group = max(int(engine["final_group_control"]), int(engine["final_group_treatment"]))
    groups = [per_group] * 3
    limitation = (
        "専用3群MMRM法ではなく、検証済み2群反復測定近似法を"
        "Bonferroniで合成した設計です。"
    )
    result = {
        "status": "CALCULATED",
        "composition_rule_id": RULE_ID,
        "public_procedure_counted": False,
        "parent_public_id": "TWO-C-009",
        "calculation_target": "required_sample_size",
        "familywise_alpha": float(familywise_alpha),
        "comparison_count": comparison_count,
        "per_comparison_alpha": per_comparison_alpha,
        "power": power,
        "final_group_sizes": groups,
        "final_total": sum(groups),
        "primary_result": {
            "key": "final_total", "value": sum(groups),
            "quantity": "participants", "unit": "person", "stage": "final",
        },
        "lineage": [{
            "role": "validated_parent_procedure", "public_id": "TWO-C-009",
            "transformation": "Bonferroni familywise alpha / 3 and common maximum per-arm finalization",
            "parent_final_group_control": engine["final_group_control"],
            "parent_final_group_treatment": engine["final_group_treatment"],
        }],
        "method_limitation": limitation,
        "parent_result": parent if output_mode == "qc" else None,
    }
    result["display"] = {
        "output_mode": output_mode,
        "status": "CALCULATED",
        "procedure": "TWO-C-009 (validated two-group parent)",
        "composition_rule": RULE_ID,
        "primary_result": result["primary_result"],
        "group_sizes": groups,
        "power": power,
        "familywise_alpha": float(familywise_alpha),
        "per_comparison_alpha": per_comparison_alpha,
        "method_limitations": [limitation],
    }
    return result
