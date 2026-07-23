from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from fast_engine_adapter import calculate as fast_calculate
from fast_engine_adapter import supports as fast_supports


def _calculate(procedure: str, target: str, inputs: object) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        return {
            "status": "ERROR",
            "error": {"code": "INVALID_INPUT", "message": "scenario inputs must be an object"},
        }
    try:
        if fast_supports(procedure, target):
            return {"status": "CALCULATED", "result": fast_calculate(procedure, target, inputs)}
        from samplesize200.procedures import ProcedureContractError, calculate_target
        return {
            "status": "CALCULATED",
            "result": calculate_target(procedure, target, inputs),
        }
    except Exception as exc:
        if hasattr(exc, "payload"):
            return {"status": "ERROR", "error": exc.payload}
        return {
            "status": "ERROR",
            "error": {"code": "ENGINE_EXECUTION_ERROR", "message": str(exc)},
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--procedure", required=True)
    parser.add_argument(
        "--target",
        default="required_sample_size",
        choices=["power", "detectable_effect", "required_events", "required_sample_size", "attrition_adjusted_sample_size"],
    )
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    raw_input = (
        args.input.read_text(encoding="utf-8-sig")
        if args.input is not None else sys.stdin.read()
    )
    if not raw_input:
        parser.error("batch input is required on stdin or with --input")
    scenarios = json.loads(raw_input)
    if not isinstance(scenarios, list):
        parser.error("batch input must be an array")
    results = [
        {"scenario_index": index, **_calculate(args.procedure, args.target, inputs)}
        for index, inputs in enumerate(scenarios)
    ]
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
