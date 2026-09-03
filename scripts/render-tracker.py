#!/usr/bin/env python3
"""Render canonical YAML tracker partitions into human-readable Markdown."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


HEAD = (
    "# Execution Tracker\n\n"
    "Canonical state: `tracker/index.yaml` and its declared task shards.\n\n"
    "| Task | Packet | State | Owner | Reviewer | Locks |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
)
ARCHIVE_HEAD = (
    "# Execution Tracker (Archive)\n\n"
    "Canonical state: `tracker/archive/index.yaml` and its declared archive shards.\n\n"
    "| Task | Packet | State | Owner | Reviewer | Locks |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
)


def load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return value


def rows_for(root: Path, relative: str) -> list[dict[str, Any]]:
    index_path = root / relative
    index = load(index_path)
    rows = list(index.get("rows", []))
    for shard in index.get("shards", []):
        shard_path = root / shard
        shard_doc = load(shard_path)
        rows.extend(shard_doc.get("rows", []))
    return rows


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(header: str, rows: list[dict[str, Any]]) -> str:
    lines = [header.rstrip("\n")]
    for row in rows:
        locks = row.get("locks", [])
        lock_text = "released" if not locks else ", ".join(map(str, locks))
        lines.append(
            "| "
            + " | ".join(
                cell(row[key])
                for key in ("task_id", "packet_id", "state", "owner", "reviewer")
            )
            + f" | {cell(lock_text)} |"
        )
    return "\n".join(lines) + "\n"


def render_projections(root: Path, check: bool = False) -> None:
    targets = (
        ("tracker/index.yaml", "execution-tracker.md", HEAD),
        (
            "tracker/archive/index.yaml",
            "archive/execution-tracker-archive.md",
            ARCHIVE_HEAD,
        ),
    )
    changed = False
    for source, destination, header in targets:
        expected = render(header, rows_for(root, source))
        path = root / destination
        if check:
            actual = path.read_text() if path.is_file() else ""
            if actual != expected:
                raise SystemExit(f"{path}: generated projection is out of date")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.is_file() or path.read_text() != expected:
                path.write_text(expected)
                changed = True
    if not check:
        print("tracker projections updated" if changed else "tracker projections current")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".contract-engineering"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    render_projections(args.root, args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
