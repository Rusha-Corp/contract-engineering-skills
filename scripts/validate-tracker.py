#!/usr/bin/env python3
"""Validate canonical YAML tracker partitions and their packet references."""

from __future__ import annotations

import argparse
import importlib.util
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from scripts.record_store import FileStore, RecordStore

IDENTIFIER_SCRIPT = Path(__file__).with_name("identifiers.py")
IDENTIFIER_SPEC = importlib.util.spec_from_file_location("identifiers", IDENTIFIER_SCRIPT)
assert IDENTIFIER_SPEC and IDENTIFIER_SPEC.loader
identifiers = importlib.util.module_from_spec(IDENTIFIER_SPEC)
IDENTIFIER_SPEC.loader.exec_module(identifiers)


STATES = {
    "Planned",
    "Claimed",
    "DesignReview",
    "DesignBlocked",
    "DataReview",
    "DataBlocked",
    "Ready",
    "Implementing",
    "Validation",
    "Rework",
    "Handoff",
    "Complete",
    "Interrupted",
    "Cancelled",
}
TASK_ID = identifiers.TASK_ID
PACKET_ID = identifiers.PACKET_ID
MAX_ACTIVE_AGE = timedelta(days=14)


def _index_commit_date(source: Path) -> date:
    """Return the date of the last git commit touching ``source``.

    Falls back to ``date.today()`` when not inside a git repository, so
    the staleness check remains deterministic relative to the committed
    state rather than the runner's wall clock.
    """
    import subprocess
    try:
        output = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci", "--", str(source)],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if output:
            return date.fromisoformat(output.split()[0])
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        pass
    return date.today()


def fail(message: str) -> None:
    raise SystemExit(f"tracker validation failed: {message}")


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail(f"missing {path}")
    try:
        value = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        fail(f"{path}: invalid YAML ({exc})")
    if not isinstance(value, dict):
        fail(f"{path}: expected a YAML mapping")
    return value


def validate_row(
    row: Any,
    source: Path,
    expected_partition: str,
    reference_date: date | None = None,
) -> str:
    if not isinstance(row, dict):
        fail(f"{source}: tracker row must be a mapping")
    required = {
        "task_id",
        "packet_id",
        "state",
        "owner",
        "reviewer",
        "locks",
        "next_action",
        "updated_at",
    }
    missing = required - row.keys()
    if missing:
        fail(f"{source}: row missing {sorted(missing)}")
    task_id = row["task_id"]
    packet_id = row["packet_id"]
    if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
        fail(f"{source}: invalid task_id {task_id!r}")
    if not isinstance(packet_id, str) or not PACKET_ID.fullmatch(packet_id):
        fail(f"{source}: invalid packet_id {packet_id!r}")
    if not packet_id.startswith(f"{task_id}-P"):
        fail(f"{source}: packet {packet_id!r} does not belong to task {task_id!r}")
    if not isinstance(row["state"], str) or row["state"] not in STATES:
        fail(f"{source}: invalid state for {packet_id!r}")
    if not isinstance(row["locks"], list) or not all(
        isinstance(lock, str) for lock in row["locks"]
    ):
        fail(f"{source}: locks must be a string list for {packet_id!r}")
    updated_at = row["updated_at"]
    if isinstance(updated_at, date):
        updated_date = updated_at
    elif isinstance(updated_at, str):
        try:
            updated_date = date.fromisoformat(updated_at)
        except ValueError:
            fail(f"{source}: updated_at must be an ISO date for {packet_id!r}")
    else:
        fail(f"{source}: updated_at must be an ISO date for {packet_id!r}")
    reviewable_states = {
        "Claimed",
        "Implementing",
        "Validation",
        "Handoff",
        "Rework",
        "DesignReview",
        "DataReview",
        "Interrupted",
    }
    if expected_partition == "active" and row["state"] in reviewable_states:
        ref = reference_date if reference_date is not None else _index_commit_date(source)
        if ref - updated_date > MAX_ACTIVE_AGE:
            fail(f"{source}: active packet {packet_id!r} has a stale updated_at")
    if expected_partition == "archive" and row["state"] not in {"Complete", "Cancelled"}:
        fail(f"{source}: archived packet {packet_id!r} is not terminal")
    return packet_id


