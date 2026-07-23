from __future__ import annotations

import copy
from typing import Any

from resolution_state import build_resolution_state, make_issue
from study_contract import study_field_contract


SCHEMA_VERSION = "2.0.0"
REMOVED_ALIASES = {
    "operation": "requested_output",
    "calculation_target": "requested_output",
    "requested_public_id": "catalog_procedure_id",
    "requested_engine_id": "engine_procedure_id",
    "requested_procedure_key": "procedure_key",
    "model_id": "engine_model_id",
    "legacy_id": "catalog_procedure_id",
    "calculator_selection": "calculator_selection_constraint",
    "factor_a_levels": "factor_levels",
    "factor_b_levels": "factor_levels",
}


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _removed_alias_issues(value: Any, path: str = "") -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            pointer = f"{path}/{_pointer_token(str(key))}"
            if key in REMOVED_ALIASES:
                issues.append(make_issue(
                    code="DEPRECATED_ALIAS_REMOVED",
                    path=pointer,
                    reason=(
                        f"{key} was removed in SAMPLESIZE200 1.0; "
                        f"use {REMOVED_ALIASES[key]} in the canonical contract."
                    ),
                    blocking=True,
                    expected_type="canonical StudySpec v2 field",
                    candidate_values=[REMOVED_ALIASES[key]],
                    category="conflict",
                ))
            issues.extend(_removed_alias_issues(child, pointer))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(_removed_alias_issues(child, f"{path}/{index}"))
    return issues


def _compatibility_location_issues(study_spec: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    contract = study_field_contract()
    records = {
        **(contract.get("study_fields") or {}),
        **((contract.get("values_namespace") or {}).get("common_fields") or {}),
    }
    for canonical, record in records.items():
        for location in record.get("compatibility_locations") or []:
            parts = [part for part in str(location).split("/") if part]
            cursor: Any = study_spec
            found = True
            for part in parts:
                if not isinstance(cursor, dict) or part not in cursor:
                    found = False
                    break
                cursor = cursor[part]
            if found:
                issues.append(make_issue(
                    code="CANONICAL_LOCATION_REQUIRED",
                    path=str(location),
                    reason=(
                        f"The compatibility location {location} was removed in 1.0; "
                        f"use {record['canonical_location']}."
                    ),
                    blocking=True,
                    expected_type=record.get("data_type"),
                    candidate_values=[record["canonical_location"]],
                    category="conflict",
                ))
    return issues


def validate_canonical_envelope(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Reject removed 0.x inputs before normalization or selection."""
    if not isinstance(payload, dict):
        return [make_issue(
            code="CANONICAL_CONTRACT_REQUIRED", path="/",
            reason="SAMPLESIZE200 1.0 requires a canonical StudySpec v2 request object.",
            blocking=True, expected_type="object", candidate_values=[], category="conflict",
        )]
    issues = _removed_alias_issues(payload)
    study_spec = payload.get("study_spec")
    requests = payload.get("calculation_requests")
    request = payload.get("calculation_request")
    if not isinstance(study_spec, dict) or not (
        isinstance(request, dict) or isinstance(requests, list)
    ):
        issues.append(make_issue(
            code="STUDYSPEC_V1_REMOVED", path="/",
            reason=(
                "Flat StudySpec v1 input was removed in SAMPLESIZE200 1.0; "
                "provide study_spec and calculation_request objects."
            ),
            blocking=True,
            expected_type="StudySpec v2 contract bundle",
            candidate_values=["study_spec", "calculation_request"],
            category="conflict",
        ))
        return issues
    if study_spec.get("schema_version") != SCHEMA_VERSION:
        issues.append(make_issue(
            code="UNSUPPORTED_STUDY_SPEC_VERSION", path="/study_spec/schema_version",
            reason="SAMPLESIZE200 1.0 accepts StudySpec schema_version 2.0.0 only.",
            blocking=True, expected_type="2.0.0", candidate_values=[SCHEMA_VERSION],
            category="conflict",
        ))
    issues.extend(_compatibility_location_issues(study_spec))
    constraint = payload.get("calculator_selection_constraint")
    if constraint is not None:
        if not isinstance(constraint, dict):
            issues.append(make_issue(
                code="CALCULATOR_SELECTION_CONSTRAINT_INVALID",
                path="/calculator_selection_constraint",
                reason="calculator_selection_constraint must be an object.",
                blocking=True, expected_type="object", candidate_values=[], category="conflict",
            ))
        else:
            unknown = sorted(set(constraint) - {"schema_version", "calculator_id"})
            if constraint.get("schema_version") != SCHEMA_VERSION:
                issues.append(make_issue(
                    code="CALCULATOR_SELECTION_CONSTRAINT_VERSION_INVALID",
                    path="/calculator_selection_constraint/schema_version",
                    reason="CalculatorSelectionConstraint schema_version must be 2.0.0.",
                    blocking=True, expected_type="2.0.0", candidate_values=[SCHEMA_VERSION],
                    category="conflict",
                ))
            if not isinstance(constraint.get("calculator_id"), str) or not constraint.get("calculator_id"):
                issues.append(make_issue(
                    code="CALCULATOR_ID_REQUIRED",
                    path="/calculator_selection_constraint/calculator_id",
                    reason="A non-empty CalculatorID is required when a selection constraint is supplied.",
                    blocking=True, expected_type="string", candidate_values=[], category="missing",
                ))
            for name in unknown:
                issues.append(make_issue(
                    code="CALCULATOR_SELECTION_CONSTRAINT_FIELD_UNKNOWN",
                    path=f"/calculator_selection_constraint/{_pointer_token(name)}",
                    reason="Only schema_version and calculator_id are allowed.",
                    blocking=True, expected_type=None, candidate_values=[], category="conflict",
                ))
    return issues


def canonical_input_error(issues: list[dict[str, Any]]) -> dict[str, Any]:
    state = build_resolution_state(copy.deepcopy(issues))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "INVALID_REQUEST",
        "error": {
            "code": str(issues[0]["code"] if issues else "CANONICAL_CONTRACT_REQUIRED"),
            "message": str(issues[0]["reason"] if issues else "Canonical input is required."),
        },
        "reason_codes": [str(issue["code"]) for issue in issues],
        "resolution_state": state,
        "questions": [],
    }
