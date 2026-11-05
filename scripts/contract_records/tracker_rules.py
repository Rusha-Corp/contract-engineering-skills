"""Tracker partition validation: row consistency, duplicates, orphans."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .constants import (
    ARCHIVE_PACKET_DIR,
    ARCHIVE_TRACKER,
    MAX_INDEX_PACKET_ROWS,
    MAX_SHARD_PACKET_ROWS,
    TERMINAL_STATES,
    TRACKER_SHARD_DIR,
    identifiers,
)
from .loaders import fail


TRACKER_ROW_RE = re.compile(
    rf"^\| ([^|]+) \| ({identifiers.PACKET_PATTERN[1:-1]}) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$",
    re.MULTILINE,
)


def is_task_or_packet_identifier(value: object) -> bool:
    return identifiers.is_task_or_packet_identifier(value)


def _parse_tracker_rows(text: str) -> list[tuple[str, str, str, str, str, str]]:
    return TRACKER_ROW_RE.findall(text)


def _check_row_consistency(
    label: str, rows: list[tuple[str, str, str, str, str, str]], packets: dict[str, dict[str, Any]]
) -> set[str]:
    """Return the set of packet IDs seen in the given tracker rows.

    Enforces no duplicate rows and that rows for known packets match state,
    owner, and reviewer. Orphan rows (no matching packet file) are reported by
    the caller, not here, because a row is only an orphan relative to its
    expected partition.
    """
    seen: set[str] = set()
    for _, packet_id, state, owner, reviewer, _ in rows:
        if packet_id in seen:
            fail(f"{label}: duplicate packet row {packet_id}")
        seen.add(packet_id)
        if packet_id in packets:
            packet = packets[packet_id]
            if state.strip() != packet["state"]:
                fail(f"{label}: state mismatch for {packet_id}")
            packet_owner = packet["owner"]
            if isinstance(packet_owner, dict):
                owner_str = packet_owner.get("identity", "")
            else:
                owner_str = str(packet_owner)
            if owner.strip() != owner_str:
                fail(f"{label}: owner mismatch for {packet_id}")
            if reviewer.strip() != str(packet["reviewer"]):
                fail(f"{label}: reviewer mismatch for {packet_id}")
    return seen


def validate_tracker(
    root: Path,
    live_packets: dict[str, dict[str, Any]],
    archive_packets: dict[str, dict[str, Any]],
) -> None:
    if (root / "tracker/index.yaml").is_file():
        return
    all_packets = {**live_packets, **archive_packets}
    live_tracker_path = root / "execution-tracker.md"
    if not live_tracker_path.is_file():
        fail("tracker: execution-tracker.md is missing")
    live_rows = _parse_tracker_rows(live_tracker_path.read_text())
    if len(live_rows) > MAX_INDEX_PACKET_ROWS:
        fail(
            f"tracker: active index has {len(live_rows)} packet rows; "
            f"move task rows into {TRACKER_SHARD_DIR}/"
        )
    live_seen = _check_row_consistency("tracker", live_rows, all_packets)
    shard_dir = root / TRACKER_SHARD_DIR
    if shard_dir.exists() and not shard_dir.is_dir():
        fail(f"tracker: {TRACKER_SHARD_DIR} is not a directory")
    shard_paths = sorted(shard_dir.glob("*.md")) if shard_dir.is_dir() else []
    for shard_path in shard_paths:
        shard_rows = _parse_tracker_rows(shard_path.read_text())
        if len(shard_rows) > MAX_SHARD_PACKET_ROWS:
            fail(
                f"tracker shard {shard_path.name}: has {len(shard_rows)} packet rows; "
                f"split the task shard before adding more work"
            )
        for task, packet_id, *_ in shard_rows:
            if not task.strip() or not shard_path.stem.startswith(task.strip()):
                fail(
                    f"tracker shard {shard_path.name}: row {packet_id} "
                    f"does not belong to task {task.strip()}"
                )
        shard_seen = _check_row_consistency(
            f"tracker shard {shard_path.name}", shard_rows, all_packets
        )
        duplicate = live_seen & shard_seen
        if duplicate:
            fail(f"tracker: packets in index and shard {sorted(duplicate)}")
        live_seen |= shard_seen

    archive_seen: set[str] = set()
    archive_tracker_path = root / ARCHIVE_TRACKER
    if archive_tracker_path.is_file():
        archive_rows = _parse_tracker_rows(archive_tracker_path.read_text())
        archive_seen = _check_row_consistency(
            "archive-tracker", archive_rows, all_packets
        )
    elif (root / ARCHIVE_PACKET_DIR).is_dir():
        fail(f"tracker: {ARCHIVE_PACKET_DIR} exists but {ARCHIVE_TRACKER} is missing")

    live_missing = set(live_packets) - live_seen
    if live_missing:
        fail(f"tracker: missing live packet rows {sorted(live_missing)}")
    archive_missing = set(archive_packets) - archive_seen
    if archive_missing:
        fail(f"tracker: missing archive packet rows {sorted(archive_missing)}")

    cross_partition = live_seen & archive_seen
    if cross_partition:
        fail(f"tracker: packets in both trackers {sorted(cross_partition)}")

    live_orphans = live_seen - set(live_packets)
    if live_orphans:
        fail(f"tracker: orphan rows with no live packet file {sorted(live_orphans)}")
    archive_orphans = archive_seen - set(archive_packets)
    if archive_orphans:
        fail(f"tracker: orphan rows with no archive packet file {sorted(archive_orphans)}")

    for packet_id, packet in archive_packets.items():
        if packet["state"] not in TERMINAL_STATES:
            fail(f"archive-tracker: {packet_id} is not terminal ({packet['state']})")
        if packet["state"] == "Complete" and not packet.get("handoff_ref"):
            fail(f"archive-tracker: {packet_id} Complete without handoff_ref")
