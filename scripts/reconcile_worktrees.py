#!/usr/bin/env python3
"""Read-only reconciliation of Git worktrees and packet ownership records."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

PACKET_ID = re.compile(r"(?P<packet>[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-P[0-9]{3})")


def parse_worktrees(text: str) -> List[Dict[str, Any]]:
    """Parse `git worktree list --porcelain` output without invoking Git."""
    records: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None
    for raw_line in text.splitlines() + [""]:
        line = raw_line.strip()
        if not line:
            if current is not None:
                current["packet_id"] = _packet_id(
                    current.get("branch"), current.get("path")
                )
                records.append(current)
                current = None
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            if current is not None:
                current["packet_id"] = _packet_id(
                    current.get("branch"), current.get("path")
                )
                records.append(current)
            current = {"path": value}
        elif current is not None and key in {"HEAD", "branch"}:
            current[key.lower()] = (
                value[len("refs/heads/") :]
                if key == "branch" and value.startswith("refs/heads/")
                else value
            )
    return sorted(records, key=lambda item: (item["path"], item.get("branch") or ""))


def reconcile_records(root: Path | str, worktree_text: str) -> Dict[str, List[Dict[str, Any]]]:
    """Compare live worktrees with packet metadata without writing anything."""
    protocol_root = Path(root)
    packets = _load_packets(protocol_root / "work-packets")
    live = parse_worktrees(worktree_text)
    by_packet = {packet["packet_id"]: packet for packet in packets}
    live_by_packet = {
        item["packet_id"]: item for item in live if item.get("packet_id")
    }

    registered: List[Dict[str, Any]] = []
    drift: List[Dict[str, Any]] = []
    unregistered: List[Dict[str, Any]] = []
    for item in live:
        packet_id = item.get("packet_id")
        if not packet_id and not _looks_like_packet_worktree(item):
            continue
        packet = by_packet.get(packet_id)
        metadata = (packet or {}).get("worktree") if packet else None
        if not packet or not metadata:
            unregistered.append(item)
        elif _matches(metadata, item):
            registered.append(_merge(item, packet))
        else:
            drift.append(_merge(item, packet, metadata))

    missing: List[Dict[str, Any]] = []
    stale: List[Dict[str, Any]] = []
    for packet in packets:
        metadata = packet.get("worktree")
        if not metadata or metadata.get("cleanup_status") in {"released", "removed"}:
            continue
        if packet["packet_id"] not in live_by_packet:
            missing.append(
                {
                    "packet_id": packet["packet_id"],
                    "path": metadata.get("path"),
                    "branch": metadata.get("branch"),
                }
            )
        elif packet.get("state") in {"Complete", "Cancelled"}:
            stale.append(
                {
                    "packet_id": packet["packet_id"],
                    "path": metadata.get("path"),
                    "state": packet.get("state"),
                }
            )

    return {
        "registered": _sorted(registered),
        "unregistered": _sorted(unregistered),
        "missing": _sorted(missing),
        "stale": _sorted(stale),
        "drift": _sorted(drift),
    }


def _load_packets(directory: Path) -> List[Dict[str, Any]]:
    packets = []
    if not directory.exists():
        return packets
    for path in sorted(directory.glob("*.yaml")):
        record = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if record.get("packet_id"):
            packets.append(record)
    return packets


def _packet_id(branch: str | None, path: str | None) -> str | None:
    for value in (branch, path):
        if value:
            match = PACKET_ID.search(value)
            if match:
                return match.group("packet")
    return None


def _looks_like_packet_worktree(item: Dict[str, Any]) -> bool:
    branch = item.get("branch") or ""
    path = item.get("path") or ""
    return branch.startswith("agent/") or "CENG-" in path


def _matches(metadata: Dict[str, Any], live: Dict[str, Any]) -> bool:
    return (
        metadata.get("path") == live.get("path")
        and metadata.get("branch") == live.get("branch")
    )


def _merge(
    live: Dict[str, Any], packet: Dict[str, Any], metadata: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    result = dict(live)
    result["state"] = packet.get("state")
    if metadata is not None:
        result["expected"] = {
            "path": metadata.get("path"),
            "branch": metadata.get("branch"),
        }
    return result


def _sorted(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        records, key=lambda item: (item.get("packet_id") or "", item.get("path") or "")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".contract-engineering")
    parser.add_argument("--input", type=Path, help="Read porcelain output from a file")
    args = parser.parse_args()
    if args.input:
        text = args.input.read_text(encoding="utf-8")
    else:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        )
        text = result.stdout
    report = reconcile_records(Path(args.root), text)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
