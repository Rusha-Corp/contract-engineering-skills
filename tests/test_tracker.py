import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate-tracker.py"
SPEC = importlib.util.spec_from_file_location("validate_tracker", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
RENDER_SCRIPT = Path(__file__).parents[1] / "scripts" / "render-tracker.py"
RENDER_SPEC = importlib.util.spec_from_file_location("render_tracker", RENDER_SCRIPT)
assert RENDER_SPEC and RENDER_SPEC.loader
renderer = importlib.util.module_from_spec(RENDER_SPEC)
RENDER_SPEC.loader.exec_module(renderer)


def row(packet_id="TEST-T001-P001", state="Implementing", task_id="TEST-T001"):
    return {
        "task_id": task_id,
        "packet_id": packet_id,
        "state": state,
        "owner": "agent",
        "reviewer": "user",
        "locks": [],
        "next_action": "continue",
        "updated_at": "2026-09-03",
    }


class TrackerValidationTests(unittest.TestCase):
    def test_rejects_wrong_task_owner(self):
        with self.assertRaises(SystemExit):
            validator.validate_row(row(packet_id="TEST-T002-P001"), Path("index.yaml"), "active")

    def test_rejects_non_terminal_archive_row(self):
        with self.assertRaises(SystemExit):
            validator.validate_row(row(state="Validation"), Path("archive.yaml"), "archive")

    def test_rejects_duplicate_partition_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tracker").mkdir()
            (root / "tracker" / "index.yaml").write_text(
                "tracker_schema_version: 1\npartition: active\nmax_rows: 25\nrows:\n"
                "  - task_id: TEST-T001\n    packet_id: TEST-T001-P001\n"
                "    state: Implementing\n    owner: agent\n    reviewer: user\n"
                "    locks: []\n    next_action: continue\n    updated_at: today\n"
                "  - task_id: TEST-T001\n    packet_id: TEST-T001-P001\n"
                "    state: Implementing\n    owner: agent\n    reviewer: user\n"
                "    locks: []\n    next_action: continue\n    updated_at: today\n"
            )
            with self.assertRaises(SystemExit):
                validator.partition_rows(root, "tracker/index.yaml", "active")

    def test_rejects_index_over_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tracker").mkdir()
            rows = "\n".join(
                "  - task_id: TEST-T001\n"
                f"    packet_id: TEST-T001-P{i:03d}\n"
                "    state: Implementing\n    owner: agent\n    reviewer: user\n"
                "    locks: []\n    next_action: continue\n    updated_at: today"
                for i in range(1, 27)
            )
            (root / "tracker" / "index.yaml").write_text(
                "tracker_schema_version: 1\npartition: active\nmax_rows: 25\nrows:\n"
                + rows
                + "\n"
            )
            with self.assertRaises(SystemExit):
                validator.partition_rows(root, "tracker/index.yaml", "active")

    def test_accepts_declared_task_shard(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tracker" / "shards").mkdir(parents=True)
            (root / "tracker" / "index.yaml").write_text(
                "tracker_schema_version: 1\npartition: active\nmax_rows: 25\n"
                "shards:\n  - tracker/shards/TEST-T001.yaml\nrows: []\n"
            )
            (root / "tracker" / "shards" / "TEST-T001.yaml").write_text(
                "tracker_schema_version: 1\npartition: active\nmax_rows: 50\n"
                "task_id: TEST-T001\nrows:\n"
                "  - task_id: TEST-T001\n    packet_id: TEST-T001-P001\n"
                "    state: Implementing\n    owner: agent\n    reviewer: user\n"
                "    locks: []\n    next_action: continue\n    updated_at: today\n"
            )
            rows, files = validator.partition_rows(
                root, "tracker/index.yaml", "active"
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(files), 2)

    def test_rejects_shard_row_for_another_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tracker" / "shards").mkdir(parents=True)
            (root / "tracker" / "index.yaml").write_text(
                "tracker_schema_version: 1\npartition: active\nmax_rows: 25\n"
                "shards:\n  - tracker/shards/TEST-T001.yaml\nrows: []\n"
            )
            (root / "tracker" / "shards" / "TEST-T001.yaml").write_text(
                "tracker_schema_version: 1\npartition: active\nmax_rows: 50\n"
                "task_id: TEST-T001\nrows:\n"
                "  - task_id: TEST-T002\n    packet_id: TEST-T002-P001\n"
                "    state: Implementing\n    owner: agent\n    reviewer: user\n"
                "    locks: []\n    next_action: continue\n    updated_at: today\n"
            )
            with self.assertRaises(SystemExit):
                validator.partition_rows(root, "tracker/index.yaml", "active")

    def test_renderer_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tracker" / "archive").mkdir(parents=True)
            (root / "tracker" / "index.yaml").write_text(
                "tracker_schema_version: 1\npartition: active\nmax_rows: 25\n"
                "rows: []\n"
            )
            (root / "tracker" / "archive" / "index.yaml").write_text(
                "tracker_schema_version: 1\npartition: archive\nmax_rows: 50\n"
                "rows: []\n"
            )
            renderer.render_projections(root)
            (root / "execution-tracker.md").write_text("stale\n")
            with self.assertRaises(SystemExit):
                renderer.render_projections(root, check=True)

    def test_validate_checks_packet_lock_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tracker" / "archive").mkdir(parents=True)
            (root / "work-packets").mkdir()
            (root / "archive" / "work-packets").mkdir(parents=True)
            (root / "tracker" / "index.yaml").write_text(
                "tracker_schema_version: 1\npartition: active\nmax_rows: 25\nrows:\n"
                "  - task_id: TEST-T001\n    packet_id: TEST-T001-P001\n"
                "    state: Implementing\n    owner: agent\n    reviewer: user\n"
                "    locks: [tracker/]\n    next_action: continue\n    updated_at: today\n"
            )
            (root / "tracker" / "archive" / "index.yaml").write_text(
                "tracker_schema_version: 1\npartition: archive\nmax_rows: 50\nrows: []\n"
            )
            (root / "work-packets" / "TEST-T001-P001.yaml").write_text(
                "packet_id: TEST-T001-P001\nstate: Implementing\nowner: agent\n"
                "reviewer: user\nlocks: [tracker/]\n"
            )
            validator.validate(root)

    def test_rejects_event_for_unknown_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tracker" / "events").mkdir(parents=True)
            (root / "tracker" / "events" / "TEST-T001.yaml").write_text(
                "task_id: TEST-T001\nschema_version: 1\nevents:\n"
                "  - event_id: TEST-T001-E001\n    packet_id: TEST-T001-P001\n"
                "    type: claimed\n    actor: agent\n"
                "    occurred_at: 2026-09-03T00:00:00Z\n    summary: claimed\n"
            )
            with self.assertRaises(SystemExit):
                validator.validate_events(root, set())

    def test_validates_repository_tracker_partitions(self):
        root = Path(__file__).parents[1] / ".contract-engineering"
        validator.validate(root)


if __name__ == "__main__":
    unittest.main()
