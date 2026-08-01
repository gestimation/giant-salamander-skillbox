from __future__ import annotations

from typing import Any


ACTIVATION_PHRASES = ("trial mode", "トライアル", "試用として記録")


def requested(text: str | None) -> bool:
    return bool(text and any(x in text.lower() for x in ACTIVATION_PHRASES))


def new_state(enabled: bool = False) -> dict[str, Any]:
    return {"enabled": enabled, "modes_used": [], "events": []}


def record(state: dict[str, Any], kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not state.get("enabled"):
        return state
    safe = {k: v for k, v in (payload or {}).items() if k not in {"input_text", "personal_information"}}
    state.setdefault("events", []).append({"kind": kind, **safe})
    mode = safe.get("mode")
    if mode and mode not in state.setdefault("modes_used", []):
        state["modes_used"].append(mode)
    return state


def report(state: dict[str, Any]) -> dict[str, Any]:
    events = state.get("events", []) if state.get("enabled") else []
    by = lambda kind: [x for x in events if x.get("kind") == kind]
    return {
        "trial_summary": "Conversation-local trial record; no external transmission or persistence is performed.",
        "tasks_performed": by("workflow"),
        "modes_used": state.get("modes_used", []),
        "procedures_selected": by("selected"),
        "clarifications_asked": by("clarification"),
        "calculations_completed": by("calculation"),
        "selection_issues": by("selection_issue"),
        "guidance_issues": by("guidance_issue"),
        "example_issues": by("example_issue"),
        "engine_errors": by("engine_error"),
        "user_corrections": by("user_correction"),
        "unresolved_points": by("unresolved"),
        "recommended_changes": by("recommended_change"),
        "overall_status": "COMPLETE" if events and not by("engine_error") and not by("unresolved") else "REVIEW_NEEDED",
    }
