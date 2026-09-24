import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_contract_records", ROOT / "scripts/validate-contract-records.py"
)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

SCOPE_SPEC = importlib.util.spec_from_file_location(
    "packet_scope", ROOT / "scripts/packet_scope.py"
)
assert SCOPE_SPEC and SCOPE_SPEC.loader
scope = importlib.util.module_from_spec(SCOPE_SPEC)
SCOPE_SPEC.loader.exec_module(scope)


class CiValidationTests(unittest.TestCase):
    def test_schema_validation_checks_epic_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            protocol_root = project / ".contract-engineering"
            schemas = project / "schemas"
            shutil.copytree(ROOT / "schemas", schemas)
            epics = protocol_root / "epics"
            epics.mkdir(parents=True)
            (epics / "TEST-E001.yaml").write_text(
                yaml.safe_dump(
                    {
                        "epic_id": "TEST-E001",
                        "title": "Invalid epic",
                        "objective": "Exercise schema validation",
                        "priority": "not-a-priority",
                        "status": "proposed",
                        "success_measures": [],
                        "non_goals": [],
                        "task_refs": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                validator.validate_json_schemas(protocol_root, {})

    def test_workflow_enforces_packet_scope_and_dry_run_migration(self):
        workflow = (
            ROOT / ".github/workflows/protocol-validation.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("--packet", workflow)
        self.assertIn("--changed-path", workflow)
        self.assertIn("packet_changed", workflow)
        self.assertIn("unclaimed", workflow)
        self.assertIn("migrate_records.py --root .contract-engineering", workflow)
        self.assertNotIn("migrate_records.py --apply --confirm", workflow)

    def test_packet_scope_dispatch_claims_only_owned_paths(self):
        packet = ROOT / ".contract-engineering/work-packets/CENG-T016-P007.yaml"
        changed = [
            ".github/workflows/protocol-validation.yml",
            "requirements-ci.txt",
            "tests/test_tracker.py",
        ]
        self.assertEqual(
            scope.claimed_paths(packet, changed),
            changed[:2],
        )
        self.assertEqual(
            scope.unclaimed_paths([packet], changed),
            ["tests/test_tracker.py"],
        )


if __name__ == "__main__":
    unittest.main()
