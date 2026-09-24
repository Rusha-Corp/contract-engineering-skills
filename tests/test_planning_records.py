import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate-contract-records.py"
SPEC = importlib.util.spec_from_file_location("validate_contract_records_planning", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class PlanningRecordTests(unittest.TestCase):
    def _root(self):
        project = Path(tempfile.mkdtemp())
        root = project / ".contract-engineering"
        (root / "epics").mkdir(parents=True)
        (root / "tasks").mkdir()
        shutil.copytree(Path(__file__).parents[1] / "schemas", project / "schemas")
        return project, root

    def _epic(self):
        return {
            "epic_id": "CENG-E015",
            "title": "Acceptance-first delivery",
            "objective": "Ship small verified slices quickly",
            "priority": "high",
            "status": "active",
            "success_measures": ["Every shipped packet has criterion evidence"],
            "non_goals": ["Automating product prioritization"],
            "task_refs": ["CENG-T015"],
        }

    def _task(self):
        return {
            "task_id": "CENG-T015",
            "epic_id": "CENG-E015",
            "title": "Implement acceptance-first workflow",
            "objective": "Make acceptance criteria the completion contract",
            "priority": "high",
            "status": "in_progress",
            "dependencies": [],
            "packet_refs": ["CENG-T015-P001"],
            "open_questions": [],
        }

    def test_valid_epic_and_task_records_pass(self):
        project, root = self._root()
        (root / "epics/CENG-E015.yaml").write_text(
            yaml.safe_dump(self._epic()), encoding="utf-8"
        )
        (root / "tasks/CENG-T015.yaml").write_text(
            yaml.safe_dump(self._task()), encoding="utf-8"
        )
        validator.validate_planning_records(
            root,
            {"CENG-T015-P001": {"packet_id": "CENG-T015-P001"}},
        )

    def test_invalid_priority_is_rejected(self):
        project, root = self._root()
        epic = self._epic()
        epic["priority"] = "urgent"
        (root / "epics/CENG-E015.yaml").write_text(
            yaml.safe_dump(epic), encoding="utf-8"
        )
        with self.assertRaises(ValueError) as context:
            validator.validate_planning_records(root, {})
        self.assertIn("priority", str(context.exception))


if __name__ == "__main__":
    unittest.main()
