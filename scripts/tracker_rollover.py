#!/usr/bin/env python3
"""Plan and confirmation-gate terminal tracker rollover into the archive."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

TERMINAL_STATES = {"Complete", "Cancelled"}


class RolloverError(ValueError):
    """Raised when a rollover cannot be applied safely."""


def _load(path: Path) -> Dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise RolloverError(f"{path}: expected a YAML mapping")
    return value


def build_plan(root: Path | str) -> Dict[str, Any]:
    """Build a deterministic rollover plan without changing any files."""
    protocol_root = Path(root)
    index_path = protocol_root / "tracker/index.yaml"
    archive_path = protocol_root / "tracker/archive/index.yaml"
    index = _load(index_path)
    archive = _load(archive_path)
    sources = [(index_path, index)]
    for relative in index.get("shards", []):
        path = protocol_root / "tracker" / Path(relative).relative_to("tracker")
        sources.append((path, _load(path)))

    archive_ids = {
        row["packet_id"] for row in archive.get("rows", []) if isinstance(row, dict)
    }
    moves: List[Dict[str, Any]] = []
    blockers: List[str] = []
    for source_path, document in sources:
        for row in document.get("rows", []):
            if row.get("state") not in TERMINAL_STATES:
                continue
            packet_id = row.get("packet_id")
            packet_path = protocol_root / "work-packets" / f"{packet_id}.yaml"
            destination = (
                protocol_root / "archive/work-packets" / f"{packet_id}.yaml"
            )
            if packet_id in archive_ids:
                blockers.append(f"{packet_id}: already exists in archive tracker")
            if not packet_path.is_file():
                blockers.append(f"{packet_id}: active packet file is missing")
            if destination.exists():
                blockers.append(f"{packet_id}: archive packet file already exists")
            if packet_path.is_file():
                packet = _load(packet_path)
                if packet.get("state") not in TERMINAL_STATES:
                    blockers.append(
                        f"{packet_id}: tracker is terminal but packet is {packet.get('state')!r}"
                    )
            moves.append(
                {
                    "packet_id": packet_id,
                    "source": str(source_path.relative_to(protocol_root)),
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
) -> Dict[str, Any]:
    """Return a dry-run plan or apply a previously reviewable confirmed plan."""
    protocol_root = Path(root)
    plan = build_plan(protocol_root)
    if not confirm:
        return plan
    if plan["blockers"]:
        raise RolloverError("; ".join(plan["blockers"]))
    if not plan["moves"]:
        return plan

    index_path = protocol_root / "tracker/index.yaml"
    archive_path = protocol_root / "tracker/archive/index.yaml"
    index = _load(index_path)
    archive = _load(archive_path)
    source_documents = {index_path: index}
    for relative in index.get("shards", []):
        path = protocol_root / "tracker" / Path(relative).relative_to("tracker")
        source_documents[path] = _load(path)

    move_ids = {item["packet_id"] for item in plan["moves"]}
    for path, document in source_documents.items():
        document["rows"] = [
            row for row in document.get("rows", []) if row.get("packet_id") not in move_ids
        ]
    archive["rows"] = list(archive.get("rows", [])) + [
        item["row"] for item in plan["moves"]
    ]
    archive["rows"] = sorted(archive["rows"], key=lambda row: row["packet_id"])

    for path, document in source_documents.items():
        _write(path, document)
    _write(archive_path, archive)
    archive_dir = protocol_root / "archive/work-packets"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for item in plan["moves"]:
        source = protocol_root / "work-packets" / f"{item['packet_id']}.yaml"
        destination = protocol_root / item["destination"]
        shutil.move(str(source), str(destination))

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


def _write(path: Path, value: Dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


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
