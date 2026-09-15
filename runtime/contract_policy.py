#!/usr/bin/env python3
"""Fail-closed policy for Contract Engineering PreToolUse hooks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

READ_ONLY_TOOLS = {"read", "grep", "glob", "ls", "getidediagnostics", "openfile"}
WRITE_TOOLS = {"create", "edit", "applypatch", "write", "delete", "move"}
EXTERNAL_COMMAND = re.compile(
    r"\b(?:git\s+push|curl|wget|ssh|scp|gh\s+(?:api|pr|issue)|docker\s+push)\b",
    re.IGNORECASE,
)
ACTIVE_STATES = {"Implementing", "Validation", "Handoff"}


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _project_path(project_root: Path, value: str) -> Path | None:
    candidate = Path(value)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        return resolved if _within(resolved, project_root.resolve()) else None
    resolved = (project_root / candidate).resolve()
    return resolved if _within(resolved, project_root.resolve()) else None


def _scoped(path: Path, project_root: Path, rules: list[str]) -> bool:
    relative = path.relative_to(project_root.resolve()).as_posix()
    for rule in rules:
        normalized = rule.rstrip("/")
        if relative == normalized or relative.startswith(normalized + "/"):
            return True
    return False


def _active_packets(project_root: Path) -> list[dict[str, Any]]:
    packet_dir = project_root / ".contract-engineering" / "work-packets"
    packets: list[dict[str, Any]] = []
    for path in sorted(packet_dir.glob("*.yaml")):
        try:
            packet = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(packet, dict) and packet.get("state") in ACTIVE_STATES:
            packets.append(packet)
    return packets


def _input_paths(tool_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("file_path", "path", "source", "destination"):
        value = tool_input.get(key)
        if isinstance(value, str):
            values.append(value)
    for key in ("paths", "files"):
        value = tool_input.get(key)
        if isinstance(value, list):
            values.extend(item for item in value if isinstance(item, str))
    return values


def evaluate_tool_call(
    project_root: Path, tool_name: str, tool_input: dict[str, Any]
) -> tuple[str, str]:
    """Return (allow|deny|ask, reason) for one Droid tool call."""
    if not isinstance(tool_input, dict):
        return "deny", "tool input must be an object"
    root = project_root.resolve()
    lowered = tool_name.lower()
    if lowered in READ_ONLY_TOOLS:
        return "allow", "read-only inspection"
    if lowered == "execute":
        command = tool_input.get("command", "")
        if not isinstance(command, str):
            return "deny", "execute command must be text"
        if EXTERNAL_COMMAND.search(command):
            return "ask", "external effect requires user approval"
        return "allow", "bounded local command"
    if lowered not in WRITE_TOOLS:
        return "deny", "unknown tool is not admitted"

    packets = _active_packets(root)
    if not packets:
        return "deny", "no claimed packet covers this write"
    paths = _input_paths(tool_input)
    if not paths:
        return "deny", "write has no explicit path"
    for value in paths:
        normalized = _project_path(root, value)
        if normalized is None:
            return "deny", "tool path escapes project root"
        relative = normalized.relative_to(root).as_posix()
        if relative.startswith(".contract-engineering/tracker/"):
            return "deny", "direct tracker state edits are governed"
        if relative.startswith(".contract-engineering/") and lowered in WRITE_TOOLS:
            return "deny", "canonical records require governed transitions"
        if not any(_scoped(normalized, root, packet.get("scope", {}).get("in", [])) for packet in packets):
            return "deny", "write is outside every active packet scope"
    return "allow", "write is within an active packet scope"


def main() -> int:
    import sys

    if len(sys.argv) != 2:
        print(json.dumps({"decision": "deny", "reason": "project root is required"}))
        return 2
    try:
        payload = json.load(sys.stdin)
        tool_name = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {})
        decision, reason = evaluate_tool_call(Path(sys.argv[1]), tool_name, tool_input)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        decision, reason = "deny", "malformed hook input"
    print(json.dumps({"decision": decision, "reason": reason}))
    return 2 if decision in {"deny", "ask"} else 0
