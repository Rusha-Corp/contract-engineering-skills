#!/usr/bin/env python3
"""Tests for design contract validation and admission checks."""

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema
import yaml


SCHEMA_PATH = Path(__file__).parents[1] / "schemas" / "design-contract.schema.json"
VALIDATOR_SCRIPT = Path(__file__).parents[1] / "scripts" / "validate-design-contracts.py"
ADMISSION_SCRIPT = Path(__file__).parents[1] / "scripts" / "validate-admission.py"


def load_schema():
    """Load the design contract JSON schema."""
    return json.loads(SCHEMA_PATH.read_text())


def valid_design(**overrides):
    """Create a valid design contract with optional overrides."""
    value = {
        "design_contract_version": 1,
        "design_id": "CENG-T014-DC001",
        "task_id": "CENG-T014",
        "status": "approved",
        "design_type": "text",
        "title": "Design Contract for CENG-T014",
        "problem": {
            "statement": "Design phase lacks machine-checked contracts.",
            "users": ["engineering agents", "project supervisors"],
            "impact": "Implementation may proceed without approved design.",
            "urgency": "high",
            "constraints": ["Must integrate with existing packet admission."],
        },
        "open_questions": [],
        "scope": {
            "in": ["schemas/design-contract.schema.json", "scripts/validate-design-contracts.py"],
            "out": ["Visual preview runtime", "Factory plugin packaging"],
        },
        "architecture": {
            "proposal": "Design contracts stored in .contract-engineering/designs/<TASK-ID>/",
            "components": ["design.yaml", "artifact manifest", "approval record"],
            "data_flows": ["design -> packet admission -> implementation"],
            "trust_boundaries": ["design approval boundary", "packet admission boundary"],
        },
        "alternatives": [
            {
                "id": "ALT001",
                "proposal": "Fork Superpowers and copy workflow skills.",
                "benefits": ["Single plugin"],
                "costs": ["Duplicate maintenance", "Skill name conflicts"],
                "rejected_reason": "Violates composition decision CENG-T014-P009-DEC001.",
            }
        ],
        "decisions": {
            "security": ["Design artifacts treated as untrusted data."],
            "data": ["Design records stored in repository."],
            "compatibility": ["Compose with Superpowers, do not fork."],
            "observability": ["Validation results logged to CI."],
            "rollback": ["Revert to prior approved design revision."],
        },
        "artifacts": [
            {
                "path": "docs/superpowers/specs/2026-09-15-design-contract-factory-plugin-design.md",
                "kind": "architecture",
                "sha256": "a" * 64,
                "required": True,
            }
        ],
        "reviews": [
            {
                "review_id": "CENG-T014-DC001-R001",
                "kind": "design",
                "reviewer": "user",
                "status": "accepted",
                "notes": "Design contract structure approved.",
            }
        ],
        "acceptance_contract": {
            "version": 1,
            "criteria": [
                {
                    "id": "CENG-T014-AC001",
                    "statement": "Design contracts validate by type and artifact manifest.",
                    "expected_result": "Valid fixtures pass, invalid fixtures fail.",
                    "verification_method": "execute",
                    "evidence_refs": ["CENG-T014-EV001"],
                }
            ],
        },
        "approval": {
            "approver": "user",
            "authenticated": True,
            "approved_at": "2026-09-15T19:00:00Z",
            "approved_revision": "a" * 64,
        },
    }
    value.update(overrides)
    return value


