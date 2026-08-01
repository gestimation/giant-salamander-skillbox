from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    SkillContractError,
    emit,
    research_example_catalog,
    research_example_index,
    resolve_procedure,
)


MESSAGES = {
    "EXACT": "📚 同じ計算方法・計算目的の研究事例があります。",
    "SAME_METHOD_DIFFERENT_OPERATION": "📚 同じ計算方法を別の計算目的で使った研究事例があります。",
    "RELATED": "📚 近い研究デザインの事例があります。",
}


def _operation(value: str | None) -> str:
    token = str(value or "required_sample_size").strip().lower()
    return {
        "sample_size": "required_sample_size",
        "required_cluster_size": "required_sample_size",
        "achieved_power": "power",
        "detectable effect": "detectable_effect",
    }.get(token, token)


def _formula_key(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def _resolve_for_examples(identifier: str) -> tuple[str, str]:
    index = research_example_index()
    key = index.get("identifier_to_procedure_key", {}).get(identifier)
    if key:
        procedure = index.get("procedures", {}).get(key, {})
        return key, procedure.get("public_id", identifier)
    item = resolve_procedure(identifier)
    return item["procedure_key"], item["public_id"]


def _entry_for(procedure: dict[str, Any], operation: str,
               formula_reference: str | None = None) -> dict[str, Any] | None:
    formula = _formula_key(formula_reference)
    exact = (
        procedure.get("exact_cases_by_operation_and_formula", {})
        .get(operation, {})
        .get(formula, [])
        if formula else []
    )
    if exact:
        return {
            "best_match_type": "EXACT",
            "candidate_case_ids": exact,
            "related_candidates": procedure.get("related_candidates", []),
        }
    same_method = [
        case_id
        for candidate_operation, case_ids in procedure.get("case_ids_by_operation", {}).items()
        if candidate_operation != operation
        for case_id in case_ids
    ]
    if same_method:
        return {
            "best_match_type": "SAME_METHOD_DIFFERENT_OPERATION",
            "candidate_case_ids": same_method,
            "related_candidates": procedure.get("related_candidates", []),
        }
    related = procedure.get("related_candidates", [])
    if related:
        return {
            "best_match_type": "RELATED",
            "candidate_case_ids": [row["case_id"] for row in related],
            "related_candidates": related,
        }
    return None


def offer(identifier: str, *, operation: str = "required_sample_size",
          formula_reference: str | None = None) -> dict[str, Any]:
    """Return offer metadata without loading any detailed example record."""
    normalized_operation = _operation(operation)
    try:
        procedure_key, public_id = _resolve_for_examples(identifier)
    except SkillContractError as exc:
        return {
            "available": False,
            "requested_identifier": identifier,
            "procedure_key": None,
            "public_id": None,
            "operation": normalized_operation,
            "candidate_count": 0,
            "detail_loaded": False,
            "formula_verified": False,
            "error": exc.payload,
        }
    index = research_example_index()
    procedure = index.get("procedures", {}).get(procedure_key, {})
    entry = _entry_for(procedure, normalized_operation, formula_reference)
    if not entry:
        return {
            "available": False,
            "procedure_key": procedure_key,
            "public_id": public_id,
            "operation": normalized_operation,
            "candidate_count": 0,
            "detail_loaded": False,
            "formula_verified": False,
        }
    match_type = entry["best_match_type"]
    return {
        "available": True,
        "procedure_key": procedure_key,
        "public_id": public_id,
        "operation": normalized_operation,
        "best_match_type": match_type,
        "candidate_count": len(entry.get("candidate_case_ids", [])),
        "message": MESSAGES[match_type],
        "candidate_case_ids": entry.get("candidate_case_ids", []),
        "detail_loaded": False,
        "formula_verified": match_type == "EXACT" and _formula_key(formula_reference) is not None,
        "formula_reference": formula_reference,
        "source_inconsistency_excluded": False,
    }


def _group_examples(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for record in records:
        key = record["research_example_id"]
        if key not in groups:
            groups[key] = {
                "research_example_id": key,
                "example_number": record.get("example_number"),
                "title": record.get("title"),
                "scenario_summary": record.get("scenario_summary"),
                "match_type": record["match_type"],
                "source": record.get("source", {}),
                "calculation_cases": [],
            }
        groups[key]["calculation_cases"].append(record)
    return list(groups.values())


def retrieve(identifier: str, *, operation: str = "required_sample_size",
             formula_reference: str | None = None,
             include_related: bool = True, limit: int = 5) -> dict[str, Any]:
    """Load details after opt-in and keep study examples distinct from calculation cases."""
    metadata = offer(identifier, operation=operation, formula_reference=formula_reference)
    if not metadata["available"]:
        return {**metadata, "examples": [], "exact_matches": [], "related_examples": []}
    index = research_example_index()
    entry = _entry_for(
        index["procedures"][metadata["procedure_key"]], metadata["operation"],
        formula_reference,
    )
    assert entry is not None
    catalog = research_example_catalog()
    by_id = {row["case_id"]: row for row in catalog.get("examples", [])}
    selected = []
    primary_type = entry["best_match_type"]
    related_metadata = {
        row["case_id"]: row for row in entry.get("related_candidates", [])
    }
    for case_id in entry.get("candidate_case_ids", []):
        if case_id in by_id:
            selected.append({
                **by_id[case_id],
                "match_type": primary_type,
                **({"match_reasons": related_metadata.get(case_id, {}).get("match_reasons", [])}
                   if primary_type == "RELATED" else {}),
            })
    related = []
    if include_related and primary_type != "RELATED":
        for candidate in entry.get("related_candidates", []):
            record = by_id.get(candidate["case_id"])
            if record:
                related.append({
                    **record,
                    "match_type": "RELATED",
                    "match_reasons": candidate.get("match_reasons", []),
                })
    combined = [*selected, *related]
    grouped = _group_examples(combined)[:max(1, int(limit))]
    return {
        **metadata,
        "detail_loaded": True,
        "examples": grouped,
        "exact_matches": [row["case_id"] for row in selected if row["match_type"] == "EXACT"],
        "same_method_different_operation": [
            row["case_id"] for row in selected
            if row["match_type"] == "SAME_METHOD_DIFFERENT_OPERATION"
        ],
        "related_examples": [row["case_id"] for row in related],
        "warning": "事例の値は別研究の検証情報であり、今回の研究の未指定入力には使用しません。",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--procedure", required=True)
    parser.add_argument("--operation", default="required_sample_size")
    parser.add_argument("--formula-reference")
    parser.add_argument("--offer-only", action="store_true")
    parser.add_argument("--exact-only", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.offer_only:
        emit(offer(
            args.procedure, operation=args.operation,
            formula_reference=args.formula_reference,
        ))
    else:
        emit(retrieve(
            args.procedure, operation=args.operation,
            formula_reference=args.formula_reference,
            include_related=not args.exact_only, limit=args.limit,
        ))


if __name__ == "__main__":
    main()
