"""Canonical Python API for SAMPLESIZE200 1.0."""

from __future__ import annotations

from typing import Any

from plan_request import plan as _authoritative_plan


def plan(
    request: dict[str, Any],
    *,
    execute: bool = False,
    output_mode: str = "concise",
    recompute_hash: bool = True,
) -> dict[str, Any]:
    """Plan or execute one canonical StudySpec v2 request."""
    return _authoritative_plan(
        request,
        execute=execute,
        output_mode=output_mode,
        recompute_hash=recompute_hash,
    )


def calculate(
    request: dict[str, Any],
    *,
    output_mode: str = "concise",
    recompute_hash: bool = True,
) -> dict[str, Any]:
    """Execute one request and return the canonical CalculationResult envelope."""
    return plan(
        request,
        execute=True,
        output_mode=output_mode,
        recompute_hash=recompute_hash,
    )


__all__ = ["calculate", "plan"]
