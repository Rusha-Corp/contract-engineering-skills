#!/usr/bin/env python3
"""Enforce that every changed path is claimed by a work-packet scope.

This script replaces the inline bash in the Protocol validation workflow's
"Enforce changed packet scope" step.  It implements three rules that
eliminate false positives without weakening real scope enforcement:

1. **Skip non-records diffs.**  If no changed path lives under
   ``.contract-engineering/``, the diff cannot violate packet scope.
   Dependency-only PRs (e.g. dependabot) pass immediately.

2. **Artifact-filename claiming.**  Evidence, handoff, and decision files
   are named after their owning packet (e.g.
   ``CENG-T023-P001-EV001.md``).  The gate treats the packet ID
   extracted from the filename as a claiming packet, provided that packet
   exists on HEAD.  This unblocks evidence/handoff pushes that do not also
   modify the packet file.

3. **Force-push skip.**  When the base SHA is unreachable (a force-push
   rewrote history), the diff cannot be computed reliably.  The gate
   warns and passes instead of enforcing against a garbage diff.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from scripts.packet_scope import path_matches, packet_scope
from scripts.record_store import FileStore, RecordStore

# Directories whose contents are protocol records.
_RECORDS_PREFIX = ".contract-engineering/"

# Artifact filename pattern: <packet-id>-<suffix>.<ext>
# Packet IDs look like CENG-T023-P001.
_ARTIFACT_RE = re.compile(
    r"^\.contract-engineering/"
    r"(evidence|handoffs|decisions)/"
    r"(CENG-\w+-P\d+)"
    r"-[A-Z0-9]+"
    r"\.(?:md|yaml)$"
)

# Protocol-level files that are not owned by any single packet.  They are
# release artifacts or cross-cutting configuration that every packet may
# touch.  The scope gate allows them without a claiming work-packet.
_PROTOCOL_LEVEL_FILES = frozenset({
    ".contract-engineering/release-attestation.yaml",
    ".contract-engineering/release-signing-key.asc",
    ".contract-engineering/protocol.lock.yaml",
    ".contract-engineering/skill-feedback.md",
})

_PACKET_FILE_RE = re.compile(
    r"^\.contract-engineering/work-packets/(CENG-\w+-P\d+)\.yaml$"
)


class GateResult:
    """The outcome of evaluating a diff against packet scopes."""

    __slots__ = ("decision", "message")

    def __init__(self, decision: str, message: str) -> None:
        self.decision = decision
        self.message = message


def _has_records_path(changed_paths: Iterable[str]) -> bool:
    """Return True if any changed path is under .contract-engineering/."""
    return any(p.startswith(_RECORDS_PREFIX) for p in changed_paths)


def _extract_packet_ids(changed_paths: Iterable[str]) -> set[str]:
    """Extract packet IDs from packet files and artifact filenames in the diff."""
    ids: set[str] = set()
    for path in changed_paths:
        m = _PACKET_FILE_RE.match(path)
        if m:
            ids.add(m.group(1))
            continue
        m = _ARTIFACT_RE.match(path)
        if m:
            ids.add(m.group(2))
    return ids


def _filter_records_paths(changed_paths: Iterable[str]) -> list[str]:
    """Return only paths under .contract-engineering/."""
    return [p for p in changed_paths if p.startswith(_RECORDS_PREFIX)]


def _is_artifact_path(path: str) -> bool:
    """Return True if *path* is an evidence/handoff/decision or protocol-level artifact."""
    return _ARTIFACT_RE.match(path) is not None or path in _PROTOCOL_LEVEL_FILES


def evaluate(
    project_dir: Path | str,
    changed_paths: list[str],
    *,
    base_reachable: bool = True,
    store: RecordStore | None = None,
) -> GateResult:
    """Evaluate changed paths against packet scopes.

    Parameters
    ----------
    project_dir
        The repository root (contains ``.contract-engineering``).
    changed_paths
        Paths changed in the diff, repo-relative.
    base_reachable
        Whether the base SHA is reachable from HEAD.  When False
        (force-push), the gate skips.
    store
        Optional pre-built record store (for testing).
    """
    # Rule 1: no records paths -> pass.
    if not _has_records_path(changed_paths):
        return GateResult("pass", "no .contract-engineering paths in diff; scope gate skipped")

    # Rule 3: unreachable base SHA (force-push) -> warn and pass.
    if not base_reachable:
        return GateResult("pass", "base SHA unreachable (force-push); scope gate skipped with warning")

    # Resolve the protocol root and record store.
    project = Path(project_dir)
    if store is None:
        # The protocol root is <project>/.contract-engineering.
        root = project / ".contract-engineering"
        store = FileStore(root)

    # Collect claiming packet IDs from the diff.
    claiming_ids = _extract_packet_ids(changed_paths)

    # Verify every claiming packet exists on HEAD.
    live_packets = store.list_packets("active")
    archive_packets = store.list_packets("archive")
    all_packets = {**live_packets, **archive_packets}
    missing = claiming_ids - set(all_packets.keys())
    if missing:
        return GateResult(
            "fail",
            f"claiming packets not found on HEAD: {sorted(missing)}",
        )

    if not claiming_ids:
        # If every records path is a protocol-level file (release attestation,
        # lock, etc.), the diff is allowed without a claiming work-packet.
        records_paths = _filter_records_paths(changed_paths)
        non_protocol = [
            p for p in records_paths if not _is_artifact_path(p)
        ]
        if non_protocol:
            return GateResult(
                "fail",
                "records paths changed but no claiming packet found in diff or artifact filenames",
            )
        return GateResult(
            "pass",
            "scope gate passed; only protocol-level records changed",
        )

    # Build packet Path objects for the scope check.
    # packet_scope() derives the protocol root from the packet path.
    pkt_dir = project / ".contract-engineering" / "work-packets"
    packet_paths: list[Path] = []
    for pid in sorted(claiming_ids):
        # Prefer the active partition path; fall back to archive.
        if pid in live_packets:
            packet_paths.append(pkt_dir / f"{pid}.yaml")
        else:
            archive_dir = project / ".contract-engineering" / "archive" / "work-packets"
            packet_paths.append(archive_dir / f"{pid}.yaml")

    # Artifact paths (evidence/handoffs/decisions) are claimed by filename.
    # All other changed paths must fall within scope.in of some claiming packet.
    all_rules: list[str] = []
    for pkt_path in packet_paths:
        all_rules.extend(packet_scope(pkt_path, store=store))

    unclaimed = [
        p
        for p in changed_paths
        if not _is_artifact_path(p)
        and not any(path_matches(p, rule) for rule in all_rules)
    ]
    if unclaimed:
        return GateResult(
            "fail",
            f"changed paths not claimed by any packet: {unclaimed}",
        )

    return GateResult("pass", f"scope gate passed; claiming packets: {sorted(claiming_ids)}")


def _base_reachable(base_sha: str) -> bool:
    """Return True if *base_sha* is a reachable commit from HEAD."""
    if not base_sha:
        return False
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{base_sha}^{{commit}}"],
            capture_output=True,
        )
        if result.returncode != 0:
            return False
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", base_sha, "HEAD"],
            capture_output=True,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _changed_paths(base_sha: str, head_sha: str) -> list[str]:
    """Return the list of changed paths between *base_sha* and *head_sha*."""
    result = subprocess.check_output(
        ["git", "diff", "--name-only", base_sha, head_sha],
        text=True,
    )
    return [line for line in result.strip().splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enforce that changed paths are claimed by a work-packet scope."
    )
    parser.add_argument("--project-dir", default=".", type=Path)
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--head-sha", default="HEAD")
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        help="explicit changed path (overrides git diff when provided)",
    )
    args = parser.parse_args()

    if args.changed_path:
        changed = args.changed_path
        reachable = True
    else:
        reachable = _base_reachable(args.base_sha)
        if reachable:
            changed = _changed_paths(args.base_sha, args.head_sha)
        else:
            # Still need to know what changed; fall back to first-parent diff.
            fp = subprocess.check_output(
                ["git", "rev-list", "--max-parents=1", "HEAD"],
                text=True,
            ).strip()
            changed = _changed_paths(fp, args.head_sha)

    result = evaluate(args.project_dir, changed, base_reachable=reachable)
    if result.decision == "pass":
        print(f"scope gate: {result.message}")
        return 0
    else:
        print(f"scope gate FAILED: {result.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
