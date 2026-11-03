#!/usr/bin/env python3
"""Storage-independent record store interface with a file-backed implementation.

The ``RecordStore`` ABC defines the operations every backend must provide.
``FileStore`` implements it over today's YAML directory layout.  A future
API backend (Task Master app) can implement the same interface and pass
the same conformance suite.
"""
from __future__ import annotations

import os
import sys
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

# Ensure the scripts package is importable when run as a standalone script.
_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))
from typing import Any

import yaml


class RecordStoreError(ValueError):
    """Raised when a record store operation cannot complete."""


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class RecordStore(ABC):
    """Abstract record store for protocol records.

    All record types—packets, tracker rows, events, handoffs, leases,
    evidence, decisions—are read and written through this interface so
    that a file backend and a future API backend are interchangeable.
    """

    # -- packets -----------------------------------------------------------

    @abstractmethod
    def get_packet(
        self, packet_id: str, *, partition: str = "active"
    ) -> dict[str, Any] | None:
        """Return the packet dict, or ``None`` if it does not exist."""

    @abstractmethod
    def put_packet(
        self,
        packet_id: str,
        record: dict[str, Any],
        *,
        expected_revision: int | None = None,
        partition: str = "active",
    ) -> dict[str, Any]:
        """Write a packet, optionally checking the current revision.

        Raises :class:`RecordStoreError` if *expected_revision* is given
        and does not match ``record.get("revision", 0)``.
        """

    @abstractmethod
    def list_packets(self, partition: str = "active") -> dict[str, dict[str, Any]]:
        """Return ``{packet_id: record}`` for every packet in the partition."""

    @abstractmethod
    def delete_packet(self, packet_id: str, *, partition: str = "active") -> None:
        """Remove a packet from the store.  No-op if it does not exist."""

    @abstractmethod
    def move_packet(
        self, packet_id: str, source_partition: str, dest_partition: str
    ) -> None:
        """Move a packet between partitions atomically.  Raises if not found."""

    # -- tracker -----------------------------------------------------------

    @abstractmethod
    def get_tracker_index(self, partition: str = "active") -> dict[str, Any] | None:
        """Return the raw tracker index document, or ``None`` if missing."""

    @abstractmethod
    def put_tracker_index(
        self, document: dict[str, Any], *, partition: str = "active"
    ) -> None:
        """Write the tracker index document."""

    @abstractmethod
    def get_shard(self, relative_path: str) -> dict[str, Any]:
        """Return a shard document by its path relative to the tracker root."""

    @abstractmethod
    def put_shard(self, relative_path: str, document: dict[str, Any]) -> None:
        """Write a shard document."""

    @abstractmethod
    def list_shard_paths(self) -> list[str]:
        """Return the declared shard paths from the active index."""

    @abstractmethod
    def get_tracker_rows(self, partition: str = "active") -> list[dict[str, Any]]:
        """Return all tracker rows (index + shards) for the partition."""

    @abstractmethod
    def move_tracker_row(
        self, packet_id: str, source_partition: str, dest_partition: str
    ) -> None:
        """Move a row from the source partition to the destination partition."""

    # -- events ------------------------------------------------------------

    @abstractmethod
    def append_event(self, task_id: str, event: dict[str, Any]) -> None:
        """Append an event.  No-op if the ``event_id`` already exists."""

    @abstractmethod
    def list_events(self, task_id: str) -> list[dict[str, Any]]:
        """Return events for *task_id*, or an empty list if none exist."""

    @abstractmethod
    def get_event_document(self, task_id: str) -> dict[str, Any] | None:
        """Return the full event document (task_id, schema_version, events) or ``None``."""

    # -- handoffs ----------------------------------------------------------

    @abstractmethod
    def get_handoff(self, handoff_id: str) -> dict[str, Any] | None:
        """Return the handoff dict, or ``None`` if it does not exist."""

    @abstractmethod
    def put_handoff(self, handoff_id: str, record: dict[str, Any]) -> None:
        """Write a handoff record."""

    @abstractmethod
    def list_handoffs(self) -> dict[str, dict[str, Any]]:
        """Return ``{handoff_id: record}`` for every handoff."""

    # -- leases ------------------------------------------------------------

    @abstractmethod
    def get_lease(self, packet_id: str) -> dict[str, Any] | None:
        """Return the lease dict, or ``None`` if it does not exist."""

    @abstractmethod
    def put_lease(self, packet_id: str, record: dict[str, Any]) -> None:
        """Write a lease record."""

    # -- evidence ----------------------------------------------------------

    @abstractmethod
    def get_evidence(self, evidence_id: str) -> str | None:
        """Return evidence file contents, or ``None`` if it does not exist."""

    @abstractmethod
    def put_evidence(self, evidence_id: str, content: str) -> None:
        """Write evidence file contents."""

    @abstractmethod
    def evidence_exists(self, evidence_id: str) -> bool:
        """Return ``True`` if the evidence file exists."""

    # -- snapshot ----------------------------------------------------------

    @abstractmethod
    def export_snapshot(self) -> dict[str, Any]:
        """Return a serialisable snapshot of every record in the store."""

    @abstractmethod
    def import_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Write a snapshot into this store (must start from an empty root)."""


# ---------------------------------------------------------------------------
# File backend
# ---------------------------------------------------------------------------

_ACTIVE_PACKETS = "work-packets"
_ARCHIVE_PACKETS = "archive/work-packets"
_ACTIVE_TRACKER = "tracker"
_ARCHIVE_TRACKER = "tracker/archive"
_EVENTS = "tracker/events"
_SHARDS = "tracker/shards"
_HANDOFFS = "handoffs"
_LEASES = "leases"
_EVIDENCE = "evidence"


def _partition_packets(partition: str) -> str:
    if partition == "active":
        return _ACTIVE_PACKETS
    if partition == "archive":
        return _ARCHIVE_PACKETS
    raise RecordStoreError(f"unknown packet partition: {partition}")


def _partition_tracker(partition: str) -> str:
    if partition == "active":
        return _ACTIVE_TRACKER
    if partition == "archive":
        return _ARCHIVE_TRACKER
    raise RecordStoreError(f"unknown tracker partition: {partition}")


class FileStore(RecordStore):
    """File-backed record store over the standard YAML directory layout."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    # -- internal helpers --------------------------------------------------

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
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

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _packet_path(self, packet_id: str, partition: str) -> Path:
        return self.root / _partition_packets(partition) / f"{packet_id}.yaml"

    def _tracker_index_path(self, partition: str) -> Path:
        return self.root / _partition_tracker(partition) / "index.yaml"

    def _events_path(self, task_id: str) -> Path:
        return self.root / _EVENTS / f"{task_id}.yaml"

    def _shard_path(self, relative_path: str) -> Path:
        """Resolve a shard path declared in the tracker index.

        Shard paths may be relative to the tracker directory
        (``shards/CENG-T015.yaml``) or to the protocol root
        (``tracker/shards/CENG-T015.yaml``).  Normalise both forms
        to ``root / tracker / shards/...``.
        """
        normalised = relative_path
        if normalised.startswith("tracker/"):
            normalised = normalised[len("tracker/"):]
        return self.root / _ACTIVE_TRACKER / normalised

    def _handoff_path(self, handoff_id: str) -> Path:
        return self.root / _HANDOFFS / f"{handoff_id}.yaml"

    def _lease_path(self, packet_id: str) -> Path:
        return self.root / _LEASES / f"{packet_id}.yaml"

    def _evidence_path(self, evidence_id: str) -> Path:
        return self.root / _EVIDENCE / f"{evidence_id}.md"

    # -- packets -----------------------------------------------------------

    def get_packet(
        self, packet_id: str, *, partition: str = "active"
    ) -> dict[str, Any] | None:
        path = self._packet_path(packet_id, partition)
        if not path.is_file():
            return None
        return self._read_yaml(path)

    def put_packet(
        self,
        packet_id: str,
        record: dict[str, Any],
        *,
        expected_revision: int | None = None,
        partition: str = "active",
    ) -> dict[str, Any]:
        if expected_revision is not None:
            current = self.get_packet(packet_id, partition=partition)
            current_revision = int((current or {}).get("revision", 0))
            if expected_revision != current_revision:
                raise RecordStoreError(
                    f"stale packet revision: expected {expected_revision}, "
                    f"current {current_revision}"
                )
        path = self._packet_path(packet_id, partition)
        self._write(path, record)
        return record

    def list_packets(self, partition: str = "active") -> dict[str, dict[str, Any]]:
        directory = self.root / _partition_packets(partition)
        if not directory.is_dir():
            return {}
        result: dict[str, dict[str, Any]] = {}
        for path in sorted(directory.glob("*.yaml")):
            record = self._read_yaml(path)
            pid = record.get("packet_id", path.stem)
            result[pid] = record
        return result

    def delete_packet(self, packet_id: str, *, partition: str = "active") -> None:
        path = self._packet_path(packet_id, partition)
        if path.is_file():
            path.unlink()

    def move_packet(
        self, packet_id: str, source_partition: str, dest_partition: str
    ) -> None:
        packet = self.get_packet(packet_id, partition=source_partition)
        if packet is None:
            raise RecordStoreError(
                f"packet {packet_id} not found in {source_partition}"
            )
        self.put_packet(packet_id, packet, partition=dest_partition)
        self.delete_packet(packet_id, partition=source_partition)

    # -- tracker -----------------------------------------------------------

    def get_tracker_index(self, partition: str = "active") -> dict[str, Any] | None:
        path = self._tracker_index_path(partition)
        if not path.is_file():
            return None
        return self._read_yaml(path)

    def put_tracker_index(
        self, document: dict[str, Any], *, partition: str = "active"
    ) -> None:
        path = self._tracker_index_path(partition)
        self._write(path, document)

    def get_shard(self, relative_path: str) -> dict[str, Any]:
        path = self._shard_path(relative_path)
        if not path.is_file():
            return {"rows": []}
        return self._read_yaml(path)

    def put_shard(self, relative_path: str, document: dict[str, Any]) -> None:
        path = self._shard_path(relative_path)
        self._write(path, document)

    def list_shard_paths(self) -> list[str]:
        index = self.get_tracker_index()
        if index is None:
            return []
        return list(index.get("shards", []))

    def get_tracker_rows(self, partition: str = "active") -> list[dict[str, Any]]:
        index = self.get_tracker_index(partition)
        if index is None:
            return []
        rows: list[dict[str, Any]] = list(index.get("rows", []))
        if partition == "active":
            for shard_path in index.get("shards", []):
                shard = self.get_shard(shard_path)
                rows.extend(shard.get("rows", []))
        return rows

    def move_tracker_row(
        self, packet_id: str, source_partition: str, dest_partition: str
    ) -> None:
        src_index = self.get_tracker_index(source_partition)
        if src_index is None:
            raise RecordStoreError(
                f"source tracker index not found: {source_partition}"
            )

        # Search in index rows first, then in shards (active only).
        row: dict[str, Any] | None = None

        for r in src_index.get("rows", []):
            if r.get("packet_id") == packet_id:
                row = r
                src_index["rows"].remove(r)
                break

        if row is None and source_partition == "active":
            for shard_path in src_index.get("shards", []):
                shard = self.get_shard(shard_path)
                for r in shard.get("rows", []):
                    if r.get("packet_id") == packet_id:
                        row = r
                        shard["rows"].remove(r)
                        self.put_shard(shard_path, shard)
                        break
                if row is not None:
                    break

        if row is None:
            raise RecordStoreError(
                f"packet {packet_id} not found in {source_partition} tracker"
            )

        self.put_tracker_index(src_index, partition=source_partition)

        dest_index = self.get_tracker_index(dest_partition)
        if dest_index is None:
            dest_index = {
                "tracker_schema_version": 1,
                "partition": dest_partition,
                "max_rows": 50 if dest_partition == "archive" else 25,
                "rows": [],
                "shards": [],
            }
        dest_index.setdefault("rows", []).append(row)
        self.put_tracker_index(dest_index, partition=dest_partition)

    # -- events ------------------------------------------------------------

    def append_event(self, task_id: str, event: dict[str, Any]) -> None:
        path = self._events_path(task_id)
        if path.is_file():
            document = self._read_yaml(path)
        else:
            document = {"task_id": task_id, "schema_version": 1, "events": []}
        events = document.setdefault("events", [])
        event_id = event.get("event_id")
        if event_id and any(e.get("event_id") == event_id for e in events):
            return
        events.append(event)
        self._write(path, document)

    def list_events(self, task_id: str) -> list[dict[str, Any]]:
        path = self._events_path(task_id)
        if not path.is_file():
            return []
        document = self._read_yaml(path)
        return list(document.get("events", []))

    def get_event_document(self, task_id: str) -> dict[str, Any] | None:
        path = self._events_path(task_id)
        if not path.is_file():
            return None
        return self._read_yaml(path)

    # -- handoffs ----------------------------------------------------------

    def get_handoff(self, handoff_id: str) -> dict[str, Any] | None:
        path = self._handoff_path(handoff_id)
        if not path.is_file():
            return None
        return self._read_yaml(path)

    def put_handoff(self, handoff_id: str, record: dict[str, Any]) -> None:
        path = self._handoff_path(handoff_id)
        self._write(path, record)

    def list_handoffs(self) -> dict[str, dict[str, Any]]:
        directory = self.root / _HANDOFFS
        if not directory.is_dir():
            return {}
        result: dict[str, dict[str, Any]] = {}
        for path in sorted(directory.glob("*.yaml")):
            record = self._read_yaml(path)
            hid = record.get("handoff_id", path.stem)
            result[hid] = record
        return result

    # -- leases ------------------------------------------------------------

    def get_lease(self, packet_id: str) -> dict[str, Any] | None:
        path = self._lease_path(packet_id)
        if not path.is_file():
            return None
        return self._read_yaml(path)

    def put_lease(self, packet_id: str, record: dict[str, Any]) -> None:
        path = self._lease_path(packet_id)
        self._write(path, record)

    # -- evidence ----------------------------------------------------------

    def get_evidence(self, evidence_id: str) -> str | None:
        path = self._evidence_path(evidence_id)
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def put_evidence(self, evidence_id: str, content: str) -> None:
        path = self._evidence_path(evidence_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def evidence_exists(self, evidence_id: str) -> bool:
        return self._evidence_path(evidence_id).is_file()

    # -- snapshot ----------------------------------------------------------

    def export_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {}

        def _collect_dir(rel_dir: str, *, yaml_only: bool = True) -> dict[str, str]:
            directory = self.root / rel_dir
            if not directory.is_dir():
                return {}
            result: dict[str, str] = {}
            for path in sorted(directory.glob("*.yaml" if yaml_only else "*.md")):
                result[f"{rel_dir}/{path.name}"] = path.read_text(encoding="utf-8")
            return result

        snapshot["packets"] = _collect_dir(_ACTIVE_PACKETS)
        snapshot["archive_packets"] = _collect_dir(_ARCHIVE_PACKETS)
        snapshot["tracker_index"] = _collect_dir(_ACTIVE_TRACKER)
        snapshot["tracker_archive_index"] = _collect_dir(_ARCHIVE_TRACKER)
        snapshot["shards"] = _collect_dir(_SHARDS)
        snapshot["events"] = _collect_dir(_EVENTS)
        snapshot["handoffs"] = _collect_dir(_HANDOFFS)
        snapshot["leases"] = _collect_dir(_LEASES)
        snapshot["evidence"] = _collect_dir(_EVIDENCE, yaml_only=False)
        return snapshot

    def import_snapshot(self, snapshot: dict[str, Any]) -> None:
        for section in (
            "packets",
            "archive_packets",
            "tracker_index",
            "tracker_archive_index",
            "shards",
            "events",
            "handoffs",
            "leases",
            "evidence",
        ):
            for rel_path, content in snapshot.get(section, {}).items():
                full = self.root / rel_path
                full.parent.mkdir(parents=True, exist_ok=True)
                fd, name = tempfile.mkstemp(dir=full.parent, prefix=f".{full.name}.")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(name, full)
                finally:
                    if os.path.exists(name):
                        os.unlink(name)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def resolve_record_store(
    lock: dict[str, Any], project_dir: Path | str
) -> RecordStore:
    """Construct a :class:`RecordStore` from the lock's ``project.record_store``."""
    project = lock.get("project", {})
    config = project.get("record_store", {})
    backend = config.get("backend", "file")
    if backend == "file":
        protocol_root = project.get("protocol_root", ".contract-engineering")
        root = Path(protocol_root)
        if not root.is_absolute():
            root = Path(project_dir) / root
        return FileStore(root)
    raise RecordStoreError(f"unsupported record_store backend: {backend}")
