"""Conformance and unit tests for the RecordStore interface and FileStore backend."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

from scripts.record_store import FileStore, RecordStore, RecordStoreError, resolve_record_store


class FileStoreBasicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / ".contract-engineering"
        self.store: RecordStore = FileStore(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_get_packet_returns_none_when_missing(self) -> None:
        self.assertIsNone(self.store.get_packet("CENG-T999-P001"))

    def test_put_then_get_packet_round_trips(self) -> None:
        packet = {"packet_id": "CENG-T013-P004", "task_id": "CENG-T013",
                  "state": "Planned", "revision": 0}
        self.store.put_packet("CENG-T013-P004", packet)
        result = self.store.get_packet("CENG-T013-P004")
        assert result is not None
        self.assertEqual(result["packet_id"], "CENG-T013-P004")
        self.assertEqual(result["state"], "Planned")

    def test_put_packet_rejects_stale_revision(self) -> None:
        packet = {"packet_id": "CENG-T013-P004", "revision": 0}
        self.store.put_packet("CENG-T013-P004", packet)
        with self.assertRaises(RecordStoreError):
            self.store.put_packet(
                "CENG-T013-P004",
                {"packet_id": "CENG-T013-P004", "revision": 0},
                expected_revision=5,
            )

    def test_get_tracker_rows_empty_when_no_index(self) -> None:
        self.assertEqual(self.store.get_tracker_rows(), [])

    def test_append_event_is_idempotent_on_duplicate_event_id(self) -> None:
        event = {
            "event_id": "CENG-T013-E001",
            "packet_id": "CENG-T013-P004",
            "type": "transition",
            "actor": "worker",
            "occurred_at": "2026-01-01T00:00:00Z",
            "summary": "test",
        }
        self.store.append_event("CENG-T013", event)
        self.store.append_event("CENG-T013", event)
        events = self.store.list_events("CENG-T013")
        self.assertEqual(len(events), 1)

    def test_list_events_empty_when_no_file(self) -> None:
        self.assertEqual(self.store.list_events("CENG-T999"), [])

    def test_get_tracker_index_returns_none_when_missing(self) -> None:
        self.assertIsNone(self.store.get_tracker_index())

    def test_list_packets_active_empty_when_no_dir(self) -> None:
        self.assertEqual(self.store.list_packets("active"), {})

    def test_list_packets_archive_empty_when_no_dir(self) -> None:
        self.assertEqual(self.store.list_packets("archive"), {})

    def test_put_packet_in_archive_partition(self) -> None:
        packet = {"packet_id": "CENG-T013-P004", "revision": 0}
        self.store.put_packet("CENG-T013-P004", packet, partition="archive")
        result = self.store.get_packet("CENG-T013-P004", partition="archive")
        assert result is not None
        self.assertEqual(result["packet_id"], "CENG-T013-P004")
        # active should still be empty
        self.assertIsNone(self.store.get_packet("CENG-T013-P004"))


class FileStoreExtendedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / ".contract-engineering"
        self.store: RecordStore = FileStore(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_put_then_get_handoff(self) -> None:
        self.store.put_handoff(
            "CENG-T013-P004-HO001",
            {"handoff_id": "CENG-T013-P004-HO001", "packet_id": "CENG-T013-P004"},
        )
        result = self.store.get_handoff("CENG-T013-P004-HO001")
        assert result is not None
        self.assertEqual(result["handoff_id"], "CENG-T013-P004-HO001")

    def test_get_handoff_returns_none_when_missing(self) -> None:
        self.assertIsNone(self.store.get_handoff("NOPE"))

    def test_list_handoffs_empty_when_no_dir(self) -> None:
        self.assertEqual(self.store.list_handoffs(), {})

    def test_put_then_get_lease(self) -> None:
        self.store.put_lease("CENG-T013-P004", {"packet_id": "CENG-T013-P004"})
        self.assertIsNotNone(self.store.get_lease("CENG-T013-P004"))

    def test_get_lease_returns_none_when_missing(self) -> None:
        self.assertIsNone(self.store.get_lease("NOPE"))

    def test_evidence_exists_after_put(self) -> None:
        self.store.put_evidence("CENG-T013-P004-EV001", "# evidence\npass\n")
        self.assertTrue(self.store.evidence_exists("CENG-T013-P004-EV001"))
        self.assertEqual(self.store.get_evidence("CENG-T013-P004-EV001"), "# evidence\npass\n")

    def test_evidence_not_exists_when_missing(self) -> None:
        self.assertFalse(self.store.evidence_exists("NOPE"))

    def test_get_evidence_returns_none_when_missing(self) -> None:
        self.assertIsNone(self.store.get_evidence("NOPE"))

    def test_move_tracker_row_from_active_to_archive(self) -> None:
        index = {
            "tracker_schema_version": 1,
            "partition": "active",
            "max_rows": 25,
            "rows": [
                {
                    "task_id": "CENG-T015",
                    "packet_id": "CENG-T015-P006",
                    "state": "Complete",
                    "owner": "droid",
                    "reviewer": "user",
                    "locks": [],
                    "next_action": "archive",
                    "updated_at": "2026-01-01",
                }
            ],
            "shards": [],
        }
        self.store.put_tracker_index(index)
        archive = {
            "tracker_schema_version": 1,
            "partition": "archive",
            "max_rows": 50,
            "rows": [],
            "shards": [],
        }
        self.store.put_tracker_index(archive, partition="archive")
        self.store.put_packet(
            "CENG-T015-P006", {"packet_id": "CENG-T015-P006", "state": "Complete"}
        )
        self.store.move_tracker_row("CENG-T015-P006", "active", "archive")
        active_rows = self.store.get_tracker_rows("active")
        archive_rows = self.store.get_tracker_rows("archive")
        self.assertEqual(len(active_rows), 0)
        self.assertEqual(archive_rows[0]["packet_id"], "CENG-T015-P006")

    def test_move_tracker_row_from_shard_to_archive(self) -> None:
        shard_doc = {
            "tracker_schema_version": 1,
            "partition": "active",
            "task_id": "CENG-T015",
            "rows": [
                {
                    "task_id": "CENG-T015",
                    "packet_id": "CENG-T015-P007",
                    "state": "Complete",
                    "owner": "droid",
                    "reviewer": "user",
                    "locks": [],
                    "next_action": "archive",
                    "updated_at": "2026-01-01",
                }
            ],
        }
        self.store.put_shard("shards/CENG-T015.yaml", shard_doc)
        index = {
            "tracker_schema_version": 1,
            "partition": "active",
            "max_rows": 25,
            "rows": [],
            "shards": ["shards/CENG-T015.yaml"],
        }
        self.store.put_tracker_index(index)
        archive = {
            "tracker_schema_version": 1,
            "partition": "archive",
            "max_rows": 50,
            "rows": [],
            "shards": [],
        }
        self.store.put_tracker_index(archive, partition="archive")
        self.store.move_tracker_row("CENG-T015-P007", "active", "archive")
        active_rows = self.store.get_tracker_rows("active")
        archive_rows = self.store.get_tracker_rows("archive")
        self.assertEqual(len(active_rows), 0)
        self.assertEqual(archive_rows[0]["packet_id"], "CENG-T015-P007")

    def test_move_tracker_row_raises_when_not_found(self) -> None:
        index = {
            "tracker_schema_version": 1,
            "partition": "active",
            "max_rows": 25,
            "rows": [],
            "shards": [],
        }
        self.store.put_tracker_index(index)
        with self.assertRaises(RecordStoreError):
            self.store.move_tracker_row("NOPE", "active", "archive")

    def test_export_import_round_trip(self) -> None:
        self.store.put_packet(
            "CENG-T013-P004", {"packet_id": "CENG-T013-P004", "revision": 0}
        )
        self.store.put_handoff(
            "CENG-T013-P004-HO001", {"handoff_id": "CENG-T013-P004-HO001"}
        )
        self.store.put_evidence("CENG-T013-P004-EV001", "# pass\n")
        self.store.append_event(
            "CENG-T013",
            {
                "event_id": "CENG-T013-E001",
                "packet_id": "CENG-T013-P004",
                "type": "transition",
                "actor": "worker",
                "occurred_at": "2026-01-01T00:00:00Z",
                "summary": "test",
            },
        )
        snapshot = self.store.export_snapshot()

        tmp2 = tempfile.TemporaryDirectory()
        try:
            root2 = Path(tmp2.name) / ".contract-engineering"
            store2 = FileStore(root2)
            store2.import_snapshot(snapshot)
            self.assertIsNotNone(store2.get_packet("CENG-T013-P004"))
            self.assertIsNotNone(store2.get_handoff("CENG-T013-P004-HO001"))
            self.assertTrue(store2.evidence_exists("CENG-T013-P004-EV001"))
            self.assertEqual(len(store2.list_events("CENG-T013")), 1)
        finally:
            tmp2.cleanup()

    def test_export_snapshot_includes_all_sections(self) -> None:
        snapshot = self.store.export_snapshot()
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
            self.assertIn(section, snapshot)

    def test_list_shard_paths_from_index(self) -> None:
        index = {
            "tracker_schema_version": 1,
            "partition": "active",
            "max_rows": 25,
            "rows": [],
            "shards": ["shards/CENG-T015.yaml", "shards/CENG-T019.yaml"],
        }
        self.store.put_tracker_index(index)
        self.assertEqual(
            self.store.list_shard_paths(),
            ["shards/CENG-T015.yaml", "shards/CENG-T019.yaml"],
        )

    def test_get_shard_returns_empty_rows_when_missing(self) -> None:
        result = self.store.get_shard("shards/NOPE.yaml")
        self.assertEqual(result.get("rows", []), [])


class FileStoreConformanceTests(unittest.TestCase):
    """Conformance suite that any RecordStore backend must pass.

    A new backend runs this class by subclassing it and overriding
    ``store_factory`` in ``setUp``.
    """

    store_factory: Callable[[], RecordStore]

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name) / ".contract-engineering"
        self.store_factory = lambda: FileStore(root)
        self.store = self.store_factory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_put_get_packet_round_trip(self) -> None:
        self.store.put_packet("CENG-T001-P001", {"packet_id": "CENG-T001-P001", "revision": 0})
        result = self.store.get_packet("CENG-T001-P001")
        assert result is not None
        self.assertEqual(result["packet_id"], "CENG-T001-P001")

    def test_stale_revision_rejected(self) -> None:
        self.store.put_packet("CENG-T001-P001", {"packet_id": "CENG-T001-P001", "revision": 0})
        with self.assertRaises(RecordStoreError):
            self.store.put_packet(
                "CENG-T001-P001",
                {"packet_id": "CENG-T001-P001", "revision": 0},
                expected_revision=99,
            )

    def test_event_append_only(self) -> None:
        event = {
            "event_id": "CENG-T001-E001",
            "packet_id": "CENG-T001-P001",
            "type": "transition",
            "actor": "worker",
            "occurred_at": "2026-01-01T00:00:00Z",
            "summary": "test",
        }
        self.store.append_event("CENG-T001", event)
        self.store.append_event("CENG-T001", event)
        self.assertEqual(len(self.store.list_events("CENG-T001")), 1)

    def test_move_tracker_row_atomic(self) -> None:
        index = {
            "tracker_schema_version": 1,
            "partition": "active",
            "max_rows": 25,
            "rows": [
                {"task_id": "T", "packet_id": "CENG-T001-P001", "state": "Complete",
                 "owner": "droid", "reviewer": "user", "locks": [],
                 "next_action": "", "updated_at": "2026-01-01"}
            ],
            "shards": [],
        }
        self.store.put_tracker_index(index)
        archive = {"tracker_schema_version": 1, "partition": "archive",
                   "max_rows": 50, "rows": [], "shards": []}
        self.store.put_tracker_index(archive, partition="archive")
        self.store.move_tracker_row("CENG-T001-P001", "active", "archive")
        self.assertEqual(len(self.store.get_tracker_rows("active")), 0)
        self.assertEqual(len(self.store.get_tracker_rows("archive")), 1)

    def test_export_import_round_trip(self) -> None:
        self.store.put_packet("CENG-T001-P001", {"packet_id": "CENG-T001-P001", "revision": 0})
        snapshot = self.store.export_snapshot()
        tmp2 = tempfile.TemporaryDirectory()
        try:
            store2 = FileStore(Path(tmp2.name) / ".contract-engineering")
            store2.import_snapshot(snapshot)
            assert store2.get_packet("CENG-T001-P001") is not None
        finally:
            tmp2.cleanup()

    def test_missing_directory_safety(self) -> None:
        self.assertIsNone(self.store.get_packet("NOPE"))
        self.assertIsNone(self.store.get_handoff("NOPE"))
        self.assertIsNone(self.store.get_lease("NOPE"))
        self.assertIsNone(self.store.get_evidence("NOPE"))
        self.assertEqual(self.store.get_tracker_rows(), [])
        self.assertEqual(self.store.list_events("NOPE"), [])
        self.assertEqual(self.store.list_packets(), {})


class ResolveRecordStoreTests(unittest.TestCase):
    def test_file_backend_from_lock(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        try:
            project_dir = Path(tmp.name)
            protocol_root = project_dir / ".contract-engineering"
            protocol_root.mkdir()
            lock = {
                "project": {
                    "protocol_root": ".contract-engineering",
                    "record_store": {"backend": "file"},
                }
            }
            store = resolve_record_store(lock, project_dir)
            self.assertIsInstance(store, FileStore)
            self.assertEqual(store.root, protocol_root)
        finally:
            tmp.cleanup()

    def test_defaults_to_file_when_record_store_absent(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        try:
            project_dir = Path(tmp.name)
            protocol_root = project_dir / ".contract-engineering"
            protocol_root.mkdir()
            lock = {"project": {"protocol_root": ".contract-engineering"}}
            store = resolve_record_store(lock, project_dir)
            self.assertIsInstance(store, FileStore)
        finally:
            tmp.cleanup()

    def test_unsupported_backend_raises(self) -> None:
        lock = {"project": {"record_store": {"backend": "api"}}}
        with self.assertRaises(RecordStoreError):
            resolve_record_store(lock, Path("."))

    def test_absolute_protocol_root_preserved(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        try:
            abs_root = Path(tmp.name) / "ce"
            abs_root.mkdir()
            lock = {"project": {"protocol_root": str(abs_root)}}
            store = resolve_record_store(lock, Path("."))
            self.assertEqual(store.root, abs_root)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(unittest.main())
