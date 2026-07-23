from __future__ import annotations

from typing import Any

from retrieve_example import offer as research_example_offer


MMRM_LIMITATION = (
    "一般的なMMRM全般ではなく、完全データ、複合対称相関、共通の測定間相関を仮定し、"
    "指定した介入後時点の平均的群間差を正規近似で扱う設計です。"
)
SMALL_SAMPLE_WARNING = (
    "必要人数が小さいため、近似式による検定特性が十分でない可能性があります。"
    "正確検定またはシミュレーションで確認してください。"
)


def _method_limitations(result: dict[str, Any]) -> list[str]:
    public_id = result.get("public_id")
    limits: list[str] = []
    if public_id == "TWO-C-009":
        limits.append(MMRM_LIMITATION)
    if public_id == "ONE-S-001":
        limits.append("指数分布の生存時間と一様登録を仮定した単群固定時点Kaplan-Meier近似です。")
    return limits


def _concise_warning(result: dict[str, Any]) -> list[str]:
    warnings = list(result.get("warnings", []))
    primary = result.get("final_result") or {}
    if result.get("public_id") == "ONE-B-001" and isinstance(primary.get("value"), int) and primary["value"] < 30:
        warnings.append(SMALL_SAMPLE_WARNING)
    return list(dict.fromkeys(warnings))


def _optional_research_example_offer(result: dict[str, Any]) -> dict[str, Any] | None:
    """Keep optional example metadata from affecting a successful calculation."""
    try:
        offer = research_example_offer(
            result["procedure_key"],
            operation=result.get("calculation_target", "required_sample_size"),
            formula_reference=(result.get("engine_output") or {}).get("formula_reference"),
        )
    except Exception:
        return None
    return offer if offer.get("available") else None


def render(result: dict[str, Any], output_mode: str = "concise",
           defaults_applied: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if output_mode not in {"concise", "detailed", "qc"}:
        raise ValueError("output_mode must be concise, detailed, or qc")
    if result.get("status") != "CALCULATED":
        return {"output_mode": output_mode, "status": result.get("status"), "error": result.get("error")}
    primary = result.get("final_result")
    inputs = result.get("structured_inputs", {})
    concise = {
        "output_mode": output_mode,
        "status": "CALCULATED",
        "procedure": result.get("public_id"),
        "calculation_target": result.get("calculation_target", "required_sample_size"),
        "primary_result": primary,
        "group_or_cluster_allocation": result.get("group_or_cluster_allocation", {}),
        "power": inputs.get("power") if result.get("calculation_target") != "power" else None,
        "beta": None if inputs.get("power") is None or result.get("calculation_target") == "power" else 1.0 - float(inputs["power"]),
        "alpha": inputs.get("alpha"),
        "sidedness": inputs.get("sides"),
        "attrition_adjusted": any(
            "attrition" in key and float(value) > 0
            for key, value in inputs.items() if isinstance(value, (int, float))
        ),
        "method_limitations": _method_limitations(result),
        "defaults_applied": defaults_applied or result.get("defaults_applied", []),
        "warnings": _concise_warning(result),
    }
    if result.get("calculation_target") == "power":
        engine = result.get("engine_output", {})
        concise.update({
            "result_type": "achieved_power",
            "achieved_power": engine.get("achieved_power"),
            "realized_design": engine.get("realized_design"),
            "method": engine.get("method"),
        })
    if result.get("calculation_target") == "required_events":
        concise["optional_next_step"] = "必要なら、群別イベント確率を追加して総被験者数へ変換できます。"
    example_offer = _optional_research_example_offer(result)
    if example_offer is not None:
        concise["research_example_offer"] = example_offer
    if output_mode == "concise":
        return concise
    detailed = {
        **concise,
        "structured_inputs": inputs,
        "raw_result": result.get("raw_result"),
        "rounding_trace": result.get("rounding_trace"),
        "adjustment_trace": result.get("adjustment_trace"),
        "provenance_reference": result.get("provenance_reference"),
    }
    if output_mode == "detailed":
        return detailed
    engine = result.get("engine_output", {})
    return {
        **detailed,
        "qc": {
            "method_id": engine.get("method_id"),
            "method_aliases": result.get("method_aliases", []),
            "formula_id": engine.get("formula_reference"),
            "input_parameters": engine.get("inputs", inputs),
            "derived_parameters": engine.get("intermediate", engine.get("calculation_stages", [])),
            "rounding_rule": engine.get("rounding_rule"),
            "validation_status": "VALIDATED_PUBLIC_PROCEDURE",
            "software_version": (result.get("engine_compatibility") or {}).get("version"),
            "warnings": engine.get("warnings", []),
            "lineage": engine.get("procedure_lineage", engine.get("lineage")),
        },
    }
