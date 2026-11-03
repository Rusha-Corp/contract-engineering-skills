"""Conformance and unit tests for the RecordStore interface and FileStore backend."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

from scripts.record_store import FileStore, RecordStore, RecordStoreError


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


if __name__ == "__main__":
    raise SystemExit(unittest.main())
