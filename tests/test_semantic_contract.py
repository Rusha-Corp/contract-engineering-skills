import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate-contract-records.py"
SPEC = importlib.util.spec_from_file_location("validate_contract_records", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


ROOT = Path(__file__).parents[1]


class SemanticContractIntegrationTests(unittest.TestCase):
    def test_repository_contract_has_evolution_fields(self):
        path = (
            ROOT
            / ".contract-engineering"
            / "semantic-contracts"
            / "CENG-T007-P001-SC001.yaml"
        )
        contract = yaml.safe_load(path.read_text(encoding="utf-8"))
        validator.validate_semantic_contract(path, contract)
        self.assertEqual(contract["maturity"], "emerging")
        self.assertTrue(contract["open_questions"])
        self.assertTrue(contract["change_log"])

    def test_active_semantic_packet_requires_contract(self):
        packet = {
            "packet_id": "TEST-T001-P001",
            "task_id": "TEST-T001",
            "phase": "P0_FOUNDATIONS",
            "domain": "documentation",
            "title": "Test packet",
            "objective": "Test semantic linkage",
            "scope": {"in": ["docs"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "claim_timestamp": "2026-08-30T00:00:00Z",
            "baseline_refs": [
                ".contract-engineering/protocol.lock.yaml",
                "cefd662d05e4e4c0b363cd6c23ba32eb6a805717",
            ],
            "acceptance_criteria": ["Meaning is reviewed"],
            "validation_plan": [{"id": "VAL001", "kind": "semantic", "expected": "pass"}],
            "state": "Implementing",
            "semantic_scope": "affected",
        }
        with self.assertRaises(ValueError):
            validator.validate_packet(
                Path("TEST-T001-P001.yaml"), packet, {}, {}
            )

    def test_nonsemantic_packet_cannot_reference_contract(self):
        packet = {
            "packet_id": "TEST-T001-P001",
            "task_id": "TEST-T001",
            "phase": "P0_FOUNDATIONS",
            "domain": "documentation",
            "title": "Test packet",
            "objective": "Test semantic linkage",
            "scope": {"in": ["docs"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "claim_timestamp": "2026-08-30T00:00:00Z",
            "baseline_refs": [
                ".contract-engineering/protocol.lock.yaml",
                "cefd662d05e4e4c0b363cd6c23ba32eb6a805717",
            ],
            "acceptance_criteria": ["Meaning is reviewed"],
            "validation_plan": [{"id": "VAL001", "kind": "semantic", "expected": "pass"}],
            "state": "Implementing",
            "semantic_scope": "none",
            "semantic_contract_ref": "TEST-SC001",
        }
        with self.assertRaises(ValueError):
            validator.validate_packet(
                Path("TEST-T001-P001.yaml"), packet, {}, {}
            )

    def test_parser_does_not_echo_invalid_contract_content(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            handle.write("contract_id: TEST-SC001\ninvalid: [unclosed\n")
            handle.flush()
            with self.assertRaises(ValueError) as context:
                validator.load_yaml(Path(handle.name))
            self.assertNotIn("unclosed", str(context.exception))


if __name__ == "__main__":
    unittest.main()
