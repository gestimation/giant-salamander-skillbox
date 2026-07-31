"""Lazy adapter for frozen longitudinal kernels that do not execute SciPy.

The bundled Alpha 0.6.9 package preserves these Alpha 0.6.7 kernels unchanged. Its public package initializer
imports every engine family, including SciPy-backed methods.  These three
Chapter 10 kernels use the frozen Guenther analytic formula only, so a clean
child process can load their exact source modules without importing unused
SciPy binaries.  Unsupported procedures and targets must use the standard
engine worker.
"""

from __future__ import annotations

import os
import sys
import types
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from typing import Any, Callable


FAST_LONGITUDINAL = {
    "TWO-031.SAMPLE_SIZE": "repeated_post_mean",
    "TWO-032.SAMPLE_SIZE": "repeated_slope",
    "TWO-033.SAMPLE_SIZE": "repeated_weighted_contrast",
}


class _UnusedScipyObject:
    def __getattr__(self, name: str) -> Any:
        raise RuntimeError(f"unused SciPy function was unexpectedly requested: {name}")


def _unused_brentq(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError("unused scipy.optimize.brentq was unexpectedly requested")


def _install_frozen_namespace() -> None:
    engine_root = Path(os.environ["PYTHONPATH"].split(os.pathsep)[0]).resolve()
    package_root = engine_root / "samplesize200"
    if not package_root.is_dir():
        raise RuntimeError("bundled samplesize200 package is unavailable")

    package = types.ModuleType("samplesize200")
    package.__path__ = [str(package_root)]
    package.__package__ = "samplesize200"
    sys.modules["samplesize200"] = package

    scipy = types.ModuleType("scipy")
    scipy.__path__ = []
    optimize = types.ModuleType("scipy.optimize")
    optimize.brentq = _unused_brentq
    stats = types.ModuleType("scipy.stats")
    stats.nct = _UnusedScipyObject()
    stats.t = _UnusedScipyObject()
    scipy.optimize = optimize
    scipy.stats = stats
    sys.modules["scipy"] = scipy
    sys.modules["scipy.optimize"] = optimize
    sys.modules["scipy.stats"] = stats


def supports(procedure: str, target: str) -> bool:
    return target == "required_sample_size" and procedure in FAST_LONGITUDINAL


def _procedure_envelope(result: dict[str, Any], procedure_id: str, version: str) -> dict[str, Any]:
    """Match the frozen procedures._procedure_envelope metadata exactly."""
    output = deepcopy(result)
    model_id = procedure_id.partition(".")[0]
    output.update({
        "product": "samplesize200 Alpha", "version": version,
        "release_stage": "alpha", "model_id": model_id,
        "operation": "sample_size", "procedure_id": procedure_id,
        "schema_status": "preview", "final_public_api": False,
    })
    primary = next((
        record for record in output.get("quantities", [])
        if record.get("key") == "final_total" and record.get("stage") == "final"
    ), None)
    if primary is None:
        primary = {
            "key": "final_total", "value": output["final_total"],
            "quantity": "participants", "unit": "person", "stage": "final",
        }
    else:
        primary = dict(primary)
        if primary.get("unit") == "participants":
            primary["unit"] = "person"
    output["primary_result"] = primary
    output["procedure_lineage"] = output.get("procedure_lineage") or [{
        "role": "calculation_specification", "method_id": result.get("method_id"),
        "consumed_keys": [], "produced_key": "final_total",
    }]
    return output


def calculate(procedure: str, target: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if not supports(procedure, target):
        raise RuntimeError(f"fast adapter does not support {procedure} / {target}")
    _install_frozen_namespace()
    version = import_module("samplesize200._version").VERSION
    module = import_module("samplesize200.longitudinal")
    function: Callable[..., dict[str, Any]] = getattr(module, FAST_LONGITUDINAL[procedure])
    return _procedure_envelope(function(**inputs), procedure, version)
