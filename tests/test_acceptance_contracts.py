import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate-contract-records.py"
SPEC = importlib.util.spec_from_file_location("validate_contract_records_acceptance", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class AcceptanceFirstTests(unittest.TestCase):
    def contract(self, *, evidence_refs=None):
        return {
            "version": 1,
            "criteria": [
                {
                    "id": "TEST-T015-P002-AC001",
                    "statement": "The packet contract is testable",
                    "expected_result": "A deterministic validation result is produced",
                    "verification_method": "execute",
                    "verification_command": "python3 -m unittest",
                    "evidence_refs": [] if evidence_refs is None else evidence_refs,
                    "validation_ref": "TEST-T015-P002-VAL001",
                }
            ],
        }

    def packet(self, *, state="Claimed", evidence_refs=None, open_questions=None):
        return {
            "packet_id": "TEST-T015-P002",
            "task_id": "TEST-T015",
            "state": state,
            "work_type": "discovery",
            "priority": "high",
            "scope": {"in": ["scripts"], "out": []},
            "acceptance_contract": self.contract(evidence_refs=evidence_refs),
            "validation_plan": [
                {
                    "id": "TEST-T015-P002-VAL001",
                    "kind": "tests",
                    "expected": "pass",
                }
            ],
            "open_questions": [] if open_questions is None else open_questions,
        }

    def test_claimed_packet_can_start_without_evidence(self):
        validator.validate_acceptance_contract(
            Path("packet.yaml"), self.packet(state="Claimed")
        )

    def test_complete_packet_requires_criterion_evidence(self):
        with self.assertRaises(ValueError) as context:
            validator.validate_acceptance_contract(
                Path("packet.yaml"), self.packet(state="Complete")
            )
        self.assertIn("evidence_refs", str(context.exception))

    def test_criterion_affecting_blocking_unknown_blocks_ready(self):
        packet = self.packet(
            state="Ready",
            open_questions=[
                {
                    "id": "TEST-T015-P002-OQ001",
                    "question": "Is the validation source available?",
                    "affects_criteria": ["TEST-T015-P002-AC001"],
                    "owner": "agent",
                    "disposition": "blocking",
                    "resolution_ref": None,
                }
            ],
        )
        with self.assertRaises(ValueError) as context:
            validator.validate_open_questions(Path("packet.yaml"), packet)
        self.assertIn("blocking", str(context.exception))

    def test_resolved_unknown_allows_ready(self):
        packet = self.packet(
            state="Ready",
            open_questions=[
                {
                    "id": "TEST-T015-P002-OQ001",
                    "question": "Is the validation source available?",
                    "affects_criteria": ["TEST-T015-P002-AC001"],
                    "owner": "agent",
                    "disposition": "resolved",
                    "resolution_ref": "TEST-T015-P002-EV001",
                }
            ],
        )
        validator.validate_open_questions(Path("packet.yaml"), packet)

    def test_invalid_work_metadata_is_rejected(self):
        packet = self.packet()
        packet["work_type"] = "unknown"
        with self.assertRaises(ValueError) as context:
            validator.validate_work_metadata(
                Path("packet.yaml"),
                packet,
            )
        self.assertIn("work_type", str(context.exception))


if __name__ == "__main__":
    unittest.main()