def partition_rows(
    root: Path,
    relative: str,
    expected_partition: str,
    *,
    store: RecordStore | None = None,
) -> tuple[list[dict[str, Any]], set[str]]:
    if store is None:
        store = FileStore(root)
    partition = "archive" if "archive" in relative else "active"
    index_path = root / relative
    index = store.get_tracker_index(partition)
    if index is None:
        fail(f"missing {index_path}")
    if index.get("tracker_schema_version") != 1:
        fail(f"{index_path}: unsupported tracker_schema_version")
    if index.get("partition") != expected_partition:
        fail(f"{index_path}: expected partition {expected_partition!r}")
    max_rows = index.get("max_rows")
    if not isinstance(max_rows, int) or max_rows < 1:
        fail(f"{index_path}: max_rows must be a positive integer")
    rows = list(index.get("rows", []))
    if not isinstance(rows, list):
        fail(f"{index_path}: rows must be a list")
    if len(rows) > max_rows:
        fail(f"{index_path}: {len(rows)} rows exceed max_rows={max_rows}")
    files = {str(index_path)}
    all_rows = rows[:]
    for shard in index.get("shards", []):
        if not isinstance(shard, str):
            fail(f"{index_path}: shard paths must be strings")
        shard_path = root / shard
        shard_doc = store.get_shard(shard)
        if shard_doc.get("tracker_schema_version") != 1:
            fail(f"{shard_path}: unsupported tracker_schema_version")
        if shard_doc.get("partition") != expected_partition:
            fail(f"{shard_path}: wrong partition")
        shard_max = shard_doc.get("max_rows")
        shard_rows = shard_doc.get("rows")
        if not isinstance(shard_max, int) or not isinstance(shard_rows, list):
            fail(f"{shard_path}: invalid shard bounds or rows")
        if len(shard_rows) > shard_max:
            fail(f"{shard_path}: {len(shard_rows)} rows exceed max_rows={shard_max}")
        task_id = shard_doc.get("task_id")
        if expected_partition == "active" and not isinstance(task_id, str):
            fail(f"{shard_path}: active shard requires task_id")
        for row in shard_rows:
            if row.get("task_id") != task_id:
                fail(f"{shard_path}: row task does not match shard task")
        all_rows.extend(shard_rows)
        files.add(str(shard_path))
    seen: set[str] = set()
    ref_date = _index_commit_date(index_path) if expected_partition == "active" else None
    for row in all_rows:
        packet_id = validate_row(row, index_path, expected_partition, ref_date)
        if packet_id in seen:
            fail(f"{packet_id}: duplicate row in {expected_partition} partition")
        seen.add(packet_id)
    return all_rows, files


def packet_files(
    root: Path,
    directory: str,
    *,
    store: RecordStore | None = None,
) -> dict[str, dict[str, Any]]:
    if store is None:
        store = FileStore(root)
    partition = "archive" if "archive" in directory else "active"
    result: dict[str, dict[str, Any]] = {}
    for packet_id, packet in store.list_packets(partition).items():
        if not isinstance(packet_id, str):
            fail(f"missing packet_id in {directory}")
        if packet_id in result:
            fail(f"duplicate packet file {packet_id}")
        result[packet_id] = packet
    return result


