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

from scripts.record_store import FileStore

STATES = {"Planned", "Claimed", "DesignReview", "DesignBlocked", "DataReview",
          "DataBlocked", "Ready", "Implementing", "Validation", "Rework",
          "Handoff", "Complete", "Interrupted", "Cancelled"}
ALLOWED = {
    "Planned": {"Claimed", "Cancelled"},
    "Claimed": {"DesignReview", "DataReview", "Ready", "Implementing", "Interrupted", "Cancelled"},
    "DesignReview": {"DesignBlocked", "DataReview", "Cancelled"},
    "DesignBlocked": {"DesignReview", "Cancelled"},
    "DataReview": {"DataBlocked", "Ready", "Cancelled"},
    "DataBlocked": {"DataReview", "Cancelled"},
    "Ready": {"Implementing", "Interrupted", "Cancelled"},
    "Implementing": {"Validation", "Interrupted", "Cancelled", "Rework"},
    "Validation": {"Handoff", "Rework", "Interrupted"},
    "Rework": {"Implementing", "Cancelled"},
    "Handoff": {"Complete", "Rework"},
    "Interrupted": {"Claimed", "Implementing", "Cancelled"},
}


class TransitionError(ValueError):
    pass


class TransitionStore:
    def __init__(self, root: Path | str = ".contract-engineering"):
        self.root = Path(root)
        self.store = FileStore(self.root)
        self.journal = self.root / "journal"

    def _load(self, packet_id: str) -> dict[str, Any]:
        packet = self.store.get_packet(packet_id)
        if packet is None:
            raise TransitionError(f"unknown packet: {packet_id}")
        return packet

    def _write_journal(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(value, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _journal(self, operation: dict[str, Any]) -> Path:
        self.journal.mkdir(parents=True, exist_ok=True)
        identity = hashlib.sha256(json.dumps(operation, sort_keys=True).encode()).hexdigest()
        path = self.journal / f"{identity}.json"
        if not path.exists():
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({**operation, "status": "prepared"}, indent=2), encoding="utf-8")
            os.replace(tmp, path)
        return path

    def transition(
        self,
        packet_id: str,
        destination: str,
        actor: str,
        reason: str,
        *,
        expected_revision: int | None = None,
        fencing_token: str | None = None,
    ) -> dict[str, Any]:
        packet = self._load(packet_id)
        source = packet.get("state")
        if source == destination:
            return packet
        if destination not in STATES or destination not in ALLOWED.get(source, set()):
            self._blocked(packet_id, source, destination, actor, reason, "illegal lifecycle transition")
            raise TransitionError(f"blocked transition {source} -> {destination}")
        current_revision = int(packet.get("revision", 0))
        if expected_revision is None:
            raise TransitionError("expected revision is required for a state transition")
        if expected_revision != current_revision:
            self._blocked(packet_id, source, destination, actor, reason, "stale packet revision")
            raise TransitionError(
                f"stale packet revision: expected {expected_revision}, current {current_revision}"
            )
        if destination == "Complete" and not packet.get("handoff_ref"):
            self._blocked(packet_id, source, destination, actor, reason, "handoff acceptance is required")
            raise TransitionError("blocked transition: handoff acceptance is required")
        if destination == "Complete":
            try:
                from scripts.finalize_handoff import HandoffError, validate_handoff

                validate_handoff(self.root, packet)
            except HandoffError as exc:
                self._blocked(packet_id, source, destination, actor, reason, str(exc))
                raise TransitionError(f"blocked transition: {exc}") from exc
        if packet.get("risk_tier") in {"high", "critical"} or packet.get("external_effects"):
            try:
                from scripts.packet_leases import LeaseError, LeaseManager

                LeaseManager(self.root).validate(
                    packet_id,
                    fencing_token or os.environ.get("CE_FENCING_TOKEN", ""),
                )
            except LeaseError as exc:
                self._blocked(packet_id, source, destination, actor, reason, str(exc))
                raise TransitionError(f"blocked transition: lease {exc}") from exc
        operation = {
            "kind": "transition",
            "packet_id": packet_id,
            "source": source,
            "destination": destination,
            "actor": actor,
            "reason": reason,
            "expected_revision": expected_revision,
            "event_id": self._next_event_id(packet["task_id"]),
        }
        journal = self._journal(operation)
        self._apply_transition(operation)
        self._write_journal(journal, {**operation, "status": "committed"})
        return self._load(packet_id)

    def _next_event_id(self, task_id: str) -> str:
        events = self.store.list_events(task_id)
        return f"{task_id}-E{len(events) + 1:03d}"

    def _update_tracker(self, packet: dict[str, Any]) -> None:
        index = self.store.get_tracker_index()
        if index is None:
            return
        # Check index rows.
        for row in index.get("rows", []):
            if row.get("packet_id") == packet["packet_id"]:
                row["state"] = packet["state"]
                row["owner"] = packet.get("owner", row.get("owner", ""))
                row["reviewer"] = packet.get("reviewer", row.get("reviewer", ""))
                row["locks"] = packet.get("locks", row.get("locks", []))
                row["updated_at"] = datetime.now(timezone.utc).date().isoformat()
                self.store.put_tracker_index(index)
                return
        # Check shard rows.
        for shard_path in index.get("shards", []):
            shard = self.store.get_shard(shard_path)
            for row in shard.get("rows", []):
                if row.get("packet_id") == packet["packet_id"]:
                    row["state"] = packet["state"]
                    row["owner"] = packet.get("owner", row.get("owner", ""))
                    row["reviewer"] = packet.get("reviewer", row.get("reviewer", ""))
                    row["locks"] = packet.get("locks", row.get("locks", []))
                    row["updated_at"] = datetime.now(timezone.utc).date().isoformat()
                    self.store.put_shard(shard_path, shard)
                    return

    def _append_event(self, operation: dict[str, Any], packet: dict[str, Any]) -> None:
        event = {
            "event_id": operation["event_id"],
            "packet_id": packet["packet_id"],
            "type": "transition",
            "actor": operation["actor"],
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "summary": (
                f"{operation['source']} -> {operation['destination']}: "
                f"{operation['reason']}"
            ),
        }
        self.store.append_event(packet["task_id"], event)

    def _apply_transition(self, operation: dict[str, Any]) -> None:
        packet = self._load(operation["packet_id"])
        current_revision = int(packet.get("revision", 0))
        if packet.get("state") == operation["destination"] and current_revision == operation["expected_revision"] + 1:
            self._update_tracker(packet)
            self._append_event(operation, packet)
            return
        if (
            packet.get("state") != operation["source"]
            or current_revision != operation["expected_revision"]
        ):
            raise TransitionError("prepared transition no longer matches packet revision")
        packet["state"] = operation["destination"]
        packet["revision"] = current_revision + 1
        if operation["destination"] == "Complete":
            packet["locks"] = []
        packet["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.store.put_packet(operation["packet_id"], packet)
        self._update_tracker(packet)
        self._append_event(operation, packet)

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
        self.store.put_packet(packet_id, packet)
        self._write_journal(journal, {**operation, "status": "committed"})
        return packet

    def _blocked(self, packet_id: str, source: str, destination: str, actor: str, reason: str, failure: str) -> None:
        operation = {"kind": "blocked", "packet_id": packet_id, "source": source,
                     "destination": destination, "actor": actor, "reason": reason,
                     "failure": failure, "redacted": True}
        journal = self._journal(operation)
        self._write_journal(journal, {**operation, "status": "committed"})

    def recover(self) -> list[str]:
        recovered = []
        for path in self.journal.glob("*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("status") != "prepared":
                continue
            if record.get("kind") == "transition":
                packet = self._load(record["packet_id"])
                record.setdefault("expected_revision", int(packet.get("revision", 0)))
                record.setdefault("event_id", self._next_event_id(packet["task_id"]))
                self._apply_transition(record)
                record["status"] = "committed"
                self._write_journal(path, record)
                recovered.append(path.name)
            elif record.get("kind") == "reassign":
                packet = self._load(record["packet_id"])
                if packet.get("owner") != record["owner"]:
                    packet["owner"] = record["owner"]
                    packet["fencing_token"] = record.get("fencing_token", "")
                    packet["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self.store.put_packet(record["packet_id"], packet)
                record["status"] = "committed"
                self._write_journal(path, record)
                recovered.append(path.name)
        return recovered

    def doctor(self) -> dict[str, Any]:
        inconsistencies = []
        for packet_id, packet in self.store.list_packets().items():
            if packet.get("state") not in STATES:
                inconsistencies.append(f"{packet_id}.yaml: invalid state")
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
    t = sub.add_parser("transition"); t.add_argument("packet"); t.add_argument("destination"); t.add_argument("--actor", required=True); t.add_argument("--reason", default=""); t.add_argument("--expected-revision", required=True, type=int)
    r = sub.add_parser("reassign"); r.add_argument("packet"); r.add_argument("owner"); r.add_argument("--actor", required=True); r.add_argument("--reason", default=""); r.add_argument("--force", action="store_true")
    sub.add_parser("doctor")
    e = sub.add_parser("explain-block"); e.add_argument("packet"); e.add_argument("destination")
    args = parser.parse_args(); store = TransitionStore(args.root)
    if args.command == "transition": result = store.transition(args.packet, args.destination, args.actor, args.reason, expected_revision=args.expected_revision)
    elif args.command == "reassign": result = store.reassign(args.packet, args.owner, args.reason, actor=args.actor, force=args.force)
    elif args.command == "doctor": result = store.doctor()
    else: result = store.explain_block(args.packet, args.destination)
    print(json.dumps(result, indent=2, default=str)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
