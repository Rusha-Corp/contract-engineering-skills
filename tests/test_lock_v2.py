"""Tests for lock v2 per-file hashing of skill folders."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCRIPT = ROOT / "scripts" / "validate-contract-records.py"
SPEC = importlib.util.spec_from_file_location("validate_contract_records_lock_v2", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class LockVersion1Tests(unittest.TestCase):
    """lock_version 1 is still accepted (SKILL.md-only hashing)."""

    def test_v1_lock_with_skill_sha256_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / ".contract-engineering"
            root.mkdir()
            (root / "protocol.lock.yaml").write_text(
                "lock_version: 1\n"
                "protocol:\n"
                "  repository: https://example.com/repo.git\n"
                "  ref: \"%s\"\n"
                "  release: 1.0.0\n"
                "skills:\n"
                "  phased-engineering-execution:\n"
                "    version: 1.0.0\n"
                "    sha256: %s\n"
                "  cleanup-protocol:\n"
                "    version: 1.0.0\n"
                "    sha256: %s\n"
                "  project-lifecycle:\n"
                "    version: 1.0.0\n"
                "    sha256: %s\n"
                "  skill-evolution:\n"
                "    version: 1.0.0\n"
                "    sha256: %s\n"
                "  coding-principles:\n"
                "    version: 1.0.0\n"
                "    sha256: %s\n"
                "  security-assurance:\n"
                "    version: 1.0.0\n"
                "    sha256: %s\n"
                "project:\n"
                "  protocol_root: .contract-engineering\n"
                % (
                    "0" * 40,
                    "a" * 64,
                    "b" * 64,
                    "c" * 64,
                    "d" * 64,
                    "e" * 64,
                    "f" * 64,
                ),
                encoding="utf-8",
            )
            validator.validate_project_lock(root)

    def test_v1_lock_rejects_unsupported_version(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / ".contract-engineering"
            root.mkdir()
            (root / "protocol.lock.yaml").write_text(
                "lock_version: 99\nprotocol:\n  repository: x\n  ref: \"%s\"\n  release: x\n"
                "skills: {}\nproject:\n  protocol_root: .ce\n" % ("0" * 40),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                validator.validate_project_lock(root)
            self.assertIn("unsupported lock schema", str(ctx.exception))


class LockVersion2Tests(unittest.TestCase):
    """lock_version 2 adds per-file hashing with backward compatibility."""

    def test_v2_accepts_files_map(self):
        """v2 lock with a files map for each skill should pass validation."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / ".contract-engineering"
            root.mkdir()
            skills_yaml = "skills:\n"
            for name in [
                "phased-engineering-execution",
                "cleanup-protocol",
                "project-lifecycle",
                "skill-evolution",
                "coding-principles",
                "security-assurance",
            ]:
                skills_yaml += (
                    f"  {name}:\n"
                    f"    version: 1.0.0\n"
                    f"    sha256: {'a' * 64}\n"
                    f"    files:\n"
                    f"      SKILL.md: {'a' * 64}\n"
                )
            (root / "protocol.lock.yaml").write_text(
                "lock_version: 2\n"
                "protocol:\n"
                "  repository: https://example.com/repo.git\n"
                "  ref: \"%s\"\n"
                "  release: 1.0.0\n"
                "%s"
                "project:\n"
                "  protocol_root: .contract-engineering\n"
                % ("0" * 40, skills_yaml),
                encoding="utf-8",
            )
            validator.validate_project_lock(root)

    def test_v2_without_files_map_still_requires_sha256(self):
        """v2 lock without files map should still validate sha256 for SKILL.md."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / ".contract-engineering"
            root.mkdir()
            skills_yaml = "skills:\n"
            for name in [
                "phased-engineering-execution",
                "cleanup-protocol",
                "project-lifecycle",
                "skill-evolution",
                "coding-principles",
                "security-assurance",
            ]:
                skills_yaml += (
                    f"  {name}:\n"
                    f"    version: 1.0.0\n"
                    f"    sha256: {'a' * 64}\n"
                )
            (root / "protocol.lock.yaml").write_text(
                "lock_version: 2\n"
                "protocol:\n"
                "  repository: https://example.com/repo.git\n"
                "  ref: \"%s\"\n"
                "  release: 1.0.0\n"
                "%s"
                "project:\n"
                "  protocol_root: .contract-engineering\n"
                % ("0" * 40, skills_yaml),
                encoding="utf-8",
            )
            validator.validate_project_lock(root)

    def test_v2_rejects_invalid_file_hash(self):
        """v2 lock with a files map entry that is not a valid sha256 should fail."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / ".contract-engineering"
            root.mkdir()
            skills_yaml = "skills:\n"
            for name in [
                "phased-engineering-execution",
                "cleanup-protocol",
                "project-lifecycle",
                "skill-evolution",
                "coding-principles",
                "security-assurance",
            ]:
                skills_yaml += (
                    f"  {name}:\n"
                    f"    version: 1.0.0\n"
                    f"    sha256: {'a' * 64}\n"
                )
            # Add an invalid files entry to the first skill
            skills_yaml = skills_yaml.replace(
                "  phased-engineering-execution:\n    version: 1.0.0\n    sha256: " + "a" * 64 + "\n",
                "  phased-engineering-execution:\n    version: 1.0.0\n    sha256: " + "a" * 64 + "\n"
                "    files:\n      SKILL.md: not-a-hash\n",
            )
            (root / "protocol.lock.yaml").write_text(
                "lock_version: 2\n"
                "protocol:\n"
                "  repository: https://example.com/repo.git\n"
                "  ref: \"%s\"\n"
                "  release: 1.0.0\n"
                "%s"
                "project:\n"
                "  protocol_root: .contract-engineering\n"
                % ("0" * 40, skills_yaml),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                validator.validate_project_lock(root)
            self.assertIn("invalid file hash", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
