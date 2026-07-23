from __future__ import annotations

import argparse
import json
import importlib.util
from importlib import metadata
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import SkillContractError, emit, resolve_procedure, validate_engine_compatibility
from validate_engine_request import validate_request
from render_result import render


MINIMUM_SCIPY_VERSION = (1, 11)


def _python_executable() -> str:
    return sys.executable


def _decode(data: bytes | str | None) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    for encoding in ("utf-8", "cp932"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _scipy_dependency_error() -> dict[str, Any] | None:
    if importlib.util.find_spec("scipy") is None:
        return {"code": "DEPENDENCY_NOT_AVAILABLE", "dependency": "scipy>=1.11"}
    try:
        installed = metadata.version("scipy")
    except metadata.PackageNotFoundError:
        return {"code": "DEPENDENCY_NOT_AVAILABLE", "dependency": "scipy>=1.11"}
    numbers = tuple(int(part) for part in re.findall(r"\d+", installed)[:2])
    if numbers < MINIMUM_SCIPY_VERSION:
        return {
            "code": "DEPENDENCY_VERSION_UNSUPPORTED",
            "dependency": "scipy>=1.11",
            "installed_version": installed,
        }
    return None


def _stage_values(result: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    return [x for x in result.get("quantities", []) if isinstance(x, dict) and x.get("stage") == stage]


def _allocation(result: dict[str, Any]) -> dict[str, Any]:
    tokens = ("group", "arm", "control", "treatment", "cluster", "sequence", "pair", "participant")
    return {
        key: value for key, value in result.items()
        if any(token in key.lower() for token in tokens) and isinstance(value, (int, float, list, dict))
    }


def _normalize(item: dict[str, Any], inputs: dict[str, Any], result: dict[str, Any], compatibility: dict[str, Any], calculation_target: str) -> dict[str, Any]:
    primary = result.get("primary_result")
    raw_quantities = _stage_values(result, "raw")
    final_quantities = _stage_values(result, "final")
    raw_fields = {key: value for key, value in result.items() if key.startswith("raw_")}
    rounding_fields = {key: value for key, value in result.items() if "round" in key.lower() or key.startswith("ceil")}
    adjustment_fields = {
        key: value for key, value in result.items()
        if any(token in key.lower() for token in ("adjust", "attrition", "allocation", "divisib", "constraint"))
    }
    return {
        "procedure_key": item["procedure_key"],
        "public_id": item["public_id"],
        "engine_id": item["engine_id"],
        "method_aliases": item.get("legacy_ids", []),
        "calculation_target": calculation_target,
        "structured_inputs": inputs,
        "raw_result": {"quantities": raw_quantities, "legacy_fields": raw_fields},
        "final_result": primary or (final_quantities[0] if final_quantities else None),
        "group_or_cluster_allocation": _allocation(result),
        "quantity": (primary or {}).get("quantity", item.get("quantity")),
        "unit": (primary or {}).get("unit", item.get("unit")),
        "stage": (primary or {}).get("stage", item.get("stage", "final")),
        "assumptions": result.get("assumptions", []),
        "rounding_trace": {"quantities": _stage_values(result, "rounded"), "fields": rounding_fields},
        "adjustment_trace": {
            "quantities": _stage_values(result, "allocation_adjusted") + _stage_values(result, "design_constrained"),
            "fields": adjustment_fields,
        },
        "warnings": result.get("warnings", []),
        "provenance_reference": item.get("source_provenance", {}),
        "validation_reference": item.get("validation_evidence", {}),
        "engine_compatibility": compatibility,
        "engine_output": result,
    }


def _resolution_response(result: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any] | None:
    status = result.get("status")
    if status == "needs_clarification":
        return {
            "status": "NEEDS_CLARIFICATION",
            "calculation_target": "power",
            "structured_inputs": inputs,
            "questions": [row.get("prompt") for row in result.get("questions", []) if row.get("prompt")],
            "engine_resolution": result,
        }
    if status == "invalid":
        return {
            "status": "ERROR",
            "calculation_target": "power",
            "structured_inputs": inputs,
            "error": {"code": "POWER_DESIGN_INVALID", "details": result},
        }
    return None


def _invoke_worker(
    item: dict[str, Any], scenarios: list[dict[str, Any]], *,
    calculation_target: str, engine_root: Path,
) -> list[dict[str, Any]]:
    """Execute ordered scenarios in one child process using stdin JSON transport."""
    env = os.environ.copy()
    inherited_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        [str(engine_root)] + ([inherited_pythonpath] if inherited_pythonpath else [])
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    worker = Path(__file__).resolve().with_name("engine_batch_worker.py")
    command = [
        _python_executable(), str(worker), "--procedure", item["engine_id"],
        "--target", calculation_target,
    ]
    payload = json.dumps(scenarios, ensure_ascii=False).encode("utf-8")
    try:
        completed = subprocess.run(
            command, input=payload, capture_output=True, env=env, timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        raise SkillContractError(
            "ENGINE_TIMEOUT",
            "engine child process exceeded the execution timeout",
            execution_phase="child_process",
            preserve_study_spec=True,
            retryable_without_user_input=True,
        ) from exc
    except OSError as exc:
        raise SkillContractError(
            "ENGINE_PROCESS_LAUNCH_FAILED",
            "engine child process could not be launched",
            execution_phase="pre_launch",
            exception_type=type(exc).__name__,
            preserve_study_spec=True,
            retryable_without_user_input=False,
        ) from exc
    if completed.returncode != 0:
        raise SkillContractError(
            "ENGINE_CHILD_FAILED",
            "engine child process exited with a nonzero status",
            execution_phase="child_process",
            returncode=completed.returncode,
            preserve_study_spec=True,
            retryable_without_user_input=False,
        )
    try:
        batch = json.loads(_decode(completed.stdout))
    except json.JSONDecodeError as exc:
        raise SkillContractError(
            "ENGINE_OUTPUT_INVALID",
            "engine child output is not valid JSON",
            execution_phase="post_process",
            preserve_study_spec=True,
            retryable_without_user_input=False,
        ) from exc
    if not isinstance(batch, list) or len(batch) != len(scenarios):
        raise SkillContractError(
            "ENGINE_OUTPUT_INVALID",
            "engine child output has an invalid scenario count",
            execution_phase="post_process",
            expected_scenarios=len(scenarios),
            preserve_study_spec=True,
            retryable_without_user_input=False,
        )
    for index, record in enumerate(batch):
        if not isinstance(record, dict) or record.get("scenario_index") != index:
            raise SkillContractError(
                "ENGINE_OUTPUT_INVALID",
                "engine child output has an invalid scenario record",
                execution_phase="post_process",
                scenario_index=index,
                preserve_study_spec=True,
                retryable_without_user_input=False,
            )
    return batch


def run(identifier: str, inputs: object, *, calculation_target: str = "required_sample_size",
        output_mode: str = "concise", recompute_hash: bool = True,
        defaults_applied: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    validation = validate_request(identifier, inputs, calculation_target)
    if not validation["valid"]:
        return {"status": "ERROR", "error": {"code": "ENGINE_REQUEST_REJECTED", "details": validation}}
    try:
        compatibility = validate_engine_compatibility(recompute_hash=recompute_hash)
        item = resolve_procedure(identifier)
        normalized_inputs = validation["normalized_inputs"]
        engine_root = Path(compatibility["engine_root"])
        dependency_error = _scipy_dependency_error()
        if dependency_error:
            return {"status": "ERROR", "error": dependency_error}
        record = _invoke_worker(
            item, [normalized_inputs], calculation_target=calculation_target,
            engine_root=engine_root,
        )[0]
        if record.get("status") != "CALCULATED":
            return {"status": "ERROR", "error": record.get("error", {
                "code": "ENGINE_OUTPUT_INVALID",
                "message": "engine child result omitted error details",
            })}
        result = record.get("result")
        if not isinstance(result, dict):
            raise SkillContractError(
                "ENGINE_OUTPUT_INVALID",
                "engine child result must be an object",
                execution_phase="post_process",
                preserve_study_spec=True,
                retryable_without_user_input=False,
            )
        resolution = _resolution_response(result, normalized_inputs)
        if resolution is not None:
            return resolution
        calculated = {"status": "CALCULATED", **_normalize(
            item, normalized_inputs, result, compatibility, calculation_target
        )}
        calculated["defaults_applied"] = list(defaults_applied or []) + validation.get("defaults_applied", [])
        calculated["display"] = render(calculated, output_mode, calculated["defaults_applied"])
        return calculated
    except SkillContractError as exc:
        return {"status": "ERROR", "error": exc.payload}


def run_many(identifier: str, scenarios: list[object], *,
             calculation_target: str = "required_sample_size",
             output_mode: str = "concise", recompute_hash: bool = True,
             defaults_applied: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Execute independent scenarios in one isolated Python child process."""
    if not scenarios:
        return []
    validations = [validate_request(identifier, inputs, calculation_target) for inputs in scenarios]
    results: list[dict[str, Any] | None] = [None] * len(scenarios)
    valid_indices = []
    for index, validation in enumerate(validations):
        if validation["valid"]:
            valid_indices.append(index)
        else:
            results[index] = {
                "status": "ERROR",
                "error": {"code": "ENGINE_REQUEST_REJECTED", "details": validation},
            }
    if not valid_indices:
        return [result for result in results if result is not None]

    try:
        compatibility = validate_engine_compatibility(recompute_hash=recompute_hash)
        item = resolve_procedure(identifier)
        engine_root = Path(compatibility["engine_root"])
        dependency_error = _scipy_dependency_error()
        if dependency_error:
            dependency_error = {
                "status": "ERROR",
                "error": dependency_error,
            }
            for index in valid_indices:
                results[index] = dependency_error
            return [result for result in results if result is not None]

        normalized = [validations[index]["normalized_inputs"] for index in valid_indices]
        batch = _invoke_worker(
            item, normalized, calculation_target=calculation_target,
            engine_root=engine_root,
        )
        for index, record in zip(valid_indices, batch):
            if record.get("status") != "CALCULATED":
                results[index] = {"status": "ERROR", "error": record.get("error", {
                    "code": "ENGINE_EXECUTION_ERROR", "message": "missing batch error details",
                })}
                continue
            raw_result = record.get("result")
            if not isinstance(raw_result, dict):
                results[index] = {
                    "status": "ERROR",
                    "error": {"code": "ENGINE_EXECUTION_ERROR", "message": "batch result must be an object"},
                }
                continue
            validation = validations[index]
            resolution = _resolution_response(raw_result, validation["normalized_inputs"])
            if resolution is not None:
                results[index] = resolution
                continue
            calculated = {"status": "CALCULATED", **_normalize(
                item, validation["normalized_inputs"], raw_result, compatibility, calculation_target
            )}
            calculated["defaults_applied"] = (
                list(defaults_applied or []) + validation.get("defaults_applied", [])
            )
            calculated["display"] = render(
                calculated, output_mode, calculated["defaults_applied"]
            )
            results[index] = calculated
    except SkillContractError as exc:
        error = {"status": "ERROR", "error": exc.payload}
        for index in valid_indices:
            results[index] = error
    return [result for result in results if result is not None]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--procedure", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--target", default="required_sample_size",
                        choices=["power", "detectable_effect", "required_events", "required_sample_size", "attrition_adjusted_sample_size"])
    parser.add_argument("--output-mode", default="concise", choices=["concise", "detailed", "qc"])
    parser.add_argument("--skip-hash-recompute", action="store_true", help="For repeated local tests only; identity metadata is still checked.")
    args = parser.parse_args()
    inputs = json.loads(args.input.read_text(encoding="utf-8-sig"))
    result = run(args.procedure, inputs, calculation_target=args.target,
                 output_mode=args.output_mode, recompute_hash=not args.skip_hash_recompute)
    emit(result)
    raise SystemExit(0 if result["status"] == "CALCULATED" else 2)


if __name__ == "__main__":
    main()