def validate_events(
    root: Path,
    packet_ids: set[str],
    *,
    store: RecordStore | None = None,
) -> None:
    if store is None:
        store = FileStore(root)
    events_dir = root / "tracker/events"
    if not events_dir.is_dir():
        return
    seen: set[str] = set()
    # Discover task IDs by listing event files, then read via store.
    for event_path in sorted(events_dir.glob("*.yaml")):
        task_id_from_file = event_path.stem
        document = store.list_events(task_id_from_file)
        # Reconstruct a pseudo-document for validation compatibility.
        task_id = task_id_from_file
        if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
            fail(f"{event_path}: invalid task_id")
        events = document
        if not isinstance(events, list):
            fail(f"{event_path}: events must be a list")
        previous_timestamp = ""
        for event in events:
            if not isinstance(event, dict):
                fail(f"{event_path}: event must be a mapping")
            required = {
                "event_id",
                "packet_id",
                "type",
                "actor",
                "occurred_at",
                "summary",
            }
            missing = required - event.keys()
            if missing:
                fail(f"{event_path}: event missing {sorted(missing)}")
            event_id = event["event_id"]
            packet_id = event["packet_id"]
            timestamp = event["occurred_at"]
            if not isinstance(event_id, str) or not event_id or event_id in seen:
                fail(f"{event_path}: duplicate or invalid event_id {event_id!r}")
            if not isinstance(packet_id, str) or not PACKET_ID.fullmatch(packet_id):
                fail(f"{event_path}: invalid event packet_id {packet_id!r}")
            if not packet_id.startswith(f"{task_id}-P") or packet_id not in packet_ids:
                fail(f"{event_path}: event packet is not a known task packet")
            if not all(
                isinstance(event[field], str) and event[field]
                for field in ("type", "actor", "occurred_at", "summary")
            ):
                fail(f"{event_path}: event fields must be non-empty strings")
            if timestamp < previous_timestamp:
                fail(f"{event_path}: events are not ordered by occurred_at")
            previous_timestamp = timestamp
            seen.add(event_id)


def compare(rows: list[dict[str, Any]], packets: dict[str, dict[str, Any]], partition: str) -> None:
    row_ids = {row["packet_id"] for row in rows}
    packet_ids = set(packets)
    missing = packet_ids - row_ids
    orphaned = row_ids - packet_ids
    if missing:
        fail(f"{partition}: packet files missing tracker rows {sorted(missing)}")
    if orphaned:
        fail(f"{partition}: tracker rows have no packet file {sorted(orphaned)}")
    for row in rows:
        packet = packets[row["packet_id"]]
        for field in ("state", "owner", "reviewer"):
            packet_value = packet.get(field)
            if field == "owner" and isinstance(packet_value, dict):
                packet_value = packet_value.get("identity", "")
            if row[field] != packet_value:
                fail(
                    f"{partition}: {row['packet_id']} {field} mismatch "
                    f"({row[field]!r} != {packet_value!r})"
                )
        packet_locks = packet.get("locks", [])
        if sorted(row["locks"]) != sorted(packet_locks):
            fail(f"{partition}: {row['packet_id']} locks mismatch")


def validate(root: Path, *, store: RecordStore | None = None) -> None:
    if store is None:
        store = FileStore(root)
    active_rows, active_files = partition_rows(root, "tracker/index.yaml", "active", store=store)
    archive_rows, archive_files = partition_rows(
        root, "tracker/archive/index.yaml", "archive", store=store
    )
    active_packets = packet_files(root, "work-packets", store=store)
    archive_packets = packet_files(root, "archive/work-packets", store=store)
    compare(active_rows, active_packets, "active")
    compare(archive_rows, archive_packets, "archive")
    active_ids = {row["packet_id"] for row in active_rows}
    archive_ids = {row["packet_id"] for row in archive_rows}
    overlap = active_ids & archive_ids
    if overlap:
        fail(f"packets appear in both active and archive partitions: {sorted(overlap)}")
    validate_events(root, active_ids | archive_ids, store=store)
    print(
        f"tracker valid: {len(active_rows)} active rows, "
        f"{len(archive_rows)} archive rows, "
        f"{len(active_files) + len(archive_files)} YAML partitions"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".contract-engineering"))
    args = parser.parse_args()
    validate(args.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
