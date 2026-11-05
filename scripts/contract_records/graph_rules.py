"""Dependency graph, lock, reference, and scope enforcement rules."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PARENT = Path(__file__).resolve().parent.parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from scripts.record_store import FileStore

from .loaders import fail, path_matches


def validate_locks(packets: dict[str, dict[str, Any]]) -> None:
    active = {
        packet_id: packet
        for packet_id, packet in packets.items()
        if packet["state"] not in {"Planned", "Complete", "Cancelled"}
    }
    resources: dict[str, str] = {}
    for packet_id, packet in active.items():
        for lock in packet["locks"]:
            if lock in resources:
                fail(f"locks: {lock} claimed by both {resources[lock]} and {packet_id}")
            resources[lock] = packet_id


def validate_dependency_graph(packets: dict[str, dict[str, Any]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(packet_id: str) -> None:
        if packet_id in visiting:
            fail(f"dependencies: cycle detected at {packet_id}")
        if packet_id in visited:
            return
        visiting.add(packet_id)
        for dependency in packets[packet_id]["dependencies"]:
            visit(dependency)
        visiting.remove(packet_id)
        visited.add(packet_id)

    for packet_id in packets:
        visit(packet_id)


def validate_references(
    root: Path,
    packets: dict[str, dict[str, Any]],
    *,
    store: FileStore | None = None,
) -> None:
    if store is None:
        store = FileStore(root)
    handoffs_dir = root / "handoffs"
    evidence_dir = root / "evidence"
    for packet_id, packet in packets.items():
        for evidence_ref in packet.get("evidence_refs", []):
            if not store.evidence_exists(evidence_ref):
                fail(f"{packet_id}: missing evidence {evidence_ref}")
        handoff_ref = packet.get("handoff_ref")
        if handoff_ref and store.get_handoff(handoff_ref) is None:
            fail(f"{packet_id}: missing handoff {handoff_ref}")
    for handoff_id, handoff in store.list_handoffs().items():
        path = handoffs_dir / f"{handoff_id}.yaml"
        required = {"handoff_id", "packet_id", "sender", "receiver", "receiver_status"}
        if not isinstance(handoff, dict) or not required <= handoff.keys():
            fail(f"{path}: incomplete handoff")
        if handoff.get("handoff_id") != handoff_id:
            fail(f"{path}: handoff_id does not match filename")
        if handoff["packet_id"] not in packets:
            fail(f"{path}: unknown packet reference")
        if handoff["receiver_status"] not in {"pending", "accepted", "rejected"}:
            fail(f"{path}: invalid receiver status")
        if handoff["receiver_status"] == "accepted" and not handoff.get("receiver_notes"):
            fail(f"{path}: accepted handoff requires receiver notes")
    for path in sorted(evidence_dir.glob("*.md")):
        if not path.read_text().startswith(f"# {path.stem}"):
            fail(f"{path}: evidence heading must match filename")


def enforce_scope(packet: dict[str, Any], changed_paths: list[str]) -> None:
    included = packet["scope"]["in"]
    excluded = packet["scope"]["out"]
    for changed in changed_paths:
        if any(path_matches(changed, rule) for rule in excluded):
            fail(f"{packet['packet_id']}: changed path is explicitly out of scope: {changed}")
        if not any(path_matches(changed, rule) for rule in included):
            fail(f"{packet['packet_id']}: changed path is outside scope.in: {changed}")
