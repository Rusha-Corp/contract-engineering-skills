"""Tests for code-health gate: file size limits and dead-code review enforcement."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCRIPT = ROOT / "scripts" / "validate-contract-records.py"
SPEC = importlib.util.spec_from_file_location("validate_contract_records_code_health", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

CODE_HEALTH = validator.code_health


def _basic_packet(**overrides):
    base = {
        "packet_id": "TEST-T010-P001",
        "task_id": "TEST-T010",
        "phase": "P1_IMPLEMENTATION",
        "domain": "coding",
        "title": "Test packet",
        "objective": "Test objective",
        "scope": {"in": ["src/"], "out": []},
        "owner": {
            "identity": "Emmanuel",
            "identity_type": "human",
            "authentication_ref": "gpg:test",
            "signed_at": "2026-01-01T00:00:00Z",
        },
        "reviewer": "user",
        "cleanup_owner": "droid",
        "dependencies": [],
        "locks": [],
        "baseline_refs": [".contract-engineering/protocol.lock.yaml", "0" * 40],
        "acceptance_criteria": [{"id": "TEST-T010-P001-AC001", "statement": "pass"}],
        "validation_plan": [
            {"id": "TEST-T010-P001-VAL001", "kind": "tests", "expected": "pass"}
        ],
        "state": "Implementing",
        "claim_timestamp": "2026-01-01T00:00:00Z",
        "cleanup_scope": {
            "dead_refs": [],
            "stale_refs": [],
            "temp_refs": [],
        },
    }
    base.update(overrides)
    return base


class SizeReviewTests(unittest.TestCase):
    """Rule 1: every changed text file over the limit needs a size_reviews entry."""

    def test_oversized_file_without_size_review_fails(self):
        packet = _basic_packet(
            cleanup_scope={
                "dead_refs": [],
                "stale_refs": [],
                "temp_refs": [],
            }
        )
        with self.assertRaises(ValueError) as ctx:
            CODE_HEALTH.validate_size_reviews(
                packet,
                changed_paths=["scripts/big.py"],
                file_lines={"scripts/big.py": 812},
                max_file_lines=500,
            )
        self.assertIn("size_reviews", str(ctx.exception))

    def test_oversized_file_with_decompose_decision_passes(self):
        packet = _basic_packet(
            cleanup_scope={
                "size_reviews": [
                    {
                        "path": "scripts/big.py",
                        "lines": 812,
                        "decision": "decompose",
                        "rationale": "splitting into modules",
                    }
                ],
                "dead_refs": [],
                "stale_refs": [],
                "temp_refs": [],
            }
        )
        CODE_HEALTH.validate_size_reviews(
            packet,
            changed_paths=["scripts/big.py"],
            file_lines={"scripts/big.py": 812},
            max_file_lines=500,
        )

    def test_oversized_file_with_retain_decision_requires_rationale(self):
        packet = _basic_packet(
            cleanup_scope={
                "size_reviews": [
                    {
                        "path": "scripts/big.py",
                        "lines": 812,
                        "decision": "retain",
                        "rationale": "",
                    }
                ],
                "dead_refs": [],
                "stale_refs": [],
                "temp_refs": [],
            }
        )
        with self.assertRaises(ValueError) as ctx:
            CODE_HEALTH.validate_size_reviews(
                packet,
                changed_paths=["scripts/big.py"],
                file_lines={"scripts/big.py": 812},
                max_file_lines=500,
            )
        self.assertIn("rationale", str(ctx.exception))

    def test_oversized_file_with_defer_decision_requires_follow_up_ref(self):
        packet = _basic_packet(
            cleanup_scope={
                "size_reviews": [
                    {
                        "path": "scripts/big.py",
                        "lines": 812,
                        "decision": "defer",
                        "rationale": "deferred to follow-up",
                    }
                ],
                "dead_refs": [],
                "stale_refs": [],
                "temp_refs": [],
            }
        )
        with self.assertRaises(ValueError) as ctx:
            CODE_HEALTH.validate_size_reviews(
                packet,
                changed_paths=["scripts/big.py"],
                file_lines={"scripts/big.py": 812},
                max_file_lines=500,
            )
        self.assertIn("follow_up_ref", str(ctx.exception))

    def test_file_under_limit_does_not_require_size_review(self):
        packet = _basic_packet(
            cleanup_scope={
                "dead_refs": [],
                "stale_refs": [],
                "temp_refs": [],
            }
        )
        CODE_HEALTH.validate_size_reviews(
            packet,
            changed_paths=["scripts/small.py"],
            file_lines={"scripts/small.py": 100},
            max_file_lines=500,
        )

    def test_excluded_path_does_not_require_size_review(self):
        packet = _basic_packet(
            cleanup_scope={
                "dead_refs": [],
                "stale_refs": [],
                "temp_refs": [],
            }
        )
        CODE_HEALTH.validate_size_reviews(
            packet,
            changed_paths=[".contract-engineering/work-packets/TEST-T010-P001.yaml"],
            file_lines={".contract-engineering/work-packets/TEST-T010-P001.yaml": 600},
            max_file_lines=500,
            exclude=[".contract-engineering/"],
        )


class DeadCodeReviewTests(unittest.TestCase):
    """Rule 2: Handoff/Complete packets need dead_code_review with both checkpoints."""

    def test_handoff_without_dead_code_review_fails(self):
        packet = _basic_packet(state="Handoff")
        with self.assertRaises(ValueError) as ctx:
            CODE_HEALTH.validate_dead_code_review(packet)
        self.assertIn("dead_code_review", str(ctx.exception))

    def test_complete_without_dead_code_review_fails(self):
        packet = _basic_packet(
            state="Complete",
            handoff_ref="TEST-T010-P001-HO001",
            locks=[],
        )
        with self.assertRaises(ValueError) as ctx:
            CODE_HEALTH.validate_dead_code_review(packet)
        self.assertIn("dead_code_review", str(ctx.exception))

    def test_handoff_with_both_checkpoints_passes(self):
        packet = _basic_packet(
            state="Handoff",
            cleanup_scope={
                "dead_code_review": ["baseline", "handoff"],
                "dead_refs": [],
                "stale_refs": [],
                "temp_refs": [],
            },
        )
        CODE_HEALTH.validate_dead_code_review(packet)

    def test_handoff_with_missing_checkpoint_fails(self):
        packet = _basic_packet(
            state="Handoff",
            cleanup_scope={
                "dead_code_review": ["baseline"],
                "dead_refs": [],
                "stale_refs": [],
                "temp_refs": [],
            },
        )
        with self.assertRaises(ValueError) as ctx:
            CODE_HEALTH.validate_dead_code_review(packet)
        self.assertIn("handoff", str(ctx.exception))

    def test_implementing_packet_does_not_require_dead_code_review(self):
        packet = _basic_packet(state="Implementing")
        CODE_HEALTH.validate_dead_code_review(packet)


class DeadRefDecisionTests(unittest.TestCase):
    """Rule 2b: every dead_refs entry needs a decision; needs_evidence blocks Complete."""

    def test_dead_ref_without_decision_fails(self):
        packet = _basic_packet(
            state="Handoff",
            cleanup_scope={
                "dead_code_review": ["baseline", "handoff"],
                "dead_refs": [
                    {"ref": "scripts/x.py::func", "evidence": "rg: no callers"},
                ],
                "stale_refs": [],
                "temp_refs": [],
            },
        )
        with self.assertRaises(ValueError) as ctx:
            CODE_HEALTH.validate_dead_code_review(packet)
        self.assertIn("decision", str(ctx.exception))

    def test_dead_ref_with_remove_decision_passes(self):
        packet = _basic_packet(
            state="Handoff",
            cleanup_scope={
                "dead_code_review": ["baseline", "handoff"],
                "dead_refs": [
                    {
                        "ref": "scripts/x.py::func",
                        "evidence": "rg: no callers",
                        "risk": "low",
                        "decision": "remove",
                    },
                ],
                "stale_refs": [],
                "temp_refs": [],
            },
        )
        CODE_HEALTH.validate_dead_code_review(packet)

    def test_dead_ref_with_needs_evidence_blocks_complete(self):
        packet = _basic_packet(
            state="Complete",
            handoff_ref="TEST-T010-P001-HO001",
            locks=[],
            cleanup_scope={
                "dead_code_review": ["baseline", "handoff"],
                "dead_refs": [
                    {
                        "ref": "scripts/x.py::func",
                        "evidence": "rg: no callers",
                        "risk": "low",
                        "decision": "needs_evidence",
                    },
                ],
                "stale_refs": [],
                "temp_refs": [],
            },
        )
        with self.assertRaises(ValueError) as ctx:
            CODE_HEALTH.validate_dead_code_review(packet)
        self.assertIn("needs_evidence", str(ctx.exception))


class DefaultLimitTests(unittest.TestCase):
    """The max_file_lines defaults to 500 when not configured."""

    def test_default_max_file_lines_is_500(self):
        self.assertEqual(CODE_HEALTH.DEFAULT_MAX_FILE_LINES, 500)

    def test_default_exclude_includes_contract_engineering(self):
        self.assertIn(".contract-engineering/", CODE_HEALTH.DEFAULT_EXCLUDE)


class CountFileLinesTests(unittest.TestCase):
    """count_file_lines reads text files and skips binaries."""

    def test_count_file_lines_reads_text(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.py"
            path.write_text("line1\nline2\nline3\n", encoding="utf-8")
            result = CODE_HEALTH.count_file_lines(path)
            self.assertEqual(result, 3)

    def test_count_file_lines_returns_none_for_binary(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "binary.bin"
            path.write_bytes(b"\x00\x01\x02\x03")
            result = CODE_HEALTH.count_file_lines(path)
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
