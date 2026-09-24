#!/usr/bin/env python3
"""Create and validate revision-bound packet handoffs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml


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


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise HandoffError(f"{path}: expected a mapping")
    return value


def validate_handoff(root: Path | str, packet: dict[str, Any]) -> dict[str, Any]:
    """Validate the accepted handoff that permits a Complete transition."""
    handoff_ref = packet.get("handoff_ref")
    if not handoff_ref:
        raise HandoffError("handoff reference is required")
    path = Path(root) / "handoffs" / f"{handoff_ref}.yaml"
    if not path.is_file():
        raise HandoffError(f"handoff is missing: {handoff_ref}")
    handoff = _load_yaml(path)
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
        if not (Path(root) / "evidence" / f"{evidence_ref}.md").is_file():
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
) -> dict[str, Any]:
    """Bind a pending handoff to the current packet content."""
    root_path = Path(root)
    packet_path = root_path / "work-packets" / f"{packet_id}.yaml"
    handoff_path = root_path / "handoffs" / f"{handoff_id}.yaml"
    if not packet_path.is_file() or not handoff_path.is_file():
        raise HandoffError("packet and handoff files are required")
    packet = _load_yaml(packet_path)
    handoff = _load_yaml(handoff_path)
    if handoff.get("packet_id") != packet_id:
        raise HandoffError("handoff packet identity does not match")
    handoff["head_revision"] = head_revision
    handoff["scope_digest"] = scope_digest(packet)
    handoff["changed_resources"] = changed_resources
    handoff["evidence_refs"] = evidence_refs
    _write(handoff_path, handoff)
    return handoff


def _write(path: Path, value: dict[str, Any]) -> None:
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            yaml.safe_dump(value, stream, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


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
