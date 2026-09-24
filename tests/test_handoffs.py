import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.contract_engineering import TransitionError, TransitionStore
from scripts.finalize_handoff import scope_digest
from scripts.packet_leases import LeaseManager


class HandoffCompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / ".contract-engineering"
        (self.root / "work-packets").mkdir(parents=True)
        (self.root / "tracker").mkdir()
        (self.root / "handoffs").mkdir()
        (self.root / "evidence").mkdir()
        packet = {
            "packet_id": "CENG-T015-P004",
            "task_id": "CENG-T015",
            "state": "Handoff",
            "owner": "worker",
            "reviewer": "user",
            "locks": [],
            "revision": 1,
            "scope": {"in": ["scripts"], "out": []},
            "handoff_ref": "CENG-T015-P004-HO001",
            "evidence_refs": ["CENG-T015-P004-EV001"],
        }
        self.packet_path = self.root / "work-packets/CENG-T015-P004.yaml"
        self.packet_path.write_text(yaml.safe_dump(packet), encoding="utf-8")
        (self.root / "evidence/CENG-T015-P004-EV001.md").write_text(
            "# CENG-T015-P004-EV001\npass\n", encoding="utf-8"
        )
        index = {
            "tracker_schema_version": 1,
            "partition": "active",
            "max_rows": 25,
            "rows": [
                {
                    "task_id": "CENG-T015",
                    "packet_id": "CENG-T015-P004",
                    "state": "Handoff",
                    "owner": "worker",
                    "reviewer": "user",
                    "locks": [],
                    "next_action": "accept",
                    "updated_at": "2026-09-24",
                }
            ],
            "shards": [],
        }
        (self.root / "tracker/index.yaml").write_text(
            yaml.safe_dump(index), encoding="utf-8"
        )
        (self.root / "tracker/events").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_handoff(self, **overrides):
        handoff = {
            "handoff_id": "CENG-T015-P004-HO001",
            "packet_id": "CENG-T015-P004",
            "receiver_status": "accepted",
            "accepted_revision": 1,
            "accepted_scope_digest": scope_digest(
                yaml.safe_load(self.packet_path.read_text())
            ),
            "accepted_evidence_refs": ["CENG-T015-P004-EV001"],
            "receiver_notes": "accepted",
        }
        handoff.update(overrides)
        (self.root / "handoffs/CENG-T015-P004-HO001.yaml").write_text(
            yaml.safe_dump(handoff), encoding="utf-8"
        )

    def test_matching_accepted_handoff_allows_complete(self):
        self._write_handoff()
        result = TransitionStore(self.root).transition(
            "CENG-T015-P004",
            "Complete",
            "worker",
            "accepted",
            expected_revision=1,
        )
        self.assertEqual(result["state"], "Complete")

    def test_pending_handoff_blocks_complete(self):
        self._write_handoff(receiver_status="pending")
        with self.assertRaises(TransitionError) as context:
            TransitionStore(self.root).transition(
                "CENG-T015-P004",
                "Complete",
                "worker",
                "pending",
                expected_revision=1,
            )
        self.assertIn("handoff", str(context.exception))

    def test_mismatched_handoff_revision_blocks_complete(self):
        self._write_handoff(accepted_revision=0)
        with self.assertRaises(TransitionError) as context:
            TransitionStore(self.root).transition(
                "CENG-T015-P004",
                "Complete",
                "worker",
                "stale",
                expected_revision=1,
            )
        self.assertIn("revision", str(context.exception))

    def test_content_and_packet_revisions_are_distinct_bindings(self):
        self._write_handoff(
            accepted_revision="a" * 40,
            accepted_packet_revision=1,
        )
        result = TransitionStore(self.root).transition(
            "CENG-T015-P004",
            "Complete",
            "worker",
            "accepted content revision",
            expected_revision=1,
        )
        self.assertEqual(result["state"], "Complete")

    def test_high_risk_completion_requires_active_lease(self):
        packet = yaml.safe_load(self.packet_path.read_text())
        packet["risk_tier"] = "high"
        self.packet_path.write_text(yaml.safe_dump(packet), encoding="utf-8")
        self._write_handoff()
        with self.assertRaises(TransitionError) as context:
            TransitionStore(self.root).transition(
                "CENG-T015-P004",
                "Complete",
                "worker",
                "no lease",
                expected_revision=1,
            )
        self.assertIn("lease", str(context.exception))

    def test_high_risk_completion_accepts_current_lease(self):
        packet = yaml.safe_load(self.packet_path.read_text())
        packet["risk_tier"] = "high"
        lease = LeaseManager(self.root).claim(
            "CENG-T015-P004", "worker", ttl_seconds=3600
        )
        packet["lease_ref"] = "CENG-T015-P004"
        packet["locks"] = ["handoff-lease-coordinator:CENG-T015-P004"]
        self.packet_path.write_text(yaml.safe_dump(packet), encoding="utf-8")
        self._write_handoff()
        result = TransitionStore(self.root).transition(
            "CENG-T015-P004",
            "Complete",
            "worker",
            "leased",
            expected_revision=1,
            fencing_token=lease["fencing_token"],
        )
        self.assertEqual(result["state"], "Complete")
        self.assertEqual(result["locks"], [])


if __name__ == "__main__":
    unittest.main()
