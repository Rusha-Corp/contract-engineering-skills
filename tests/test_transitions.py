import json
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.contract_engineering import TransitionError, TransitionStore


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / ".contract-engineering"
        (self.root / "work-packets").mkdir(parents=True)
        (self.root / "tracker").mkdir()
        packet = {
            "packet_id": "CENG-T013-P004", "task_id": "CENG-T013",
            "state": "Implementing", "owner": "worker", "reviewer": "user",
            "locks": ["lease"], "scope": {"in": ["scripts"], "out": []},
            "revision": 0,
        }
        (self.root / "work-packets/CENG-T013-P004.yaml").write_text(
            yaml.safe_dump(packet), encoding="utf-8"
        )
        index = {"tracker_schema_version": 1, "partition": "active",
                 "max_rows": 25, "rows": [{
                     "task_id": "CENG-T013", "packet_id": "CENG-T013-P004",
                     "state": "Implementing", "owner": "worker", "reviewer": "user",
                     "locks": ["lease"], "next_action": "work",
                     "updated_at": "2026-09-16"}], "shards": []}
        (self.root / "tracker/index.yaml").write_text(
            yaml.safe_dump(index), encoding="utf-8"
        )
        (self.root / "tracker/events").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_transition_and_replay_are_idempotent(self):
        store = TransitionStore(self.root)
        result = store.transition(
            "CENG-T013-P004", "Validation", "worker", "ready", expected_revision=0
        )
        self.assertEqual(result["state"], "Validation")
        self.assertEqual(result["revision"], 1)
        journal = next((self.root / "journal").glob("*.json"))
        data = json.loads(journal.read_text())
        self.assertEqual(data["status"], "committed")
        self.assertEqual(store.recover(), [])
        self.assertEqual(
            store.transition(
                "CENG-T013-P004", "Validation", "worker", "retry",
                expected_revision=1,
            )["state"],
            "Validation",
        )

    def test_transition_updates_tracker_and_event_projection(self):
        store = TransitionStore(self.root)
        store.transition(
            "CENG-T013-P004",
            "Validation",
            "worker",
            "ready",
            expected_revision=0,
        )
        tracker = yaml.safe_load(
            (self.root / "tracker/index.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(tracker["rows"][0]["state"], "Validation")
        events = yaml.safe_load(
            (self.root / "tracker/events/CENG-T013.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(events["events"][-1]["type"], "transition")
        self.assertEqual(events["events"][-1]["packet_id"], "CENG-T013-P004")

    def test_stale_revision_is_rejected(self):
        store = TransitionStore(self.root)
        store.transition(
            "CENG-T013-P004",
            "Validation",
            "worker",
            "ready",
            expected_revision=0,
        )
        with self.assertRaises(TransitionError) as context:
            store.transition(
                "CENG-T013-P004",
                "Rework",
                "worker",
                "stale retry",
                expected_revision=0,
            )
        self.assertIn("revision", str(context.exception))

    def test_planned_packet_can_be_claimed(self):
        packet_path = self.root / "work-packets/CENG-T013-P004.yaml"
        packet = yaml.safe_load(packet_path.read_text(encoding="utf-8"))
        packet["state"] = "Planned"
        packet_path.write_text(yaml.safe_dump(packet), encoding="utf-8")
        store = TransitionStore(self.root)
        result = store.transition(
            "CENG-T013-P004",
            "Claimed",
            "worker",
            "claim",
            expected_revision=0,
        )
        self.assertEqual(result["state"], "Claimed")

    def test_illegal_completion_explains_gate(self):
        store = TransitionStore(self.root)
        with self.assertRaises(TransitionError):
            store.transition("CENG-T013-P004", "Complete", "worker", "skip")
        explanation = store.explain_block("CENG-T013-P004", "Complete")
        self.assertIn("handoff", " ".join(explanation["failures"]))

    def test_reassign_requires_expired_or_released_lease(self):
        store = TransitionStore(self.root)
        with self.assertRaises(TransitionError):
            store.reassign("CENG-T013-P004", "other", "takeover", actor="worker")
        result = store.reassign("CENG-T013-P004", "other", "takeover", actor="worker", force=True)
        self.assertEqual(result["owner"], "other")
        self.assertTrue(result["fencing_token"])

    def test_doctor_is_read_only(self):
        store = TransitionStore(self.root)
        self.assertFalse((self.root / "journal").exists())
        report = store.doctor()
        self.assertEqual(report["inconsistencies"], [])
        self.assertFalse((self.root / "journal").exists())

    def test_crash_recovery_completes_transition(self):
        """Simulate a crash after journal write but before packet update."""
        store = TransitionStore(self.root)
        # Manually create a prepared journal entry (crash simulation)
        store.journal.mkdir(parents=True)
        operation = {"kind": "transition", "packet_id": "CENG-T013-P004",
                     "source": "Implementing", "destination": "Validation",
                     "actor": "worker", "reason": "crash test", "status": "prepared",
                     "expected_revision": 0}
        journal_path = store.journal / "crash-transition.json"
        journal_path.write_text(json.dumps(operation), encoding="utf-8")
        # Packet state should still be Implementing
        packet = store._load("CENG-T013-P004")
        self.assertEqual(packet["state"], "Implementing")
        # Recover
        recovered = store.recover()
        self.assertEqual(len(recovered), 1)
        # Packet should now be Validation
        packet = store._load("CENG-T013-P004")
        self.assertEqual(packet["state"], "Validation")
        # Journal should be committed
        record = json.loads(journal_path.read_text())
        self.assertEqual(record["status"], "committed")

    def test_crash_recovery_completes_reassignment(self):
        """Simulate a crash after reassign journal write but before packet update."""
        store = TransitionStore(self.root)
        store.journal.mkdir(parents=True)
        operation = {"kind": "reassign", "packet_id": "CENG-T013-P004",
                     "owner": "new-worker", "actor": "worker", "reason": "takeover",
                     "fencing_token": "abc123", "status": "prepared"}
        journal_path = store.journal / "crash-reassign.json"
        journal_path.write_text(json.dumps(operation), encoding="utf-8")
        # Owner should still be original
        packet = store._load("CENG-T013-P004")
        self.assertEqual(packet["owner"], "worker")
        # Recover
        recovered = store.recover()
        self.assertEqual(len(recovered), 1)
        # Owner should now be new-worker
        packet = store._load("CENG-T013-P004")
        self.assertEqual(packet["owner"], "new-worker")
        self.assertEqual(packet["fencing_token"], "abc123")

    def test_recovery_is_idempotent_after_replay(self):
        """Calling recover() multiple times must not duplicate or lose state."""
        store = TransitionStore(self.root)
        store.journal.mkdir(parents=True)
        # Create a prepared transition journal entry
        operation = {"kind": "transition", "packet_id": "CENG-T013-P004",
                     "source": "Implementing", "destination": "Validation",
                     "actor": "worker", "reason": "idempotent test", "status": "prepared",
                     "expected_revision": 0}
        journal_path = store.journal / "idempotent-test.json"
        journal_path.write_text(json.dumps(operation), encoding="utf-8")
        # First recovery
        store.recover()
        self.assertEqual(store._load("CENG-T013-P004")["state"], "Validation")
        # Second recovery should be a no-op
        second = store.recover()
        self.assertEqual(second, [])
        # State unchanged
        self.assertEqual(store._load("CENG-T013-P004")["state"], "Validation")


if __name__ == "__main__":
    unittest.main()
