import copy
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
from referencing import Registry, Resource


REPO = Path(__file__).parents[1]
SCRIPT = REPO / "scripts" / "validate-contract-records.py"
SPEC = importlib.util.spec_from_file_location("validate_contract_records", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

NOW = datetime(2026, 11, 23, 22, 0, tzinfo=timezone.utc)
SHA = "a" * 40


def assessment(**overrides):
    value = {
        "version": 1,
        "status": "complete",
        "risk": "low",
        "rationale": "Only a local helper changes.",
        "packet_revision": 2,
        "assessed_at": "2026-11-23T21:50:00Z",
        "source_revision": SHA,
        "components": [],
        "couplings": [],
        "rollout": [],
        "unknowns": [],
        "inference_review": {
            "status": "not_required",
            "evidence_refs": [],
            "reviewed_at": None,
        },
        "live_scope": {
            "environments": [],
            "source_revision": None,
            "live_revision": None,
            "observed_at": None,
            "evidence_refs": [],
        },
        "post_deploy_verification": {
            "entry_point": None,
            "source_revision": None,
            "live_revision": None,
            "verified_at": None,
            "evidence_refs": [],
        },
    }
    value.update(overrides)
    return value


def packet(**overrides):
    value = {
        "packet_id": "TEST-T038-P001",
        "state": "Implementing",
        "revision": 2,
        "claim_timestamp": "2026-11-23T21:00:00Z",
        "blast_radius": assessment(),
    }
    value.update(overrides)
    return value


def high_risk_assessment(**overrides):
    value = assessment(
        risk="high",
        rationale="The service identity loses direct pod mutation permissions.",
        components=[{
            "name": "gate-service",
            "kind": "service",
            "provenance": "verified",
            "environments": ["dev"],
            "consumers": ["platform-gate"],
            "shared_resources": ["pods"],
            "identities": ["system:serviceaccount:rusha-dev:rusha-gate-svc"],
        }],
        couplings=[{
            "from": "rusha-gate-svc",
            "to": "pods/create",
            "effect": "permission-removal",
            "compatibility": "incompatible",
            "provenance": "verified",
            "rationale": "The running revision still creates pods directly.",
        }],
        rollout=[
            {"phase": "expand", "description": "Deploy Job-based service with pod permissions retained.", "status": "verified", "evidence_refs": ["EV-EXPAND"]},
            {"phase": "migrate", "description": "Verify Jobs through the real gate entry point.", "status": "verified", "evidence_refs": ["EV-MIGRATE"]},
            {"phase": "contract", "description": "Remove direct pod create/delete.", "status": "verified", "evidence_refs": ["EV-CONTRACT"]},
        ],
        live_scope={
            "environments": ["dev"],
            "source_revision": SHA,
            "live_revision": "b" * 40,
            "observed_at": "2026-11-23T21:55:00Z",
            "evidence_refs": ["EV-LIVE"],
        },
        post_deploy_verification={
            "entry_point": "platform gate run",
            "source_revision": SHA,
            "live_revision": "b" * 40,
            "verified_at": "2026-11-23T21:58:00Z",
            "evidence_refs": ["EV-POST"],
        },
    )
    value.update(overrides)
    return value


class BlastRadiusSemanticTests(unittest.TestCase):
    def test_low_risk_assessment_passes(self):
        validator.validate_blast_radius_semantics(packet(), Path("packet.yaml"), now=NOW)

    def test_missing_assessment_for_new_active_packet_fails(self):
        value = packet()
        del value["blast_radius"]
        with self.assertRaisesRegex(ValueError, "blast_radius is required"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_legacy_terminal_packets_remain_valid(self):
        for state in ("Complete", "Cancelled"):
            value = packet(state=state, claim_timestamp="2026-01-01T00:00:00Z")
            del value["blast_radius"]
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_material_packet_revision_makes_assessment_stale(self):
        value = packet(revision=3)
        with self.assertRaisesRegex(ValueError, "stale"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_explicit_no_impact_requires_low_risk_and_reason(self):
        value = packet(blast_radius=assessment(status="no_runtime_impact", rationale="Documentation only."))
        validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)
        value["blast_radius"]["rationale"] = ""
        with self.assertRaisesRegex(ValueError, "rationale"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_unknown_shared_runtime_impact_is_high_and_blocks_ready(self):
        value = packet(state="Ready", blast_radius=assessment(
            status="unknown", risk="high", unknowns=["shared RBAC"]
        ))
        with self.assertRaisesRegex(ValueError, "unknown"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_medium_handoff_requires_inference_review(self):
        value = packet(state="Handoff", blast_radius=assessment(
            risk="medium",
            inference_review={"status": "pending", "evidence_refs": [], "reviewed_at": None},
        ))
        with self.assertRaisesRegex(ValueError, "inference_review"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)
        value["blast_radius"]["inference_review"] = {
            "status": "completed", "evidence_refs": ["EV-INFER"],
            "reviewed_at": "2026-11-23T21:51:00Z",
        }
        validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_rbac_incident_identifies_live_consumer_and_blocks_ready(self):
        value = packet(state="Ready", blast_radius=high_risk_assessment())
        value["blast_radius"]["live_scope"]["evidence_refs"] = []
        with self.assertRaisesRegex(ValueError, "live_scope"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_expand_migrate_contract_with_retained_permission_passes(self):
        value = packet(state="Ready", blast_radius=high_risk_assessment())
        validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_incompatible_contraction_requires_ordered_evidence(self):
        value = packet(state="Ready", blast_radius=high_risk_assessment())
        value["blast_radius"]["rollout"] = [value["blast_radius"]["rollout"][2]]
        with self.assertRaisesRegex(ValueError, "expand.*migrate.*contract"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_stale_live_evidence_blocks_high_risk_ready(self):
        value = packet(state="Ready", blast_radius=high_risk_assessment())
        value["blast_radius"]["live_scope"]["observed_at"] = (
            NOW - timedelta(hours=25)
        ).isoformat().replace("+00:00", "Z")
        with self.assertRaisesRegex(ValueError, "stale"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_high_risk_complete_requires_real_entry_point_verification(self):
        value = packet(state="Complete", blast_radius=high_risk_assessment())
        value["blast_radius"]["post_deploy_verification"]["entry_point"] = None
        with self.assertRaisesRegex(ValueError, "post_deploy_verification"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_pre_adoption_active_packet_requires_migration_assessment(self):
        value = packet(state="Implementing", claim_timestamp="2026-01-01T00:00:00Z")
        del value["blast_radius"]
        with self.assertRaisesRegex(ValueError, "blast_radius is required"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)
        value["blast_radius"] = assessment(
            status="unknown", risk="high", unknowns=["migration triage"],
        )
        validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_medium_review_rejects_invalid_timestamp(self):
        value = packet(state="Handoff", blast_radius=assessment(
            risk="medium",
            inference_review={
                "status": "completed", "evidence_refs": ["EV-INFER"],
                "reviewed_at": "yesterday",
            },
        ))
        with self.assertRaisesRegex(ValueError, "ISO-8601"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_high_risk_ready_requires_rollout_order(self):
        value = packet(state="Ready", blast_radius=high_risk_assessment(rollout=[]))
        value["blast_radius"]["couplings"][0]["compatibility"] = "compatible"
        with self.assertRaisesRegex(ValueError, "rollout order"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_ready_allows_planned_contract_but_complete_does_not(self):
        value = packet(state="Ready", blast_radius=high_risk_assessment())
        value["blast_radius"]["rollout"][2] = {
            "phase": "contract",
            "description": "Remove direct pod mutation after verified migration.",
            "status": "planned",
            "evidence_refs": [],
        }
        validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)
        value["state"] = "Complete"
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_completed_history_does_not_expire(self):
        value = packet(state="Complete", blast_radius=high_risk_assessment())
        value["blast_radius"]["live_scope"]["observed_at"] = (
            NOW - timedelta(days=30)
        ).isoformat().replace("+00:00", "Z")
        value["blast_radius"]["post_deploy_verification"]["verified_at"] = (
            NOW - timedelta(days=29)
        ).isoformat().replace("+00:00", "Z")
        validator.validate_blast_radius_semantics(value, Path("packet.yaml"), now=NOW)

    def test_nested_live_evidence_must_exist(self):
        value = packet(state="Ready", blast_radius=high_risk_assessment())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            evidence.mkdir()
            for ref in ("EV-EXPAND", "EV-MIGRATE", "EV-CONTRACT", "EV-POST"):
                (evidence / f"{ref}.md").write_text(f"# {ref}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing blast_radius.live_scope evidence EV-LIVE"):
                validator.validate_references(root, {value["packet_id"]: value})


class BlastRadiusSchemaTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((REPO / "schemas" / "blast-radius.schema.json").read_text())
        topology = json.loads((REPO / "schemas" / "runtime-topology.schema.json").read_text())
        self.registry = Registry().with_resources([
            (self.schema["$id"], Resource.from_contents(self.schema)),
            (topology["$id"], Resource.from_contents(topology)),
        ])

    def test_schema_rejects_unlabelled_provenance(self):
        value = high_risk_assessment()
        value["components"][0]["provenance"] = "observed"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.schema, registry=self.registry).validate(value)

    def test_topology_schema_requires_path_mapping(self):
        schema = json.loads((REPO / "schemas" / "runtime-topology.schema.json").read_text())
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({"version": 1, "components": [{"name": "gate", "paths": []}]}, schema)


if __name__ == "__main__":
    unittest.main()
