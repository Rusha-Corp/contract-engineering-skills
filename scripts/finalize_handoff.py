#!/usr/bin/env python3
"""Create and validate revision-bound packet handoffs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from scripts.record_store import FileStore, RecordStore


class HandoffError(ValueError):
    """Raised when a handoff cannot be finalized or accepted."""


def scope_digest(packet: dict[str, Any]) -> str:
    payload = {
        "packet_id": packet["packet_id"],
        "scope": packet.get("scope", {}),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validate_handoff(
    root: Path | str,
    packet: dict[str, Any],
    *,
    store: RecordStore | None = None,
) -> dict[str, Any]:
    """Validate the accepted handoff that permits a Complete transition."""
    if store is None:
        store = FileStore(root)
    handoff_ref = packet.get("handoff_ref")
    if not handoff_ref:
        raise HandoffError("handoff reference is required")
    handoff = store.get_handoff(handoff_ref)
    if handoff is None:
        raise HandoffError(f"handoff is missing: {handoff_ref}")
    if handoff.get("packet_id") != packet.get("packet_id"):
        raise HandoffError("handoff packet identity does not match")
    if handoff.get("receiver_status") != "accepted":
        raise HandoffError("handoff receiver acceptance is required")
    if not handoff.get("receiver_notes"):
        raise HandoffError("accepted handoff requires receiver notes")
    accepted_packet_revision = handoff.get(
        "accepted_packet_revision", handoff.get("accepted_revision")
    )
    if accepted_packet_revision != packet.get("revision", 0):
        raise HandoffError("handoff revision does not match packet revision")
    if handoff.get("accepted_scope_digest") != scope_digest(packet):
        raise HandoffError("handoff scope digest does not match packet scope")
    required_evidence = set(packet.get("evidence_refs", []))
    accepted_evidence = set(handoff.get("accepted_evidence_refs", []))
    if not required_evidence.issubset(accepted_evidence):
        raise HandoffError("handoff does not accept all packet evidence")
    for evidence_ref in required_evidence:
        if not store.evidence_exists(evidence_ref):
            raise HandoffError(f"packet evidence is missing: {evidence_ref}")
    return handoff


def finalize(
    root: Path | str,
    packet_id: str,
    handoff_id: str,
    *,
    head_revision: str,
    changed_resources: list[dict[str, str]],
    evidence_refs: list[str],
    store: RecordStore | None = None,
) -> dict[str, Any]:
    """Bind a pending handoff to the current packet content."""
    if store is None:
        store = FileStore(root)
    packet = store.get_packet(packet_id)
    handoff = store.get_handoff(handoff_id)
    if packet is None or handoff is None:
        raise HandoffError("packet and handoff files are required")
    if handoff.get("packet_id") != packet_id:
        raise HandoffError("handoff packet identity does not match")
    handoff["head_revision"] = head_revision
    handoff["scope_digest"] = scope_digest(packet)
    handoff["changed_resources"] = changed_resources
    handoff["evidence_refs"] = evidence_refs
    store.put_handoff(handoff_id, handoff)
    return handoff


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".contract-engineering"))
    parser.add_argument("--packet", required=True)
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--head-revision", required=True)
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--changed-resource", action="append", default=[])
    args = parser.parse_args()
    resources = []
    for value in args.changed_resource:
        try:
            path, digest = value.split("=", 1)
        except ValueError as exc:
            raise SystemExit("--changed-resource must be path=sha256") from exc
        resources.append({"path": path, "sha256": digest})
    result = finalize(
        args.root,
        args.packet,
        args.handoff,
        head_revision=args.head_revision,
        changed_resources=resources,
        evidence_refs=args.evidence_ref,
    )
    print(yaml.safe_dump(result, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
