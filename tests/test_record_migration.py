import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import migrate_records


class RecordMigrationTests(unittest.TestCase):
    def test_dry_run_reports_legacy_packet_without_mutating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".contract-engineering"
            packets = root / "work-packets"
            packets.mkdir(parents=True)
            packet_path = packets / "TEST-T015-P002.yaml"
            original = {
                "packet_id": "TEST-T015-P002",
                "task_id": "TEST-T015",
                "state": "Planned",
                "acceptance_criteria": ["The packet remains valid"],
            }
            packet_path.write_text(yaml.safe_dump(original), encoding="utf-8")

            plan = migrate_records.plan(root)

            self.assertEqual(plan[0]["packet_id"], "TEST-T015-P002")
            self.assertIn("work_type", plan[0]["changes"])
            self.assertEqual(yaml.safe_load(packet_path.read_text()), original)

    def test_apply_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".contract-engineering"
            packets = root / "work-packets"
            packets.mkdir(parents=True)
            packet_path = packets / "TEST-T015-P002.yaml"
            packet_path.write_text(
                yaml.safe_dump(
                    {
                        "packet_id": "TEST-T015-P002",
                        "task_id": "TEST-T015",
                        "state": "Planned",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(migrate_records.MigrationError):
                migrate_records.apply(root, confirm=False)


if __name__ == "__main__":
    unittest.main()
