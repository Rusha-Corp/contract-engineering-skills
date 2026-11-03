#!/usr/bin/env python3
"""Plan and explicitly apply acceptance-first packet metadata migrations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.record_store import FileStore, RecordStore


class MigrationError(ValueError):
    """Raised when a migration is attempted without explicit confirmation."""


DEFAULTS = {
    "work_type": "delivery",
    "priority": "normal",
    "iteration": "",
    "open_questions": [],
}


def plan(root: Path | str, *, store: RecordStore | None = None) -> list[dict[str, Any]]:
    """Return proposed metadata changes without modifying any packet."""
    if store is None:
        store = FileStore(root)
    results: list[dict[str, Any]] = []
    for packet_id, packet in store.list_packets().items():
        changes = {
            key: value
            for key, value in DEFAULTS.items()
            if key not in packet
        }
        if changes:
            results.append(
                {
                    "packet_id": packet.get("packet_id", packet_id),
                    "changes": changes,
                }
            )
    return results


def apply(
    root: Path | str,
    *,
    confirm: bool = False,
    store: RecordStore | None = None,
) -> list[dict[str, Any]]:
    if not confirm:
        raise MigrationError("record migration requires --confirm")
    if store is None:
        store = FileStore(root)
    changes = plan(root, store=store)
    for item in changes:
        packet_id = item["packet_id"]
        packet = store.get_packet(packet_id)
        if packet is not None:
            packet.update(item["changes"])
            store.put_packet(packet_id, packet)
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
