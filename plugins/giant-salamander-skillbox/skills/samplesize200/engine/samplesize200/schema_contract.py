"""Provisional internal result contract for safe calculation composition.

This module is intentionally not a public compatibility promise.  It adds
typed quantity records beside the inherited Chapter 3--20 fields so new
composite methods never need to guess what ``raw_total`` means.
"""

from __future__ import annotations

from functools import wraps
from math import isfinite
from typing import Any, Callable, Iterable, Mapping

STAGES = frozenset({"raw", "rounded", "allocation_adjusted", "design_constrained", "final"})
QUANTITIES = frozenset({
    "participants", "pairs", "matched_units", "events", "person_time",
    "specimens", "ratings", "repeated_specimens", "raters",
})
UNITS = frozenset({
    "participants", "pairs", "matched_units", "events", "person_time",
    "person", "specimen", "rating", "repeated_specimen", "rater",
})
FUTURE_QUANTITY_CANDIDATES = ("clusters", "cluster_pairs")

_CHAPTER_METHODS = {
    3: {"ONE-001", "TWO-001", "TWO-002", "TWO-003"},
    4: {"TWO-004", "TWO-005", "TWO-006", "TWO-007"},
    5: {"ONE-002", "TWO-008", "TWO-009", "TWO-010", "TWO-011", "TWO-012"},
    6: {"ONE-003", "ONE-004", "TWO-013", "TWO-014", "TWO-015", "TWO-016"},
    8: {"TWO-023", "TWO-024", "TWO-025", "TWO-026", "TWO-027", "TWO-028", "TWO-029", "TWO-030"},
    9: {f"CI-{number:03d}" for number in range(1, 13)},
    10: {"TWO-031", "TWO-032", "TWO-033"},
    7: {"TWO-017", "TWO-018", "TWO-019", "TWO-020", "TWO-021", "TWO-022"},
    19: {f"CORR-{number:03d}" for number in range(1, 6)},
    20: {f"AGREE-{number:03d}" for number in range(1, 11)},
    21: {f"DIAG-{number:03d}" for number in range(1, 8)},
}

_TABLE_METHODS = {
    "TWO-001", "TWO-002", "ONE-002", "TWO-009", "TWO-010", "TWO-012",
    "ONE-003", "ONE-004", "TWO-015", "TWO-016", "TWO-023", "TWO-029",
    "CI-003", "CI-006", "CI-007", "CI-008", "CI-009", "CI-011", "CI-012",
    "TWO-031",
    "TWO-017", "TWO-018", "TWO-019",
    "CORR-001", "CORR-003", "CORR-005",
    *{f"AGREE-{number:03d}" for number in (2, 3, 5, 7, 8, 9, 10)},
    *{f"DIAG-{number:03d}" for number in range(1, 8)},
}
_EXAMPLE_METHODS = {
    "ONE-001", "ONE-002", "ONE-003", "ONE-004",
    "TWO-001", "TWO-002", "TWO-003", "TWO-004", "TWO-005", "TWO-007",
    "TWO-009", "TWO-010", "TWO-011", "TWO-012", "TWO-013", "TWO-014",
    "TWO-015", "TWO-016", "TWO-023", "TWO-024", "TWO-025", "TWO-026",
    "TWO-027", "TWO-028", "TWO-029",
    *{f"CI-{number:03d}" for number in range(1, 13)},
    "TWO-031", "TWO-032", "TWO-033",
    "TWO-017", "TWO-018", "TWO-019",
    *{f"CORR-{number:03d}" for number in range(1, 6)},
    *{f"AGREE-{number:03d}" for number in range(1, 11)},
    *{f"DIAG-{number:03d}" for number in range(1, 8)},
}

_SOURCE_DISCREPANCIES = {
    "TWO-003": ["CH03-EQ3.5-MARKDOWN-PDF"],
    "TWO-004": ["CH04-EX4.1-GAMMA-ARITHMETIC"],
    "TWO-023": ["CH08-TABLE8.1-PUBLISHED-TYPOGRAPHY"],
    "TWO-029": ["CH08-TABLE8.2-PUBLISHED-DECIMAL-SHIFT"],
    "CI-003": ["CH09-EX9.2-WILSON-PUBLISHED-VALUE"],
    "CI-012": ["CH09-EX9.10-INTERMEDIATE-RAW"],
    "TWO-020": ["CH07-COMPETING-EVENT-EQUATION"],
    "TWO-021": ["CH07-COMPETING-EVENT-EQUATION"],
    "TWO-022": ["CH07-COMPETING-EVENT-EQUATION"],
    "CORR-001": ["CH19-TABLE-INTEGERIZATION"],
    "CORR-003": ["CH19-TABLE-INTEGERIZATION", "CH19-EX19.5-TABLE19.2-RHO06"],
    "CORR-004": ["CH19-EX19.6-SPEARMAN-ARITHMETIC"],
    "CORR-005": ["CH19-TABLE-INTEGERIZATION"],
    **{f"AGREE-{number:03d}": ["CH20-TABLE-DIFFERENCES-11-CELLS"]
       for number in (2, 3, 7, 9, 10)},
    "DIAG-002": ["CH21-EX21.2-TABLE-ROUNDING"],
    "DIAG-003": ["CH21-EQ21.15-ALPHA-NOTATION"],
    "DIAG-004": ["CH21-TABLE21.3-EXACT-RULE", "CH21-TABLE21.3-CELL-TYPO"],
    "DIAG-005": ["CH21-TABLE21.4-SOURCE-TYPOS"],
    "DIAG-006": ["CH21-TABLE21.5-SOURCE-TYPO", "CH21-EX21.4-INPUT-CHANGE"],
    "DIAG-007": ["CH21-EX21.5-ORIGINAL-ROUNDING"],
}