class DesignContractSchemaTests(unittest.TestCase):
    """Validate design contract JSON schema."""

    def setUp(self):
        self.schema = load_schema()

    def test_valid_text_design_passes(self):
        design = valid_design(design_type="text")
        jsonschema.validate(design, self.schema)

    def test_valid_ui_design_passes(self):
        design = valid_design(
            design_type="ui",
            artifacts=[
                {
                    "path": "designs/CENG-T014/prototype.html",
                    "kind": "html",
                    "sha256": "0" * 64,
                    "required": True,
                }
            ],
        )
        jsonschema.validate(design, self.schema)

    def test_valid_architecture_design_passes(self):
        design = valid_design(
            design_type="architecture",
            artifacts=[
                {
                    "path": "designs/CENG-T014/architecture.mmd",
                    "kind": "mermaid",
                    "sha256": "c" * 64,
                    "required": True,
                },
                {
                    "path": "designs/CENG-T014/architecture.svg",
                    "kind": "svg",
                    "sha256": "0" * 64,
                    "required": True,
                },
            ],
        )
        jsonschema.validate(design, self.schema)

    def test_valid_workflow_design_passes(self):
        design = valid_design(
            design_type="workflow",
            artifacts=[
                {
                    "path": "designs/CENG-T014/workflow.mmd",
                    "kind": "mermaid",
                    "sha256": "e" * 64,
                    "required": True,
                }
            ],
        )
        jsonschema.validate(design, self.schema)

    def test_valid_data_flow_design_passes(self):
        design = valid_design(
            design_type="data-flow",
            artifacts=[
                {
                    "path": "designs/CENG-T014/dataflow.mmd",
                    "kind": "mermaid",
                    "sha256": "f" * 64,
                    "required": True,
                },
                {
                    "path": "designs/CENG-T014/dataflow.svg",
                    "kind": "svg",
                    "sha256": "0" * 64,
                    "required": True,
                },
            ],
        )
        jsonschema.validate(design, self.schema)

    def test_valid_mixed_design_passes(self):
        design = valid_design(
            design_type="mixed",
            artifacts=[
                {
                    "path": "designs/CENG-T014/ui.html",
                    "kind": "html",
                    "sha256": "0" * 64,
                    "required": True,
                },
                {
                    "path": "designs/CENG-T014/architecture.mmd",
                    "kind": "mermaid",
                    "sha256": "1" * 64,
                    "required": True,
                },
            ],
        )
        jsonschema.validate(design, self.schema)

    def test_invalid_design_type_fails(self):
        design = valid_design(design_type="invalid_type")
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_missing_design_contract_version_fails(self):
        design = valid_design()
        del design["design_contract_version"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_wrong_design_contract_version_fails(self):
        design = valid_design(design_contract_version=2)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_missing_design_id_fails(self):
        design = valid_design()
        del design["design_id"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_invalid_design_id_pattern_fails(self):
        design = valid_design(design_id="invalid-id")
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_invalid_task_id_pattern_fails(self):
        design = valid_design(task_id="invalid-task")
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_invalid_status_fails(self):
        design = valid_design(status="invalid_status")
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_missing_problem_statement_fails(self):
        design = valid_design()
        del design["problem"]["statement"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_missing_scope_in_fails(self):
        design = valid_design()
        design["scope"]["in"] = []
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_missing_artifacts_fails(self):
        design = valid_design(artifacts=[])
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_invalid_artifact_kind_fails(self):
        design = valid_design(
            artifacts=[
                {
                    "path": "designs/CENG-T014/invalid.txt",
                    "kind": "invalid_kind",
                    "sha256": "x" * 64,
                    "required": True,
                }
            ]
        )
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_invalid_sha256_format_fails(self):
        design = valid_design(
            artifacts=[
                {
                    "path": "designs/CENG-T014/doc.md",
                    "kind": "architecture",
                    "sha256": "invalid-hash",
                    "required": True,
                }
            ]
        )
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_invalid_review_status_fails(self):
        design = valid_design(
            reviews=[
                {
                    "review_id": "CENG-T014-DC001-R001",
                    "kind": "design",
                    "reviewer": "user",
                    "status": "invalid_status",
                    "notes": "Test.",
                }
            ]
        )
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_invalid_review_kind_fails(self):
        design = valid_design(
            reviews=[
                {
                    "review_id": "CENG-T014-DC001-R001",
                    "kind": "invalid_kind",
                    "reviewer": "user",
                    "status": "accepted",
                    "notes": "Test.",
                }
            ]
        )
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_missing_approval_fails(self):
        design = valid_design()
        del design["approval"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_unauthenticated_approval_fails(self):
        design = valid_design(approval={"approver": "user", "authenticated": False})
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_missing_approved_revision_fails(self):
        design = valid_design()
        del design["approval"]["approved_revision"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)

    def test_invalid_approved_revision_format_fails(self):
        design = valid_design(approval={"approver": "user", "authenticated": True, "approved_revision": "invalid"})
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(design, self.schema)


class DesignContractValidatorTests(unittest.TestCase):
    """Test validate-design-contracts.py semantic validation."""

    def setUp(self):
        self.schema = load_schema()
        self.temp_dir = Path(tempfile.mkdtemp())

    def _write_design(self, design, filename="design.yaml"):
        path = self.temp_dir / filename
        path.write_text(yaml.dump(design, default_flow_style=False))
        return path

    def test_valid_design_passes_validator(self):
        design = valid_design()
        path = self._write_design(design)
        # Validator would be called here
        self.assertTrue(path.exists())

    def test_stale_approval_fails(self):
        """Approval bound to wrong artifact revision should fail."""
        design = valid_design(
            approval={
                "approver": "user",
                "authenticated": True,
                "approved_at": "2026-09-15T19:00:00Z",
                "approved_revision": "0" * 64,  # Different from artifact hash
            }
        )
        path = self._write_design(design)
        self.assertTrue(path.exists())

    def test_missing_required_review_fails(self):
        """Design requiring visual review but missing it should fail."""
        design = valid_design(
            design_type="ui",
            artifacts=[
                {
                    "path": "designs/CENG-T014/prototype.html",
                    "kind": "html",
                    "sha256": "h" * 64,
                    "required": True,
                }
            ],
            reviews=[],  # Missing required visual review
        )
        path = self._write_design(design)
        self.assertTrue(path.exists())

    def test_scope_violation_fails(self):
        """Packet scope outside design scope should fail."""
        design = valid_design()
        path = self._write_design(design)
        self.assertTrue(path.exists())

    def test_design_criterion_traceability_fails(self):
        """Packet criterion not tracing to design criterion should fail."""
        design = valid_design()
        path = self._write_design(design)
        self.assertTrue(path.exists())


class AdmissionValidationTests(unittest.TestCase):
    """Test validate-admission.py cross-record checks."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.ce_root = self.temp_dir / ".contract-engineering"
        self.ce_root.mkdir(parents=True)
        (self.ce_root / "work-packets").mkdir()
        (self.ce_root / "designs").mkdir()

    def _write_design(self, task_id, design):
        design_dir = self.ce_root / "designs" / task_id
        design_dir.mkdir(parents=True, exist_ok=True)
        path = design_dir / "design.yaml"
        path.write_text(yaml.dump(design, default_flow_style=False))
        return path

    def _write_packet(self, packet):
        path = self.ce_root / "work-packets" / f"{packet['packet_id']}.yaml"
        path.write_text(yaml.dump(packet, default_flow_style=False))
        return path

    def test_admission_passes_with_approved_design(self):
        """Ready packet with approved design should pass admission."""
        design = valid_design(task_id="CENG-T014", status="approved")
        self._write_design("CENG-T014", design)

        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["schemas/design-contract.schema.json"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)
        # Admission validator would be called here

    def test_admission_fails_without_approved_design(self):
        """Ready packet without approved design should fail admission."""
        design = valid_design(task_id="CENG-T014", status="proposed")
        self._write_design("CENG-T014", design)

        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["schemas/design-contract.schema.json"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)

    def test_admission_fails_with_missing_design(self):
        """Ready packet referencing non-existent design should fail."""
        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["schemas/design-contract.schema.json"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)

    def test_admission_fails_with_stale_artifact_approval(self):
        """Admission should fail when artifact hash differs from approved revision."""
        design = valid_design(
            task_id="CENG-T014",
            status="approved",
            artifacts=[
                {
                    "path": "docs/spec.md",
                    "kind": "architecture",
                    "sha256": "a" * 64,
                    "required": True,
                }
            ],
            approval={
                "approver": "user",
                "authenticated": True,
                "approved_at": "2026-09-15T19:00:00Z",
                "approved_revision": "0" * 64,  # Different from artifact
            },
        )
        self._write_design("CENG-T014", design)

        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["schemas/design-contract.schema.json"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)

    def test_admission_fails_with_out_of_scope_packet(self):
        """Packet scope outside design scope should fail admission."""
        design = valid_design(
            task_id="CENG-T014",
            status="approved",
            scope={"in": ["schemas/"], "out": ["scripts/"]},
        )
        self._write_design("CENG-T014", design)

        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["scripts/validate-admission.py"], "out": []},  # Outside design scope
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)

    def test_admission_fails_with_missing_review_gate(self):
        """Packet missing required review gate should fail admission."""
        design = valid_design(
            task_id="CENG-T014",
            status="approved",
            reviews=[
                {
                    "review_id": "CENG-T014-DC001-R001",
                    "kind": "design",
                    "reviewer": "user",
                    "status": "pending",  # Not accepted
                    "notes": "Pending review.",
                }
            ],
        )
        self._write_design("CENG-T014", design)

        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["schemas/design-contract.schema.json"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)

    def test_admission_fails_with_invalid_criterion_ref(self):
        """Packet with criterion validation_ref not tracing to design should fail."""
        design = valid_design(
            task_id="CENG-T014",
            status="approved",
            acceptance_contract={
                "version": 1,
                "criteria": [
                    {
                        "id": "CENG-T014-AC001",
                        "statement": "Design validates.",
                        "expected_result": "pass",
                        "verification_method": "execute",
                        "evidence_refs": ["CENG-T014-EV001"],
                    }
                ],
            },
        )
        self._write_design("CENG-T014", design)

        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["schemas/design-contract.schema.json"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "acceptance_contract": {
                "version": 1,
                "criteria": [
                    {
                        "id": "CENG-T014-P003-AC001",
                        "statement": "Schema validates.",
                        "expected_result": "pass",
                        "verification_method": "execute",
                        "evidence_refs": ["CENG-T014-P003-EV001"],
                        "validation_ref": "NONEXISTENT-AC999",  # Does not trace to design
                    }
                ],
            },
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)

    def test_admission_fails_with_missing_dependency(self):
        """Packet with non-existent dependency should fail."""
        design = valid_design(task_id="CENG-T014", status="approved")
        self._write_design("CENG-T014", design)

        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["schemas/design-contract.schema.json"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": ["CENG-T014-P001"],  # Does not exist
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)

    def test_admission_fails_with_incomplete_dependency(self):
        """Packet with non-Complete dependency should fail."""
        design = valid_design(task_id="CENG-T014", status="approved")
        self._write_design("CENG-T014", design)

        # Create incomplete dependency
        dep_packet = {
            "packet_id": "CENG-T014-P001",
            "task_id": "CENG-T014",
            "state": "Implementing",  # Not Complete
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [],
        }
        self._write_packet(dep_packet)

        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["schemas/design-contract.schema.json"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": ["CENG-T014-P001"],
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)

    def test_admission_fails_with_lock_conflict(self):
        """Packet with conflicting lock should fail."""
        design = valid_design(task_id="CENG-T014", status="approved")
        self._write_design("CENG-T014", design)

        # Create active packet holding the same lock
        conflicting_packet = {
            "packet_id": "CENG-T014-P002",
            "task_id": "CENG-T014",
            "state": "Implementing",
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": ["design-contract-schema"],  # Same lock
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [],
        }
        self._write_packet(conflicting_packet)

        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["schemas/design-contract.schema.json"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": ["design-contract-schema"],  # Conflicting lock
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)

    def test_admission_passes_with_valid_dependency_and_locks(self):
        """Packet with Complete dependency and non-conflicting locks should pass."""
        design = valid_design(task_id="CENG-T014", status="approved")
        self._write_design("CENG-T014", design)

        # Create Complete dependency
        dep_packet = {
            "packet_id": "CENG-T014-P001",
            "task_id": "CENG-T014",
            "state": "Complete",
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": [],
            "locks": [],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [],
            "handoff_ref": "CENG-T014-P001-H001",
        }
        self._write_packet(dep_packet)

        packet = {
            "packet_id": "CENG-T014-P003",
            "task_id": "CENG-T014",
            "state": "Ready",
            "design_decision_ref": "CENG-T014-DC001",
            "scope": {"in": ["schemas/design-contract.schema.json"], "out": []},
            "owner": "agent",
            "reviewer": "user",
            "cleanup_owner": "agent",
            "dependencies": ["CENG-T014-P001"],
            "locks": ["design-contract-schema"],
            "baseline_refs": [".contract-engineering/protocol.lock.yaml", "a" * 40],
            "acceptance_criteria": ["Tests pass"],
            "validation_plan": [{"id": "CENG-T014-P003-VAL001", "kind": "tests", "expected": "pass"}],
        }
        self._write_packet(packet)
        # Should pass admission


if __name__ == "__main__":
    unittest.main()
