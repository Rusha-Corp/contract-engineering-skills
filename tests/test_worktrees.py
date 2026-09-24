import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.reconcile_worktrees import parse_worktrees, reconcile_records


WORKTREES = """\
worktree /repo
HEAD abcdef0123456789abcdef0123456789abcdef01
branch refs/heads/main

worktree /repo-CENG-T015-P005
HEAD 1234567890123456789012345678901234567890
branch refs/heads/agent/CENG-T015-P005

worktree /repo-orphan
HEAD 9999999999999999999999999999999999999999
branch refs/heads/agent/CENG-T999-P001
"""


class WorktreeReconciliationTests(unittest.TestCase):
    def test_parser_returns_deterministic_records(self):
        records = parse_worktrees(WORKTREES)
        self.assertEqual(records[1]["packet_id"], "CENG-T015-P005")
        self.assertEqual(records[2]["packet_id"], "CENG-T999-P001")

    def test_reconcile_reports_registered_unregistered_and_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".contract-engineering"
            packets = root / "work-packets"
            packets.mkdir(parents=True)
            packet = {
                "packet_id": "CENG-T015-P005",
                "worktree": {
                    "path": "/repo-CENG-T015-P005",
                    "branch": "agent/CENG-T015-P005",
                    "base_revision": "1234567890123456789012345678901234567890",
                    "cleanup_status": "active",
                },
            }
            (packets / "CENG-T015-P005.yaml").write_text(
                yaml.safe_dump(packet), encoding="utf-8"
            )
            report = reconcile_records(root, WORKTREES)
            self.assertEqual(report["registered"][0]["packet_id"], "CENG-T015-P005")
            self.assertEqual(report["unregistered"][0]["packet_id"], "CENG-T999-P001")
            self.assertEqual(report["missing"], [])

    def test_reconcile_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".contract-engineering"
            (root / "work-packets").mkdir(parents=True)
            path = root / "work-packets/CENG-T015-P005.yaml"
            path.write_text("packet_id: CENG-T015-P005\n", encoding="utf-8")
            before = path.read_bytes()
            reconcile_records(root, WORKTREES)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
