#!/usr/bin/env python3
"""Return the bundled Japanese quick guide as a structured help response."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit


ROOT = Path(__file__).resolve().parents[1]
GUIDE_PATH = ROOT / "references" / "SAMPLESIZE200_QUICK_GUIDE_JA.md"


def build_help_response(reason: str) -> dict[str, object]:
    response: dict[str, object] = {
        "status": "HELP",
        "reason": reason,
        "help_only": True,
        "terminal_for_turn": True,
        "resume_previous_work": False,
        "research_example_offer": None,
        "title": "SAMPLESIZE200 クイックガイド",
        "restart_options": [
            "必要サンプルサイズを計算する",
            "固定した人数で検出力を計算する",
            "どの方法を使うか相談する",
        ],
    }
    if reason == "explicit_help_request":
        response["guide"] = GUIDE_PATH.read_text(encoding="utf-8")
    else:
        response["message"] = "まず、必要サンプルサイズ・達成パワー・必要イベント数のどれを知りたいかを教えてください。"
        response["guide_available_on_request"] = True
    return response


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reason",
        default="explicit_help_request",
        choices=("explicit_help_request", "workflow_confusion"),
    )
    args = parser.parse_args()
    emit(build_help_response(args.reason))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
