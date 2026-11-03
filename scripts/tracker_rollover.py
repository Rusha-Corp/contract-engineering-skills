#!/usr/bin/env python3
"""Plan and confirmation-gate terminal tracker rollover into the archive."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from scripts.record_store import FileStore, RecordStore

TERMINAL_STATES = {"Complete", "Cancelled"}


class RolloverError(ValueError):
    """Raised when a rollover cannot be applied safely."""


def build_plan(root: Path | str, *, store: RecordStore | None = None) -> dict[str, Any]:
    """Build a deterministic rollover plan without changing any files."""
    if store is None:
        store = FileStore(root)
    protocol_root = Path(root)
    index = store.get_tracker_index()
    if index is None:
        raise RolloverError("tracker/index.yaml not found")
    archive = store.get_tracker_index(partition="archive") or {
        "tracker_schema_version": 1,
        "partition": "archive",
        "max_rows": 50,
        "rows": [],
        "shards": [],
    }

    # Collect all source documents (index + shards).
    sources: list[tuple[str, dict[str, Any]]] = [("tracker/index.yaml", index)]
    for relative in index.get("shards", []):
        shard = store.get_shard(relative)
        sources.append((relative, shard))

    archive_ids = {
        row["packet_id"] for row in archive.get("rows", []) if isinstance(row, dict)
    }
    moves: list[dict[str, Any]] = []
    blockers: list[str] = []
    for source_rel, document in sources:
        for row in document.get("rows", []):
            if row.get("state") not in TERMINAL_STATES:
                continue
            packet_id = row.get("packet_id")
            packet = store.get_packet(packet_id)
            destination = (
                protocol_root / "archive/work-packets" / f"{packet_id}.yaml"
            )
            if packet_id in archive_ids:
                blockers.append(f"{packet_id}: already exists in archive tracker")
            if packet is None:
                blockers.append(f"{packet_id}: active packet file is missing")
            if destination.exists():
                blockers.append(f"{packet_id}: archive packet file already exists")
            if packet is not None:
                if packet.get("state") not in TERMINAL_STATES:
                    blockers.append(
                        f"{packet_id}: tracker is terminal but packet is {packet.get('state')!r}"
                    )
            moves.append(
                {
                    "packet_id": packet_id,
                    "source": source_rel,
                    "destination": str(destination.relative_to(protocol_root)),
                    "row": row,
                }
            )
    moves.sort(key=lambda item: item["packet_id"])
    return {
        "moves": moves,
        "blockers": sorted(set(blockers)),
        "moved": [],
    }


def apply_rollover(
    root: Path | str,
    *,
    confirm: bool = False,
    run_validation: bool = False,
    store: RecordStore | None = None,
) -> dict[str, Any]:
    """Return a dry-run plan or apply a previously reviewable confirmed plan."""
    if store is None:
        store = FileStore(root)
    protocol_root = Path(root)
    plan = build_plan(protocol_root, store=store)
    if not confirm:
        return plan
    if plan["blockers"]:
        raise RolloverError("; ".join(plan["blockers"]))
    if not plan["moves"]:
        return plan

    # Move tracker rows and packet files from active to archive via the store.
    for item in plan["moves"]:
        packet_id = item["packet_id"]
        store.move_tracker_row(packet_id, "active", "archive")
        store.move_packet(packet_id, "active", "archive")

    # Keep archive rows sorted by packet_id for deterministic output.
    archive_index = store.get_tracker_index("archive")
    if archive_index is not None and archive_index.get("rows"):
        archive_index["rows"] = sorted(
            archive_index["rows"], key=lambda r: r.get("packet_id", "")
        )
        store.put_tracker_index(archive_index, partition="archive")

    if run_validation:
        scripts = Path(__file__).parent
        subprocess.run(
            [sys.executable, str(scripts / "render-tracker.py"), "--root", str(protocol_root)],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(scripts / "validate-tracker.py"), "--root", str(protocol_root)],
            check=True,
        )
    plan["moved"] = sorted(item["packet_id"] for item in plan["moves"])
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(".contract-engineering"))
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    try:
        plan = apply_rollover(args.root, confirm=args.confirm, run_validation=args.confirm)
    except RolloverError as exc:
        raise SystemExit(f"rollover blocked: {exc}")
    print(yaml.safe_dump(plan, sort_keys=False))
    if not args.confirm:
        print("dry-run only; pass --confirm after review to apply moves", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
