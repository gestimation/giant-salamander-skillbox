#!/usr/bin/env python3
"""Run one ordinary planning request and emit the compact assistant view."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit
from assistant_input_adapter import adapt_assistant_contract
from assistant_views import compact_plan
from plan_request import plan


def calculate(spec: dict, *, recompute_hash: bool = True) -> dict:
    """Execute the authoritative planner exactly once and project its result."""
    prepared = adapt_assistant_contract(spec)
    interaction = prepared.setdefault("interaction_context", {
        "schema_version": "2.0.0", "presentation": {},
        "conversation": {}, "compatibility": {"source_schema": "StudySpec-v2"},
    })
    interaction.setdefault("presentation", {})["requested_mode"] = "CALCULATE"
    return compact_plan(plan(
        prepared, execute=True, output_mode="concise",
        recompute_hash=recompute_hash,
    ))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-spec", required=True, type=Path)
    parser.add_argument("--skip-hash-recompute", action="store_true")
    args = parser.parse_args()
    spec = json.loads(args.study_spec.read_text(encoding="utf-8-sig"))
    emit(calculate(
        spec, recompute_hash=not args.skip_hash_recompute,
    ))


if __name__ == "__main__":
    main()
