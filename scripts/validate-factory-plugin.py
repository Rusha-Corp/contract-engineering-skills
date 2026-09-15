#!/usr/bin/env python3
"""Validate root-level Factory plugin packaging without network access."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED_DIRS = ("skills", "commands", "droids", "hooks", "runtime", "scripts")
FORBIDDEN_SKILLS = {
    "using-superpowers",
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "using-git-worktrees",
    "test-driven-development",
}


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level value must be an object")
    return value


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    plugin = load_json(root / ".factory-plugin" / "plugin.json")
    marketplace = load_json(root / ".factory-plugin" / "marketplace.json")
    for key in ("name", "version", "description", "license"):
        if not isinstance(plugin.get(key), str) or not plugin[key]:
            errors.append(f"plugin.json missing {key}")
    if marketplace.get("name") != plugin.get("name"):
        errors.append("marketplace and plugin names differ")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        errors.append("marketplace must declare exactly one plugin")
    elif plugins[0].get("source") != "./":
        errors.append("marketplace source must be ./")
    for directory in REQUIRED_DIRS:
        if not (root / directory).is_dir():
            errors.append(f"missing root plugin directory: {directory}")
    skill_names = set()
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        name = path.parent.name
        if name in FORBIDDEN_SKILLS:
            errors.append(f"forbidden duplicate Superpowers skill: {name}")
        if name in skill_names:
            errors.append(f"duplicate skill: {name}")
        skill_names.add(name)
        text = path.read_text(encoding="utf-8")
        if not re.search(rf"^name:\s*{re.escape(name)}\s*$", text, re.MULTILINE):
            errors.append(f"{path}: metadata name is missing or mismatched")
    for path in sorted((root / "hooks").glob("*")):
        if path.is_file() and "${DROID_PLUGIN_ROOT}" not in path.read_text(
            encoding="utf-8", errors="ignore"
        ) and path.name == "hooks.json":
            errors.append("hooks.json must resolve plugin-local paths through DROID_PLUGIN_ROOT")
    return errors


def main() -> int:
    root = Path(".")
    if len(sys.argv) == 3 and sys.argv[1] == "--root":
        root = Path(sys.argv[2])
    errors = validate(root.resolve())
    if errors:
        for error in errors:
            print(f"plugin validation failed: {error}", file=sys.stderr)
        return 1
    print("Factory root plugin valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
