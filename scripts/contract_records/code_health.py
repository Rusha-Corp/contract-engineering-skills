"""Code-health gate: file-size limits and dead-code review enforcement.

The recorded decision is hard-gated; the outcome is left to judgment.
For every touched file over the limit, and for every dead-code finding,
the packet must record a decision. CI fails when the record is missing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .loaders import fail, path_matches

DEFAULT_MAX_FILE_LINES = 500
DEFAULT_EXCLUDE = (".contract-engineering/",)

VALID_SIZE_DECISIONS = {"decompose", "retain", "defer"}
VALID_DEAD_REF_DECISIONS = {
    "remove",
    "deprecate",
    "retain",
    "archive",
    "false_positive",
    "needs_evidence",
}
DEAD_CODE_CHECKPOINTS = {"baseline", "handoff"}


def count_file_lines(path: Path) -> int | None:
    """Return the number of lines in a text file, or None for binary files."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    # Skip files with null bytes (binary).
    if b"\x00" in raw:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def _is_excluded(path: str, exclude: list[str]) -> bool:
    return any(path_matches(path, rule) for rule in exclude)


def validate_size_reviews(
    packet: dict[str, Any],
    changed_paths: list[str],
    file_lines: dict[str, int],
    max_file_lines: int,
    exclude: list[str] | None = None,
) -> None:
    """Rule 1: every changed text file over the limit needs a size_reviews entry."""
    if exclude is None:
        exclude = list(DEFAULT_EXCLUDE)

    cleanup_scope = packet.get("cleanup_scope", {})
    size_reviews = cleanup_scope.get("size_reviews", [])
    reviewed_paths = {entry.get("path") for entry in size_reviews if isinstance(entry, dict)}

    for changed in changed_paths:
        if _is_excluded(changed, exclude):
            continue
        lines = file_lines.get(changed)
        if lines is None or lines <= max_file_lines:
            continue
        if changed not in reviewed_paths:
            fail(
                f"{packet['packet_id']}: changed file {changed} has {lines} lines "
                f"(limit {max_file_lines}) but has no size_reviews entry; "
                f"record a decision: decompose, retain, or defer"
            )

    # Validate each size_reviews entry has a valid decision.
    for entry in size_reviews:
        if not isinstance(entry, dict):
            fail(f"{packet['packet_id']}: size_reviews entry must be a mapping")
        decision = entry.get("decision")
        if decision not in VALID_SIZE_DECISIONS:
            fail(
                f"{packet['packet_id']}: size_reviews for {entry.get('path')} "
                f"has invalid decision '{decision}'; "
                f"must be one of {sorted(VALID_SIZE_DECISIONS)}"
            )
        if decision == "retain" and not entry.get("rationale"):
            fail(
                f"{packet['packet_id']}: size_reviews for {entry.get('path')} "
                f"with decision 'retain' requires a rationale"
            )
        if decision == "defer" and not entry.get("follow_up_ref"):
            fail(
                f"{packet['packet_id']}: size_reviews for {entry.get('path')} "
                f"with decision 'defer' requires a follow_up_ref"
            )


def validate_dead_code_review(packet: dict[str, Any]) -> None:
    """Rule 2: Handoff/Complete packets need dead_code_review with both checkpoints.

    Also validates that every dead_refs entry has a decision, and that
    needs_evidence findings block Complete state.
    """
    state = packet.get("state", "")
    if state not in {"Handoff", "Complete"}:
        return

    cleanup_scope = packet.get("cleanup_scope", {})
    dead_code_review = cleanup_scope.get("dead_code_review")

    if dead_code_review is None:
        fail(
            f"{packet['packet_id']}: state {state} requires "
            f"cleanup_scope.dead_code_review with both 'baseline' and 'handoff' "
            f"checkpoints"
        )

    if not isinstance(dead_code_review, list):
        fail(f"{packet['packet_id']}: dead_code_review must be a list")

    missing = DEAD_CODE_CHECKPOINTS - set(dead_code_review)
    if missing:
        fail(
            f"{packet['packet_id']}: dead_code_review is missing "
            f"checkpoints: {sorted(missing)}"
        )

    # Validate each dead_refs entry has a decision.
    dead_refs = cleanup_scope.get("dead_refs", [])
    # Legacy format: dead_refs is a list of strings (old packets).
    if all(isinstance(r, str) for r in dead_refs) and dead_refs:
        # Legacy string-format dead_refs are allowed without decisions
        # for backward compatibility with pre-existing packets.
        return

    for entry in dead_refs:
        if not isinstance(entry, dict):
            fail(f"{packet['packet_id']}: dead_refs entry must be a mapping")
        decision = entry.get("decision")
        if decision not in VALID_DEAD_REF_DECISIONS:
            fail(
                f"{packet['packet_id']}: dead_refs entry {entry.get('ref')} "
                f"has invalid decision '{decision}'; "
                f"must be one of {sorted(VALID_DEAD_REF_DECISIONS)}"
            )
        if state == "Complete" and decision == "needs_evidence":
            fail(
                f"{packet['packet_id']}: dead_refs entry {entry.get('ref')} "
                f"has decision 'needs_evidence' which blocks Complete state"
            )


def validate_code_health(
    packet: dict[str, Any],
    changed_paths: list[str],
    file_lines: dict[str, int],
    *,
    max_file_lines: int = DEFAULT_MAX_FILE_LINES,
    exclude: list[str] | None = None,
) -> None:
    """Run all code-health checks for a packet."""
    validate_size_reviews(packet, changed_paths, file_lines, max_file_lines, exclude)
    validate_dead_code_review(packet)
