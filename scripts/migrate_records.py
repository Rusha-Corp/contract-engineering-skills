#!/usr/bin/env python3
"""Plan and explicitly apply acceptance-first packet metadata migrations."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml


class MigrationError(ValueError):
    """Raised when a migration is attempted without explicit confirmation."""


DEFAULTS = {
    "work_type": "delivery",
    "priority": "normal",
    "iteration": "",
    "open_questions": [],
}


def _load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise MigrationError(f"{path}: packet must be a mapping")
    return value


def plan(root: Path | str) -> list[dict[str, Any]]:
    """Return proposed metadata changes without modifying any packet."""
    packet_dir = Path(root) / "work-packets"
    results: list[dict[str, Any]] = []
    if not packet_dir.is_dir():
        return results
    for path in sorted(packet_dir.glob("*.yaml")):
        packet = _load(path)
        changes = {
            key: value
            for key, value in DEFAULTS.items()
            if key not in packet
        }
        if changes:
            results.append(
                {
                    "packet_id": packet.get("packet_id", path.stem),
                    "path": str(path),
                    "changes": changes,
                }
            )
    return results


def _write(path: Path, packet: dict[str, Any]) -> None:
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            yaml.safe_dump(packet, stream, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def apply(root: Path | str, *, confirm: bool = False) -> list[dict[str, Any]]:
    if not confirm:
        raise MigrationError("record migration requires --confirm")
    changes = plan(root)
    for item in changes:
        path = Path(item["path"])
        packet = _load(path)
        packet.update(item["changes"])
        _write(path, packet)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".contract-engineering"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if args.apply:
        changes = apply(args.root, confirm=args.confirm)
    else:
        changes = plan(args.root)
    print(json.dumps(changes, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
