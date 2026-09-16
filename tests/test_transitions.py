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
        result = store.transition("CENG-T013-P004", "Validation", "worker", "ready")
        self.assertEqual(result["state"], "Validation")
        journal = next((self.root / "journal").glob("*.json"))
        data = json.loads(journal.read_text())
        self.assertEqual(data["status"], "committed")
        self.assertEqual(store.recover(), [])
        self.assertEqual(store.transition("CENG-T013-P004", "Validation", "worker", "retry")["state"], "Validation")

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
        report = store.doctor()
        self.assertEqual(report["inconsistencies"], [])


if __name__ == "__main__":
    unittest.main()
