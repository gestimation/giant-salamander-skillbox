#!/usr/bin/env python3
"""Retrieve research evidence and emit one compact, relevant calculation case."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit
from assistant_views import compact_example
from retrieve_example import retrieve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--procedure", required=True)
    parser.add_argument("--operation", default="required_sample_size")
    parser.add_argument("--formula-reference")
    parser.add_argument("--current-inputs", type=Path)
    parser.add_argument("--exact-only", action="store_true")
    parser.add_argument("--study-limit", type=int, default=5)
    args = parser.parse_args()
    current = (
        json.loads(args.current_inputs.read_text(encoding="utf-8-sig"))
        if args.current_inputs else {}
    )
    full = retrieve(
        args.procedure,
        operation=args.operation,
        formula_reference=args.formula_reference,
        include_related=not args.exact_only,
        limit=args.study_limit,
    )
    emit(compact_example(full, current))


if __name__ == "__main__":
    main()
