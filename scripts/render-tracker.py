#!/usr/bin/env python3
"""Render canonical YAML tracker partitions into human-readable Markdown."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from scripts.record_store import FileStore, RecordStore


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


def rows_for(root: Path, relative: str, *, store: RecordStore | None = None) -> list[dict[str, Any]]:
    if store is None:
        store = FileStore(root)
    partition = "archive" if "archive" in relative else "active"
    index = store.get_tracker_index(partition)
    if index is None:
        return []
    rows = list(index.get("rows", []))
    for shard in index.get("shards", []):
        shard_doc = store.get_shard(shard)
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


def render_projections(root: Path, check: bool = False, *, store: RecordStore | None = None) -> None:
    if store is None:
        store = FileStore(root)
    targets = (
        ("tracker/index.yaml", "execution-tracker.md", HEAD, "active"),
        (
            "tracker/archive/index.yaml",
            "archive/execution-tracker-archive.md",
            ARCHIVE_HEAD,
            "archive",
        ),
    )
    changed = False
    for source, destination, header, partition in targets:
        expected = render(header, rows_for(root, source, store=store))
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
