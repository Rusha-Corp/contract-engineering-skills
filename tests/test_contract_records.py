import importlib.util
import tempfile
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
        "domain": "coding",
        "scope": {"in": ["src"], "out": []},
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

    def test_security_gate_does_not_depend_on_task_identifier(self):
        value = packet(
            packet_id="TEST-T999-P001",
            task_id="CENG-T999",
            domain="security",
        )
        validator.validate_security_semantics(value)

    def test_classified_sensitive_scope_triggers_security_gate(self):
        value = packet(
            packet_id="TEST-T999-P001",
            task_id="CENG-T999",
            domain="documentation",
            risk_tier="low",
            packet_class="single-domain",
            scope={"in": [".github/workflows/check.yml"], "out": []},
        )
        value.pop("actor")
        with self.assertRaises(ValueError):
            validator.validate_security_semantics(value)

    def test_automatic_high_risk_approval_is_rejected(self):
        with self.assertRaises(ValueError):
            validator.validate_security_semantics(packet(approval_policy="automatic"))

    def test_excessive_capability_is_rejected(self):
        with self.assertRaises(ValueError):
            validator.validate_security_semantics(
                packet(capabilities=["admin:repository"])
            )

    def test_missing_actor_identity_is_rejected(self):
        value = packet()
        value.pop("actor")
        with self.assertRaises(ValueError):
            validator.validate_security_semantics(value)

    def test_security_gate_ignores_historical_task_name(self):
        value = packet(
            packet_id="TEST-T001-P001",
            task_id="CENG-T005",
            domain="security",
        )
        validator.validate_security_semantics(value)

    def test_unlisted_external_effect_is_rejected(self):
        with self.assertRaises(ValueError):
            validator.validate_security_semantics(
                packet(external_effects=[{"declared": True}])
            )

    def test_structured_external_effect_requires_binding_fields(self):
        with self.assertRaises(ValueError):
            validator.validate_security_semantics(
                packet(
                    external_effects=[
                        {
                            "effect_id": "EFFECT-001",
                            "target": "review",
                            "operation": "prepare",
                            "data_classification": "internal",
                            "approval_ref": "",
                            "rollback": "discard draft",
                            "declared": True,
                            "reversible": True,
                        }
                    ]
                )
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


def _packet(packet_id, state, owner="agent", reviewer="user", handoff_ref=None):
    return {
        "packet_id": packet_id,
        "state": state,
        "owner": owner,
        "reviewer": reviewer,
        "handoff_ref": handoff_ref,
    }


LIVE_TRACKER = (
    "# Execution Tracker\n\n"
    "| Task | Packet | State | Owner | Reviewer | Locks |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
)
ARCHIVE_TRACKER = (
    "# Execution Tracker (Archive)\n\n"
    "| Task | Packet | State | Owner | Reviewer | Locks |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
)


class TrackerPartitionTests(unittest.TestCase):
    """validate_tracker enforces live/archive partition invariants."""

    def _write_root(self, live_text, archive_text=None):
        root = Path(tempfile.mkdtemp()) / "ce"
        root.mkdir()
        (root / "execution-tracker.md").write_text(live_text)
        if archive_text is not None:
            (root / validator.ARCHIVE_PACKET_DIR).mkdir(parents=True)
            (root / validator.ARCHIVE_TRACKER).write_text(archive_text)
        return root

    def _row(self, task, packet_id, state):
        return f"| {task} | {packet_id} | {state} | agent | user | released |\n"

    def test_live_packet_must_have_live_row(self):
        root = self._write_root(LIVE_TRACKER)
        live = {"TEST-T001-P001": _packet("TEST-T001-P001", "Implementing")}
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(root, live, {})
        self.assertIn("missing live packet rows", str(ctx.exception))

    def test_archive_packet_must_have_archive_row(self):
        root = self._write_root(
            LIVE_TRACKER,
            ARCHIVE_TRACKER + self._row("T", "TEST-T001-P001", "Complete"),
        )
        archive = {"TEST-T001-P001": _packet("TEST-T001-P001", "Complete", handoff_ref="X")}
        # Row present -> passes.
        validator.validate_tracker(root, {}, archive)
        # Row missing -> fails.
        (root / validator.ARCHIVE_TRACKER).write_text(ARCHIVE_TRACKER)
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(root, {}, archive)
        self.assertIn("missing archive packet rows", str(ctx.exception))

    def test_archive_packet_must_be_terminal(self):
        root = self._write_root(
            LIVE_TRACKER,
            ARCHIVE_TRACKER + "| T | TEST-T001-P001 | Implementing | agent | user | released |\n",
        )
        archive = {"TEST-T001-P001": _packet("TEST-T001-P001", "Implementing")}
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(root, {}, archive)
        self.assertIn("not terminal", str(ctx.exception))

    def test_archive_complete_without_handoff_ref_fails(self):
        root = self._write_root(
            LIVE_TRACKER,
            ARCHIVE_TRACKER + self._row("T", "TEST-T001-P001", "Complete"),
        )
        archive = {"TEST-T001-P001": _packet("TEST-T001-P001", "Complete", handoff_ref=None)}
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(root, {}, archive)
        self.assertIn("without handoff_ref", str(ctx.exception))

    def test_packet_in_both_trackers_fails(self):
        root = self._write_root(
            LIVE_TRACKER + self._row("T", "TEST-T001-P001", "Complete"),
            ARCHIVE_TRACKER + self._row("T", "TEST-T001-P001", "Complete"),
        )
        live = {"TEST-T001-P001": _packet("TEST-T001-P001", "Complete", handoff_ref="X")}
        archive = {"TEST-T001-P001": _packet("TEST-T001-P001", "Complete", handoff_ref="X")}
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(root, live, archive)
        self.assertIn("both trackers", str(ctx.exception))

    def test_orphan_live_row_fails(self):
        root = self._write_root(LIVE_TRACKER + self._row("T", "TEST-T001-P001", "Implementing"))
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(root, {}, {})
        self.assertIn("orphan rows", str(ctx.exception))

    def test_orphan_archive_row_fails(self):
        root = self._write_root(
            LIVE_TRACKER,
            ARCHIVE_TRACKER + self._row("T", "TEST-T001-P001", "Complete"),
        )
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(root, {}, {})
        self.assertIn("orphan rows", str(ctx.exception))

    def test_archive_dir_without_ledger_fails(self):
        root = Path(tempfile.mkdtemp()) / "ce"
        root.mkdir()
        (root / validator.ARCHIVE_PACKET_DIR).mkdir(parents=True)
        (root / "execution-tracker.md").write_text(LIVE_TRACKER)
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(root, {}, {})
        self.assertIn("missing", str(ctx.exception))

    def test_valid_partitioned_state_passes(self):
        root = self._write_root(
            LIVE_TRACKER + self._row("T", "TEST-T001-P001", "Implementing"),
            ARCHIVE_TRACKER + self._row("T", "TEST-T002-P001", "Complete"),
        )
        live = {"TEST-T001-P001": _packet("TEST-T001-P001", "Implementing")}
        archive = {"TEST-T002-P001": _packet("TEST-T002-P001", "Complete", handoff_ref="X")}
        validator.validate_tracker(root, live, archive)

    def test_task_tracker_shard_passes(self):
        root = self._write_root(LIVE_TRACKER)
        shard = root / validator.TRACKER_SHARD_DIR
        shard.mkdir()
        (shard / "TEST-T001.md").write_text(
            LIVE_TRACKER + self._row("TEST-T001", "TEST-T001-P001", "Implementing")
        )
        validator.validate_tracker(
            root,
            {"TEST-T001-P001": _packet("TEST-T001-P001", "Implementing")},
            {},
        )

    def test_tracker_shard_rejects_wrong_task(self):
        root = self._write_root(LIVE_TRACKER)
        shard = root / validator.TRACKER_SHARD_DIR
        shard.mkdir()
        (shard / "TEST-T001.md").write_text(
            LIVE_TRACKER + self._row("TEST-T002", "TEST-T002-P001", "Implementing")
        )
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(
                root,
                {"TEST-T002-P001": _packet("TEST-T002-P001", "Implementing")},
                {},
            )
        self.assertIn("does not belong", str(ctx.exception))

    def test_tracker_shard_rejects_duplicate_packet(self):
        root = self._write_root(
            LIVE_TRACKER + self._row("TEST-T001", "TEST-T001-P001", "Implementing")
        )
        shard = root / validator.TRACKER_SHARD_DIR
        shard.mkdir()
        (shard / "TEST-T001.md").write_text(
            LIVE_TRACKER + self._row("TEST-T001", "TEST-T001-P001", "Implementing")
        )
        live = {"TEST-T001-P001": _packet("TEST-T001-P001", "Implementing")}
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(root, live, {})
        self.assertIn("index and shard", str(ctx.exception))

    def test_tracker_index_enforces_row_cap(self):
        rows = "".join(
            self._row("TEST-T001", f"TEST-T001-P{i:03d}", "Implementing")
            for i in range(1, validator.MAX_INDEX_PACKET_ROWS + 2)
        )
        root = self._write_root(LIVE_TRACKER + rows)
        live = {
            f"TEST-T001-P{i:03d}": _packet(
                f"TEST-T001-P{i:03d}", "Implementing"
            )
            for i in range(1, validator.MAX_INDEX_PACKET_ROWS + 2)
        }
        with self.assertRaises(ValueError) as ctx:
            validator.validate_tracker(root, live, {})
        self.assertIn("active index has", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
