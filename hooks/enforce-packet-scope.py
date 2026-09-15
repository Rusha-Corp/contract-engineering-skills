#!/usr/bin/env python3
"""Factory PreToolUse hook for packet scope and canonical-record protection."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "runtime"))
from contract_policy import evaluate_tool_call


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        root = Path(payload.get("cwd") or os.getcwd())
        decision, reason = evaluate_tool_call(
            root, payload.get("tool_name", ""), payload.get("tool_input", {})
        )
    except (json.JSONDecodeError, TypeError, OSError):
        decision, reason = "deny", "malformed hook input"
    print(f"{decision}: {reason}")
    return 2 if decision in {"deny", "ask"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
