"""Tests for the extracted packet-scope enforcement gate.

These tests verify the three gate rules that fix the false positives:
1. Skip diffs that touch no .contract-engineering/ paths.
2. Claim artifacts (evidence/handoff/decision) by the packet ID in their filename.
3. Skip when the base SHA is unreachable (force-push aftermath).
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

SPEC = importlib.util.spec_from_file_location(
    "enforce_packet_scope", ROOT / "scripts/enforce_packet_scope.py"
)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

SCOPE_SPEC = importlib.util.spec_from_file_location(
    "packet_scope", ROOT / "scripts/packet_scope.py"
)
assert SCOPE_SPEC and SCOPE_SPEC.loader
scope = importlib.util.module_from_spec(SCOPE_SPEC)
SCOPE_SPEC.loader.exec_module(scope)


def _make_packet(directory: Path, packet_id: str, scope_in: list[str]) -> None:
    """Write a minimal valid work-packet to *directory*."""
    pkt_dir = directory / ".contract-engineering" / "work-packets"
    pkt_dir.mkdir(parents=True, exist_ok=True)
    (pkt_dir / f"{packet_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "packet_id": packet_id,
                "task_id": packet_id.rsplit("-P", 1)[0],
                "phase": "P1_IMPLEMENTATION",
                "domain": "coding",
                "work_type": "delivery",
                "title": f"Test packet {packet_id}",
                "objective": "Test objective",
                "scope": {"in": scope_in, "out": ["skills/*/SKILL.md"]},
                "owner": {
                    "identity": "test",
                    "identity_type": "human",
                    "authentication_ref": "gpg:test",
                    "signed_at": "2026-01-01T00:00:00Z",
                },
                "implementor": {
                    "agent_id": "test-droid",
                    "harness": "test",
                    "model": "test",
                    "session_id": "test",
                },
                "reviewer": "user",
                "cleanup_owner": "droid",
                "dependencies": [],
                "locks": [],
                "baseline_refs": [],
                "acceptance_criteria": ["criterion"],
                "validation_plan": [
                    {
                        "id": "VAL001",
                        "kind": "type-check",
                        "skill": "test",
                        "checks": ["check"],
                        "expected": "pass",
                    }
                ],
                "state": "Claimed",
            }
        ),
        encoding="utf-8",
    )


class ClassifyDiffTests(unittest.TestCase):
    """Rule 1: diffs with no .contract-engineering/ paths pass."""

    def test_workflow_only_diff_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _make_packet(project, "CENG-T999-P001", ["scripts/foo.py"])
            changed = [
                ".github/workflows/protocol-validation.yml",
                ".github/workflows/secret-scanning.yml",
            ]
            result = gate.evaluate(project, changed, base_reachable=True)
            self.assertEqual(result.decision, "pass")
            self.assertIn("no .contract-engineering", result.message.lower())

    def test_empty_diff_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _make_packet(project, "CENG-T999-P001", ["scripts/foo.py"])
            result = gate.evaluate(project, [], base_reachable=True)
            self.assertEqual(result.decision, "pass")

    def test_non_records_diff_passes(self):
        """A diff touching only source files and tests, no records."""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _make_packet(project, "CENG-T999-P001", ["scripts/foo.py"])
            changed = ["scripts/foo.py", "tests/test_foo.py", "README.md"]
            result = gate.evaluate(project, changed, base_reachable=True)
            self.assertEqual(result.decision, "pass")


class ForcePushSkipTests(unittest.TestCase):
    """Rule 3: unreachable base SHA warns and skips."""

    def test_unreachable_base_sha_skips(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _make_packet(project, "CENG-T999-P001", ["scripts/foo.py"])
            changed = [".contract-engineering/work-packets/CENG-T999-P001.yaml"]
            result = gate.evaluate(project, changed, base_reachable=False)
            self.assertEqual(result.decision, "pass")
            self.assertIn("force-push", result.message.lower())

    def test_script_with_unreachable_base_exits_zero(self):
        """Regression: the CLI must not crash on an unreachable base SHA.

        A tag move (force-push) in a shallow CI checkout leaves the base
        unreachable.  The old fallback diffed against the full multi-line
        ``git rev-list`` output and crashed before the skip rule could run.
        """
        bogus = "0" * 40
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "enforce_packet_scope.py"),
                "--project-dir",
                str(ROOT),
                "--base-sha",
                bogus,
                "--head-sha",
                "HEAD",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("unreachable", proc.stdout.lower())


class PacketClaimingTests(unittest.TestCase):
    """Rule 2: artifacts claimed by filename, plus normal packet-file claiming."""

    def test_packet_file_plus_claimed_paths_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _make_packet(
                project,
                "CENG-T999-P001",
                [
                    "scripts/foo.py",
                    ".contract-engineering/work-packets/CENG-T999-P001.yaml",
                ],
            )
            changed = [
                "scripts/foo.py",
                ".contract-engineering/work-packets/CENG-T999-P001.yaml",
            ]
            result = gate.evaluate(project, changed, base_reachable=True)
            self.assertEqual(result.decision, "pass")

    def test_unclaimed_path_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _make_packet(
                project,
                "CENG-T999-P001",
                [
                    "scripts/foo.py",
                    ".contract-engineering/work-packets/CENG-T999-P001.yaml",
                ],
            )
            changed = [
                "scripts/foo.py",
                ".contract-engineering/work-packets/CENG-T999-P001.yaml",
                "scripts/unclaimed.py",
            ]
            result = gate.evaluate(project, changed, base_reachable=True)
            self.assertEqual(result.decision, "fail")

    def test_artifact_filename_claims_packet(self):
        """Evidence/handoff/decision files are claimed by packet ID in filename."""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _make_packet(
                project,
                "CENG-T999-P001",
                [
                    "scripts/foo.py",
                    ".contract-engineering/work-packets/CENG-T999-P001.yaml",
                    ".contract-engineering/evidence/CENG-T999-P001-EV001.md",
                    ".contract-engineering/handoffs/CENG-T999-P001-HO001.yaml",
                    ".contract-engineering/decisions/CENG-T999-P001-DEC001.yaml",
                ],
            )
            # Diff has the artifacts but NOT the packet file itself.
            changed = [
                "scripts/foo.py",
                ".contract-engineering/evidence/CENG-T999-P001-EV001.md",
                ".contract-engineering/handoffs/CENG-T999-P001-HO001.yaml",
                ".contract-engineering/decisions/CENG-T999-P001-DEC001.yaml",
            ]
            result = gate.evaluate(project, changed, base_reachable=True)
            self.assertEqual(result.decision, "pass")

    def test_artifact_referencing_missing_packet_fails(self):
        """An artifact whose filename packet ID does not exist must fail."""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _make_packet(
                project,
                "CENG-T999-P001",
                [".contract-engineering/work-packets/CENG-T999-P001.yaml"],
            )
            changed = [
                ".contract-engineering/evidence/CENG-T888-P001-EV001.md",
            ]
            result = gate.evaluate(project, changed, base_reachable=True)
            self.assertEqual(result.decision, "fail")

    def test_records_diff_without_any_claiming_packet_fails(self):
        """A records path that no packet claims must fail."""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _make_packet(
                project,
                "CENG-T999-P001",
                [".contract-engineering/work-packets/CENG-T999-P001.yaml"],
            )
            changed = [
                ".contract-engineering/tracker/index.yaml",
            ]
            result = gate.evaluate(project, changed, base_reachable=True)
            self.assertEqual(result.decision, "fail")


class ProtocolLevelRecordsTests(unittest.TestCase):
    """Protocol-level records (attestation, lock) pass without a claiming packet."""

    def test_release_attestation_only_diff_passes(self):
        """A release attestation push is protocol-level, not packet-scoped."""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / ".contract-engineering").mkdir()
            changed = [
                ".contract-engineering/release-attestation.yaml",
            ]
            result = gate.evaluate(project, changed, base_reachable=True)
            self.assertEqual(result.decision, "pass")

    def test_all_protocol_level_files_pass(self):
        """Every protocol-level file passes without a claiming packet."""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / ".contract-engineering").mkdir()
            changed = [
                ".contract-engineering/release-attestation.yaml",
                ".contract-engineering/release-signing-key.asc",
                ".contract-engineering/protocol.lock.yaml",
                ".contract-engineering/skill-feedback.md",
            ]
            result = gate.evaluate(project, changed, base_reachable=True)
            self.assertEqual(result.decision, "pass")

    def test_protocol_level_plus_unclaimed_records_path_fails(self):
        """A protocol-level file does not excuse other unclaimed records paths."""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _make_packet(
                project,
                "CENG-T999-P001",
                [".contract-engineering/work-packets/CENG-T999-P001.yaml"],
            )
            changed = [
                ".contract-engineering/release-attestation.yaml",
                ".contract-engineering/tracker/index.yaml",
            ]
            result = gate.evaluate(project, changed, base_reachable=True)
            self.assertEqual(result.decision, "fail")


class RealRepoReplayTests(unittest.TestCase):
    """Replay the three real failing diffs that motivated this packet."""

    def test_pr30_workflow_only_diff(self):
        """PR #30: only workflow files changed, no records."""
        changed = [
            ".github/workflows/protocol-validation.yml",
            ".github/workflows/secret-scanning.yml",
        ]
        result = gate.evaluate(ROOT, changed, base_reachable=True)
        self.assertEqual(result.decision, "pass")

    def test_evidence_handoff_push(self):
        """Commit 7664a6a: evidence + handoff for CENG-T023-P001."""
        changed = [
            ".contract-engineering/evidence/CENG-T023-P001-EV001.md",
            ".contract-engineering/handoffs/CENG-T023-P001-HO001.yaml",
        ]
        result = gate.evaluate(ROOT, changed, base_reachable=True)
        self.assertEqual(result.decision, "pass")

    def test_release_attestation_push(self):
        """A release attestation commit changes only protocol-level records."""
        changed = [
            ".contract-engineering/release-attestation.yaml",
        ]
        result = gate.evaluate(ROOT, changed, base_reachable=True)
        self.assertEqual(result.decision, "pass")


if __name__ == "__main__":
    unittest.main()