def _chapter(method_id: str) -> int:
    for chapter, methods in _CHAPTER_METHODS.items():
        if method_id in methods:
            return chapter
    raise ValueError(f"no chapter metadata registered for {method_id}")


def quantity_record(*, key: str, value: float | int, quantity: str, unit: str,
                    stage: str) -> dict[str, Any]:
    if quantity not in QUANTITIES:
        raise ValueError(f"unsupported provisional quantity: {quantity}")
    if unit not in UNITS:
        raise ValueError(f"unsupported provisional unit: {unit}")
    if stage not in STAGES:
        raise ValueError(f"unsupported calculation stage: {stage}")
    numeric = float(value)
    if not isfinite(numeric) or numeric < 0:
        raise ValueError(f"{key} must be a finite nonnegative numeric quantity")
    return {"key": key, "value": value, "quantity": quantity, "unit": unit, "stage": stage}


def _append(records: list[dict[str, Any]], result: Mapping[str, Any], key: str,
            quantity: str, unit: str, stage: str) -> None:
    value = result.get(key)
    if value is not None:
        records.append(quantity_record(key=key, value=value, quantity=quantity, unit=unit, stage=stage))


def _legacy_quantity_records(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    method = str(result["method_id"])
    records: list[dict[str, Any]] = []

    if method.startswith("CORR-"):
        _append(records, result, "raw_participants", "participants", "person", "raw")
        _append(records, result, "rounded_participants", "participants", "person", "rounded")
        _append(records, result, "final_participants", "participants", "person", "final")
        return records

    if method.startswith("AGREE-"):
        _append(records, result, "raw_specimens", "specimens", "specimen", "raw")
        _append(records, result, "rounded_specimens", "specimens", "specimen", "rounded")
        _append(records, result, "final_specimens", "specimens", "specimen", "final")
        _append(records, result, "raw_repeated_specimens", "repeated_specimens", "repeated_specimen", "raw")
        _append(records, result, "rounded_repeated_specimens", "repeated_specimens", "repeated_specimen", "rounded")
        _append(records, result, "final_repeated_specimens", "repeated_specimens", "repeated_specimen", "design_constrained")
        _append(records, result, "raw_total_ratings", "ratings", "rating", "raw")
        _append(records, result, "final_total_ratings", "ratings", "rating", "final")
        _append(records, result, "final_raters", "raters", "rater", "final")
        return records

    if method.startswith("DIAG-"):
        role_keys = {
            "reference": "reference_participants",
            "information": "information_participants",
            "disease": "disease_participants",
            "nondisease": "nondisease_participants",
            "test_a": "test_a_participants",
            "test_b": "test_b_participants",
            "paired": "paired_participants",
            "total": "total_participants",
        }
        stage_prefixes = {
            "raw": "raw", "rounded": "rounded",
            "allocation_adjusted": "allocation_adjusted", "final": "final",
        }
        for prefix, stage in stage_prefixes.items():
            for stem in role_keys.values():
                _append(records, result, f"{prefix}_{stem}", "participants", "person", stage)
        _append(records, result, "raw_total", "participants", "person", "raw")
        _append(records, result, "rounded_total", "participants", "person", "rounded")
        _append(records, result, "final_total", "participants", "person", "final")
        return records

    if method in {"TWO-017", "TWO-018"}:
        _append(records, result, "raw_events", "events", "events", "raw")
        _append(records, result, "rounded_events", "events", "events", "rounded")
        _append(records, result, "final_events", "events", "events", "final")
        return records

    if method in {"TWO-019", "TWO-020", "TWO-021", "TWO-022"}:
        _append(records, result, "raw_required_events", "events", "events", "raw")
        _append(records, result, "rounded_required_events", "events", "events", "rounded")

    if method == "TWO-016":
        _append(records, result, "raw_matched_units", "matched_units", "matched_units", "raw")
        _append(records, result, "rounded_matched_units", "matched_units", "matched_units", "rounded")
        _append(records, result, "final_matched_units", "matched_units", "matched_units", "design_constrained")
        _append(records, result, "final_cases", "participants", "participants", "final")
        _append(records, result, "final_controls", "participants", "participants", "final")
        _append(records, result, "raw_subject_total", "participants", "participants", "raw")
        _append(records, result, "final_total", "participants", "participants", "final")
        return records

    if "raw_pairs" in result:
        _append(records, result, "raw_pairs", "pairs", "pairs", "raw")
        _append(records, result, "rounded_pairs", "pairs", "pairs", "rounded")
        _append(records, result, "constraint_adjusted_pairs", "pairs", "pairs", "design_constrained")
        _append(records, result, "final_pairs", "pairs", "pairs", "final")

    _append(records, result, "raw_total", "participants", "participants", "raw")
    _append(records, result, "rounded_total", "participants", "participants", "rounded")
    for key in ("rounded_group_control", "rounded_group_treatment"):
        _append(records, result, key, "participants", "participants", "rounded")
    for key in ("raw_group_control", "raw_group_treatment"):
        _append(records, result, key, "participants", "participants", "raw")
    for key in ("final_group_control", "final_group_treatment"):
        _append(records, result, key, "participants", "participants", "allocation_adjusted")
    _append(records, result, "final_total", "participants", "participants", "final")

    if method == "TWO-013":
        _append(records, result, "raw_total_exposure", "person_time", "person_time", "raw")
        _append(records, result, "raw_group_control_exposure", "person_time", "person_time", "raw")
        _append(records, result, "raw_group_treatment_exposure", "person_time", "person_time", "raw")
    return records


def source_provenance_for(result: Mapping[str, Any]) -> dict[str, Any]:
    method = str(result["method_id"])
    chapter = _chapter(method)
    return {
        "chapter": chapter,
        "equation_or_section": result.get("formula_reference"),
        "preferred_source": "医学研究のためのサンプルサイズ設計_20220330.pdf",
        "source_discrepancy_ids": list(_SOURCE_DISCREPANCIES.get(method, ())),
    }


def validation_evidence_for(method_id: str) -> dict[str, Any]:
    chapter = _chapter(method_id)
    prefix = f"chapter{chapter:02d}"
    if method_id in {"TWO-020", "TWO-021", "TWO-022"}:
        example_fixtures = [f"validation/chapter07_competing_examples.yaml::method_id={method_id}"]
    elif method_id in _EXAMPLE_METHODS:
        example_fixtures = [f"validation/{prefix}_examples.yaml::method_id={method_id}"]
    else:
        example_fixtures = []
    audit_fixture = (
        f"tests/test_chapter07_competing_independent_audit.py::{method_id}"
        if method_id in {"TWO-020", "TWO-021", "TWO-022"}
        else f"tests/test_{prefix}_independent_audit.py::{method_id}"
    )
    return {
        "scope": "method_implementation",
        "input_match_claim": False,
        "fixed_table_fixture_ids": [f"validation/{prefix}_tables.csv::method_id={method_id}"] if method_id in _TABLE_METHODS else [],
        "example_fixture_ids": example_fixtures,
        "independent_audit_case_ids": [audit_fixture],
        "discrepancy_ids": list(_SOURCE_DISCREPANCIES.get(method_id, ())),
    }


def attach_result_contract(result: dict[str, Any]) -> dict[str, Any]:
    """Attach typed quantities and separate source/evidence metadata in place."""
    result["quantities"] = _legacy_quantity_records(result)
    result["source_provenance"] = source_provenance_for(result)
    result["validation_evidence"] = validation_evidence_for(str(result["method_id"]))
    return result


def contracted(function: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """Decorate a public calculation without changing its numerical fields."""
    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return attach_result_contract(function(*args, **kwargs))
    return wrapper


def consume_quantity(parent_result: Mapping[str, Any], *, allowed_parent_methods: Iterable[str],
                     key: str, quantity: str, unit: str, stage: str) -> dict[str, Any]:
    """Return an exact typed parent record or reject an unsafe composition."""
    method = parent_result.get("method_id")
    allowed = set(allowed_parent_methods)
    if method not in allowed:
        raise ValueError(f"incompatible parent method {method!r}; expected one of {sorted(allowed)}")
    if quantity not in QUANTITIES or stage not in STAGES:
        raise ValueError("invalid expected parent quantity or stage")
    matches = [
        record for record in parent_result.get("quantities", ())
        if record.get("key") == key
        and record.get("quantity") == quantity
        and record.get("unit") == unit
        and record.get("stage") == stage
    ]
    if len(matches) != 1:
        raise ValueError(
            f"parent result must expose exactly one {key!r} record as "
            f"{quantity}/{unit} at stage {stage}"
        )
    return dict(matches[0])


def correction_lineage(*, parent_result: Mapping[str, Any], consumed: Mapping[str, Any],
                       transformation: str, child_outputs: Iterable[Mapping[str, str]]) -> dict[str, Any]:
    parent_inputs = dict(parent_result.get("inputs", {}))
    inference = {
        key: parent_inputs.get(key)
        for key in ("alpha", "adjusted_alpha", "power", "sides", "confidence_level")
        if key in parent_inputs
    }
    return {
        "calculation_type": "correction",
        "parent_method_id": parent_result.get("method_id"),
        "consumed_result": dict(consumed),
        "parent_primary_inputs": parent_inputs,
        "parent_inference": inference,
        "transformation": transformation,
        "child_outputs": [dict(item) for item in child_outputs],
        "parent_source_provenance": parent_result.get("source_provenance"),
        "parent_validation_evidence": parent_result.get("validation_evidence"),
    }
