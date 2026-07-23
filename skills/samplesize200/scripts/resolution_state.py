from __future__ import annotations

import copy
from typing import Any, Iterable


SCHEMA_VERSION = "2.0.0"
ISSUE_CATEGORIES = {"missing", "uncertain", "conflict", "unsupported", "warning"}


def _token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def field_path(value: Any, *, default_root: str = "/values") -> str:
    text = str(value or "")
    if text.startswith("/"):
        return text
    return f"{default_root}/{_token(text or 'unknown')}"


def make_issue(
    *, code: str, path: str, reason: str, blocking: bool,
    expected_type: Any = None, candidate_values: Iterable[Any] | None = None,
    category: str = "conflict", details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if category not in ISSUE_CATEGORIES:
        category = "conflict"
    issue = {
        "code": str(code),
        "path": field_path(path),
        "reason": str(reason),
        "blocking": bool(blocking),
        "expected_type": copy.deepcopy(expected_type),
        "candidate_values": copy.deepcopy(list(candidate_values or [])),
        "category": category,
    }
    if details:
        issue["details"] = copy.deepcopy(details)
    return issue


def normalize_issue(
    value: Any, *, category: str = "conflict", default_code: str = "UNRESOLVED_INPUT",
) -> dict[str, Any]:
    if isinstance(value, str):
        code = {
            "missing": "REQUIRED_INPUT_MISSING",
            "uncertain": "INPUT_UNCERTAIN",
            "conflict": "INPUT_CONFLICT",
        }.get(category, default_code)
        return make_issue(
            code=code, path=field_path(value), reason=f"{value} is {category}.",
            blocking=category != "warning", category=category,
        )
    if not isinstance(value, dict):
        return make_issue(
            code=default_code, path="/values/unknown", reason=str(value),
            blocking=category != "warning", category=category,
        )
    known = {
        "code", "path", "reason", "message", "blocking", "expected_type",
        "candidate_values", "candidates", "category", "field", "name", "details",
    }
    details = copy.deepcopy(value.get("details") or {})
    details.update({key: copy.deepcopy(item) for key, item in value.items() if key not in known})
    issue_category = str(value.get("category") or category)
    return make_issue(
        code=str(value.get("code") or default_code),
        path=field_path(value.get("path") or value.get("field") or value.get("name")),
        reason=str(value.get("reason") or value.get("message") or value.get("code") or default_code),
        blocking=bool(value.get("blocking", issue_category != "warning")),
        expected_type=value.get("expected_type"),
        candidate_values=value.get("candidate_values") or value.get("candidates") or [],
        category=issue_category,
        details=details,
    )


def issues_from_legacy(spec: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for field, category in (
        ("missing_required_fields", "missing"),
        ("uncertain_fields", "uncertain"),
        ("input_conflicts", "conflict"),
    ):
        issues.extend(normalize_issue(item, category=category) for item in (spec.get(field) or []))
    unresolved = spec.get("unresolved") or {}
    if isinstance(unresolved, dict):
        for field, category in (("missing", "missing"), ("uncertain", "uncertain"), ("conflicts", "conflict")):
            issues.extend(normalize_issue(item, category=category) for item in (unresolved.get(field) or []))
    return deduplicate_issues(issues)


def deduplicate_issues(issues: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for raw in issues:
        issue = normalize_issue(raw, category=str(raw.get("category") or "conflict"))
        key = (issue["code"], issue["path"], issue["reason"], issue["blocking"])
        if key not in seen:
            result.append(issue)
            seen.add(key)
    return result


def build_resolution_state(
    issues: Iterable[dict[str, Any]] | None = None, *, unsupported: bool = False,
) -> dict[str, Any]:
    normalized = deduplicate_issues(issues or [])
    status = (
        "UNSUPPORTED" if unsupported or any(
            issue["blocking"] and issue.get("category") == "unsupported" for issue in normalized
        )
        else "NEEDS_CLARIFICATION" if any(issue["blocking"] for issue in normalized)
        else "RESOLVED"
    )
    return {"schema_version": SCHEMA_VERSION, "status": status, "issues": normalized}


def merge_resolution_state(
    state: dict[str, Any] | None, issues: Iterable[dict[str, Any]], *, unsupported: bool = False,
) -> dict[str, Any]:
    existing = (state or {}).get("issues") or []
    return build_resolution_state([*existing, *issues], unsupported=unsupported)


def legacy_unresolved_lists(state: dict[str, Any] | None) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    missing: list[str] = []
    uncertain: list[str] = []
    conflicts: list[dict[str, Any]] = []
    for issue in (state or {}).get("issues") or []:
        name = str(issue.get("path") or "").rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~")
        category = issue.get("category")
        if category == "missing":
            missing.append(name)
        elif category == "uncertain":
            uncertain.append(name)
        elif issue.get("blocking"):
            legacy = {
                "field": name, "path": issue.get("path"),
                "code": issue.get("code"), "message": issue.get("reason"),
            }
            legacy.update(copy.deepcopy(issue.get("details") or {}))
            conflicts.append(legacy)
    return missing, uncertain, conflicts
