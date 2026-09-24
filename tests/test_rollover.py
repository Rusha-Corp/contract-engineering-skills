import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.tracker_rollover import RolloverError, apply_rollover


def write_yaml(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def packet(packet_id, state="Complete"):
    return {"packet_id": packet_id, "task_id": "CENG-T015", "state": state}


def row(packet_id, state="Complete"):
    return {
        "task_id": "CENG-T015",
        "packet_id": packet_id,
        "state": state,
        "owner": "droid",
        "reviewer": "user",
        "locks": [],
        "next_action": "Retain in archive at iteration closure",
        "updated_at": "2026-09-24",
    }


class TrackerRolloverTests(unittest.TestCase):
    def make_root(self, rows, shards=None):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name) / ".contract-engineering"
        write_yaml(
            root / "tracker/index.yaml",
            {
                "tracker_schema_version": 1,
                "partition": "active",
                "max_rows": 25,
                "shards": shards or [],
                "rows": rows,
            },
        )
        write_yaml(
            root / "tracker/archive/index.yaml",
            {
                "tracker_schema_version": 1,
                "partition": "archive",
                "max_rows": 50,
                "rows": [],
            },
        )
        return directory, root

    def test_dry_run_is_non_mutating_and_lists_moves(self):
        directory, root = self.make_root([row("CENG-T015-P006")])
        try:
            packet_path = root / "work-packets/CENG-T015-P006.yaml"
            write_yaml(packet_path, packet("CENG-T015-P006"))
            before = packet_path.read_bytes()
            result = apply_rollover(root)
            self.assertEqual(result["moves"][0]["packet_id"], "CENG-T015-P006")
            self.assertEqual(packet_path.read_bytes(), before)
            self.assertTrue(packet_path.exists())
            self.assertFalse(
                (root / "archive/work-packets/CENG-T015-P006.yaml").exists()
            )
        finally:
            directory.cleanup()

    def test_confirmed_rollover_moves_packet_and_row_to_archive(self):
        directory, root = self.make_root([row("CENG-T015-P006")])
        try:
            write_yaml(
                root / "work-packets/CENG-T015-P006.yaml",
                packet("CENG-T015-P006"),
            )
            result = apply_rollover(root, confirm=True)
            self.assertEqual(result["moved"], ["CENG-T015-P006"])
            self.assertFalse((root / "work-packets/CENG-T015-P006.yaml").exists())
            self.assertTrue(
                (root / "archive/work-packets/CENG-T015-P006.yaml").exists()
            )
            active = yaml.safe_load((root / "tracker/index.yaml").read_text())
            archive = yaml.safe_load(
                (root / "tracker/archive/index.yaml").read_text()
            )
            self.assertEqual(active["rows"], [])
            self.assertEqual(archive["rows"][0]["packet_id"], "CENG-T015-P006")
        finally:
            directory.cleanup()

    def test_confirmed_rollover_handles_terminal_shard_rows(self):
        directory, root = self.make_root(
            [], shards=["tracker/shards/CENG-T015.yaml"]
        )
        try:
            write_yaml(
                root / "tracker/shards/CENG-T015.yaml",
                {
                    "tracker_schema_version": 1,
                    "partition": "active",
                    "task_id": "CENG-T015",
                    "max_rows": 50,
                    "rows": [row("CENG-T015-P006")],
                },
            )
            write_yaml(
                root / "work-packets/CENG-T015-P006.yaml",
                packet("CENG-T015-P006"),
            )
            apply_rollover(root, confirm=True)
            shard = yaml.safe_load(
                (root / "tracker/shards/CENG-T015.yaml").read_text()
            )
            self.assertEqual(shard["rows"], [])
        finally:
            directory.cleanup()

    def test_terminal_row_with_active_packet_blocks_without_mutation(self):
        directory, root = self.make_root([row("CENG-T015-P006", "Complete")])
        try:
            packet_path = root / "work-packets/CENG-T015-P006.yaml"
            write_yaml(packet_path, packet("CENG-T015-P006", "Implementing"))
            before = packet_path.read_bytes()
            with self.assertRaises(RolloverError):
                apply_rollover(root, confirm=True)
            self.assertEqual(packet_path.read_bytes(), before)
        finally:
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
