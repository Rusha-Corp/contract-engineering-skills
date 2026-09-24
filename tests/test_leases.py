import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from scripts.packet_leases import LeaseError, LeaseManager


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / ".contract-engineering"
        (self.root / "leases").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_claim_creates_expiring_fenced_lease(self):
        now = datetime(2026, 9, 24, tzinfo=timezone.utc)
        lease = LeaseManager(self.root).claim(
            "CENG-T015-P004", "worker", ttl_seconds=60, now=now
        )
        self.assertEqual(lease["release"]["status"], "active")
        self.assertEqual(lease["fencing_token"], "epoch:1")
        self.assertEqual(lease["expires_at"], "2026-09-24T00:01:00+00:00")
        stored = yaml.safe_load(
            (self.root / "leases/CENG-T015-P004.yaml").read_text()
        )
        self.assertNotIn("fencing_token", stored)
        self.assertEqual(stored["fencing_epoch"], 1)

    def test_expired_lease_is_rejected(self):
        now = datetime(2026, 9, 24, tzinfo=timezone.utc)
        manager = LeaseManager(self.root)
        lease = manager.claim("CENG-T015-P004", "worker", ttl_seconds=60, now=now)
        expired = now + timedelta(seconds=61)
        with self.assertRaises(LeaseError) as context:
            manager.validate("CENG-T015-P004", lease["fencing_token"], now=expired)
        self.assertIn("expired", str(context.exception))

    def test_old_fencing_token_is_rejected_after_takeover(self):
        now = datetime(2026, 9, 24, tzinfo=timezone.utc)
        manager = LeaseManager(self.root)
        first = manager.claim("CENG-T015-P004", "worker", ttl_seconds=60, now=now)
        second = manager.claim(
            "CENG-T015-P004",
            "new-worker",
            ttl_seconds=60,
            now=now + timedelta(seconds=61),
        )
        self.assertEqual(first["fencing_token"], "epoch:1")
        self.assertEqual(second["fencing_token"], "epoch:2")
        with self.assertRaises(LeaseError):
            manager.validate(
                "CENG-T015-P004",
                first["fencing_token"],
                now=now + timedelta(seconds=62),
            )


if __name__ == "__main__":
    unittest.main()
