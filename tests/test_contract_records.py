import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate-contract-records.py"
SPEC = importlib.util.spec_from_file_location("validate_contract_records", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def packet(**overrides):
    value = {
        "packet_id": "TEST-T005-P001",
        "task_id": "CENG-T005",
        "state": "Implementing",
        "actor": {
            "agent_id": "agent-1",
            "harness": "test",
            "model": "test-model",
            "session_id": "session-1",
        },
        "capabilities": ["read:repository", "execute:local-validation"],
        "risk_tier": "high",
        "approval_policy": "user",
        "external_effects": [],
        "trust_boundary_ref": "docs/agent-trust-boundaries.md",
        "execution_budget_ref": "templates/execution-budget.yaml",
        "checkpoint_ref": "templates/execution-checkpoint.yaml",
        "evaluation_ref": "templates/evaluation-plan.yaml",
        "agent_run_ref": "templates/agent-run.yaml",
        "observability_refs": ["templates/agent-event.yaml"],
        "incident_refs": ["templates/agent-incident.yaml"],
    }
    value.update(overrides)
    return value


class SecuritySemanticTests(unittest.TestCase):
    def test_valid_high_risk_packet(self):
        validator.validate_security_semantics(packet())

    def test_automatic_high_risk_approval_is_rejected(self):
        with self.assertRaises(ValueError):
            validator.validate_security_semantics(packet(approval_policy="automatic"))

    def test_excessive_capability_is_rejected(self):
        with self.assertRaises(ValueError):
            validator.validate_security_semantics(
                packet(capabilities=["admin:repository"])
            )

    def test_unlisted_external_effect_is_rejected(self):
        with self.assertRaises(ValueError):
            validator.validate_security_semantics(
                packet(external_effects=[{"declared": True}])
            )

    def test_unredacted_restricted_evidence_is_rejected(self):
        policy = {
            "evidence_policy_version": 1,
            "classification": "restricted",
            "contains_sensitive_data": True,
            "redaction": {"required": True, "performed": False},
            "secret_scan": {"required": True, "result": "pass"},
            "access": {
                "storage": "restricted_store",
                "encryption_at_rest": True,
            },
            "retention": {},
            "telemetry": {"raw_content_allowed": False},
        }
        with self.assertRaises(ValueError):
            validator.validate_evidence_policy(policy, "synthetic-policy")


if __name__ == "__main__":
    unittest.main()
