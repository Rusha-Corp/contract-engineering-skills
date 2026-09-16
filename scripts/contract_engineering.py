#!/usr/bin/env python3
"""Crash-recoverable local packet coordination operations."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

STATES = {"Planned", "Claimed", "DesignReview", "DesignBlocked", "DataReview",
          "DataBlocked", "Ready", "Implementing", "Validation", "Rework",
          "Handoff", "Complete", "Interrupted", "Cancelled"}
ALLOWED = {
    "Ready": {"Claimed", "Implementing", "Cancelled"},
    "Claimed": {"Implementing", "Interrupted", "Cancelled"},
    "Implementing": {"Validation", "Interrupted", "Cancelled", "Rework"},
    "Validation": {"Handoff", "Rework", "Interrupted"},
    "Rework": {"Implementing", "Cancelled"},
    "Handoff": {"Complete", "Rework"},
}


class TransitionError(ValueError):
    pass


class TransitionStore:
    def __init__(self, root: Path | str = ".contract-engineering"):
        self.root = Path(root)
        self.packets = self.root / "work-packets"
        self.journal = self.root / "journal"
        self.journal.mkdir(parents=True, exist_ok=True)

    def _path(self, packet_id: str) -> Path:
        path = self.packets / f"{packet_id}.yaml"
        if not path.is_file():
            raise TransitionError(f"unknown packet: {packet_id}")
        return path

    def _load(self, packet_id: str) -> dict[str, Any]:
        return yaml.safe_load(self._path(packet_id).read_text(encoding="utf-8"))

    def _write(self, path: Path, value: Any) -> None:
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

    def _journal(self, operation: dict[str, Any]) -> Path:
        identity = hashlib.sha256(json.dumps(operation, sort_keys=True).encode()).hexdigest()
        path = self.journal / f"{identity}.json"
        if not path.exists():
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({**operation, "status": "prepared"}, indent=2), encoding="utf-8")
            os.replace(tmp, path)
        return path

    def transition(self, packet_id: str, destination: str, actor: str, reason: str) -> dict[str, Any]:
        packet = self._load(packet_id)
        source = packet.get("state")
        if source == destination:
            return packet
        if destination not in STATES or destination not in ALLOWED.get(source, set()):
            self._blocked(packet_id, source, destination, actor, reason, "illegal lifecycle transition")
            raise TransitionError(f"blocked transition {source} -> {destination}")
        if destination == "Complete" and not packet.get("handoff_ref"):
            self._blocked(packet_id, source, destination, actor, reason, "handoff acceptance is required")
            raise TransitionError("blocked transition: handoff acceptance is required")
        operation = {"kind": "transition", "packet_id": packet_id, "source": source,
                     "destination": destination, "actor": actor, "reason": reason}
        journal = self._journal(operation)
        if packet["state"] != destination:
            packet["state"] = destination
            packet["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write(self._path(packet_id), packet)
        journal.write_text(json.dumps({**operation, "status": "committed"}, indent=2), encoding="utf-8")
        return packet

    def reassign(self, packet_id: str, owner: str, reason: str, *, actor: str, force: bool = False) -> dict[str, Any]:
        packet = self._load(packet_id)
        if packet.get("owner") == owner:
            return packet
        if not force:
            raise TransitionError("lease is not proven expired, revoked, or released")
        operation = {"kind": "reassign", "packet_id": packet_id, "owner": owner,
                     "actor": actor, "reason": reason, "fencing_token": secrets.token_hex(16)}
        journal = self._journal(operation)
        packet["owner"] = owner
        packet["fencing_token"] = operation["fencing_token"]
        packet["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write(self._path(packet_id), packet)
        journal.write_text(json.dumps({**operation, "status": "committed"}, indent=2), encoding="utf-8")
        return packet

    def _blocked(self, packet_id: str, source: str, destination: str, actor: str, reason: str, failure: str) -> None:
        operation = {"kind": "blocked", "packet_id": packet_id, "source": source,
                     "destination": destination, "actor": actor, "reason": reason,
                     "failure": failure, "redacted": True}
        self._journal(operation)

    def recover(self) -> list[str]:
        recovered = []
        for path in self.journal.glob("*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("status") != "prepared":
                continue
            if record.get("kind") == "transition":
                packet = self._load(record["packet_id"])
                if packet.get("state") == record["source"]:
                    packet["state"] = record["destination"]
                    self._write(self._path(record["packet_id"]), packet)
                record["status"] = "committed"
                path.write_text(json.dumps(record, indent=2), encoding="utf-8")
                recovered.append(path.name)
        return recovered

    def doctor(self) -> dict[str, Any]:
        inconsistencies = []
        for path in self.packets.glob("*.yaml"):
            packet = yaml.safe_load(path.read_text(encoding="utf-8"))
            if packet.get("state") not in STATES:
                inconsistencies.append(f"{path.name}: invalid state")
        return {"inconsistencies": inconsistencies, "pending_journal": [
            p.name for p in self.journal.glob("*.json")
            if json.loads(p.read_text()).get("status") == "prepared"
        ]}

    def explain_block(self, packet_id: str, destination: str) -> dict[str, Any]:
        packet = self._load(packet_id)
        failures = []
        if destination not in ALLOWED.get(packet.get("state"), set()):
            failures.append(f"{packet.get('state')} cannot transition to {destination}")
        if destination == "Complete" and not packet.get("handoff_ref"):
            failures.append("handoff acceptance is required")
        return {"packet_id": packet_id, "source": packet.get("state"),
                "destination": destination, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".contract-engineering"))
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("transition"); t.add_argument("packet"); t.add_argument("destination"); t.add_argument("--actor", required=True); t.add_argument("--reason", default="")
    r = sub.add_parser("reassign"); r.add_argument("packet"); r.add_argument("owner"); r.add_argument("--actor", required=True); r.add_argument("--reason", default=""); r.add_argument("--force", action="store_true")
    sub.add_parser("doctor")
    e = sub.add_parser("explain-block"); e.add_argument("packet"); e.add_argument("destination")
    args = parser.parse_args(); store = TransitionStore(args.root)
    if args.command == "transition": result = store.transition(args.packet, args.destination, args.actor, args.reason)
    elif args.command == "reassign": result = store.reassign(args.packet, args.owner, args.reason, actor=args.actor, force=args.force)
    elif args.command == "doctor": result = store.doctor()
    else: result = store.explain_block(args.packet, args.destination)
    print(json.dumps(result, indent=2, default=str)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
