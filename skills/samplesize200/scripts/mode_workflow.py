from __future__ import annotations

import argparse
import copy
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit
from plan_request import plan
from trial_mode import new_state, record, report
from validate_study_spec import _normalized_mode


MODE_PLANS = {
    "CALCULATE": [
        "ask only nondefaultable inputs needed by the selected calculation target",
        "execute the validated engine",
        "show the concise final result and applied defaults",
    ],
    "STATISTICIAN": [
        "compare remaining procedures",
        "review effect and nuisance assumptions",
        "propose sensitivity scenarios without inventing values",
    ],
    "TEACHER": [
        "explain selection and calculation stages",
        "offer exact or clearly labelled related examples",
        "explain rounding and discrepancies",
    ],
    "REVIEWER": [
        "reconstruct the canonical StudySpec",
        "list missing reported assumptions",
        "reproduce only when inputs are complete",
        "classify discrepancies",
    ],
}


def workflow(spec: dict, *, previous_state: dict | None = None) -> dict:
    """Plan one canonical request while retaining conversation-local mode state."""
    state = copy.deepcopy(previous_state or {})
    conversation_id = state.get("conversation_id", str(uuid.uuid4()))
    request = copy.deepcopy(spec)
    interaction = request.setdefault("interaction_context", {
        "schema_version": "2.0.0", "presentation": {},
        "conversation": {}, "compatibility": {"source_schema": "StudySpec-v2"},
    })
    interaction.setdefault("conversation", {})["conversation_state_id"] = conversation_id
    mode = _normalized_mode((interaction.setdefault("presentation", {})).get("requested_mode") or "CALCULATE")
    if mode is None:
        mode = "CALCULATE"
    interaction["presentation"]["requested_mode"] = mode
    planned = plan(request, execute=False)
    trial = copy.deepcopy(state.get("trial_state") or new_state())
    record(trial, "workflow", {
        "mode": mode,
        "selection_status": planned.get("status"),
    })
    result = {
        **planned,
        "conversation_id": conversation_id,
        "requested_mode": mode,
        "engine_executed": False,
        "trial_state": trial,
        "mode_plan": MODE_PLANS.get(mode, MODE_PLANS["CALCULATE"]),
    }
    if mode == "REVIEWER":
        result["allowed_review_classifications"] = [
            "ERROR", "ASSUMPTION_DIFFERENCE", "ROUNDING_DIFFERENCE",
            "SOURCE_INCONSISTENCY", "MISSING_INFORMATION", "NOT_REPRODUCIBLE",
        ]
    status = planned.get("status")
    result["next_action"] = (
        "RUN_ENGINE" if status == "READY"
        else "ASK_REQUIRED_INPUTS" if status == "NEEDS_CLARIFICATION"
        else "CLARIFY_OR_STOP"
    )
    return result


def trial_report(previous_state: dict) -> dict:
    return report(previous_state.get("trial_state", {}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-spec", required=True, type=Path)
    parser.add_argument("--previous-state", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.study_spec.read_text(encoding="utf-8-sig"))
    previous = json.loads(args.previous_state.read_text(encoding="utf-8-sig")) if args.previous_state else None
    emit(workflow(spec, previous_state=previous))


if __name__ == "__main__":
    main()
