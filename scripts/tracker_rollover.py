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

    index = store.get_tracker_index()
    archive = store.get_tracker_index(partition="archive") or {
        "tracker_schema_version": 1,
        "partition": "archive",
        "max_rows": 50,
        "rows": [],
        "shards": [],
    }
    source_documents: dict[str, dict[str, Any]] = {"tracker/index.yaml": index}
    for relative in index.get("shards", []):
        source_documents[relative] = store.get_shard(relative)

    move_ids = {item["packet_id"] for item in plan["moves"]}
    for rel, document in source_documents.items():
        document["rows"] = [
            row for row in document.get("rows", []) if row.get("packet_id") not in move_ids
        ]
    archive["rows"] = list(archive.get("rows", [])) + [
        item["row"] for item in plan["moves"]
    ]
    archive["rows"] = sorted(archive["rows"], key=lambda row: row["packet_id"])

    for rel, document in source_documents.items():
        if rel == "tracker/index.yaml":
            store.put_tracker_index(document)
        else:
            store.put_shard(rel, document)
    store.put_tracker_index(archive, partition="archive")

    # Move packet YAML files from active to archive partition.
    archive_dir = protocol_root / "archive/work-packets"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for item in plan["moves"]:
        packet = store.get_packet(item["packet_id"])
        if packet is not None:
            store.put_packet(item["packet_id"], packet, partition="archive")
            # Remove from active by deleting the file.
            active_path = protocol_root / "work-packets" / f"{item['packet_id']}.yaml"
            if active_path.exists():
                active_path.unlink()

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
    plan["moved"] = sorted(move_ids)
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
