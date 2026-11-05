"""Tests for the release tag verification guard (CENG-T023-P001).

The guard extracts the stable-release-gate logic from the inline workflow
Python into a reusable script. These tests cover the signature, publisher
key, release name, commit relationship, and artifact hash checks using a
temporary repository and controlled inputs.
"""
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_release_tag", ROOT / "scripts/verify_release_tag.py"
)
assert SPEC and SPEC.loader
vrt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vrt)


def _make_attestation(
    *,
    release="3.0.1",
    commit="a" * 40,
    auth_ref="038022B4EDF5F704B38DF6C7BE1DF7FA3C3BC996",
    signature_ref="gpg:tag:v3.0.1:038022B4EDF5F704B38DF6C7BE1DF7FA3C3BC996",
    artifacts=None,
    result="pass",
    revocation_status="active",
    independent_approver="user",
):
    if artifacts is None:
        artifacts = [{"path": "CHANGELOG.md", "sha256": "b" * 64}]
    return {
        "attestation_version": 1,
        "subject": {
            "repository": "https://github.com/test/repo.git",
            "commit": commit,
            "release": release,
            "artifacts": artifacts,
        },
        "publisher": {
            "identity": "Emmanuel",
            "identity_type": "human",
            "authentication_ref": auth_ref,
            "workflow": "test",
            "signing_system": "gpg",
            "signature_ref": signature_ref,
        },
        "provenance": {
            "builder": "test",
            "builder_digest": "test",
            "source_repository": "https://github.com/test/repo.git",
            "source_commit": commit,
            "dependencies": [],
            "reproducible": True,
        },
        "review": {
            "author": "droid",
            "independent_approver": independent_approver,
            "approval_ref": "TEST-APPROVAL",
            "approved_at": "2026-11-05T12:00:00Z",
        },
        "verification": {
            "verified_at": "2026-11-05T12:00:00Z",
            "verifier": "droid",
            "result": result,
            "transparency_ref": "test",
            "revocation_checked_at": "2026-11-05T12:00:00Z",
        },
        "revocation": {
            "status": revocation_status,
            "revocation_ref": None,
            "rollback_ref": "c" * 40,
        },
    }


class ParseValidSigsTests(unittest.TestCase):
    """Unit tests for VALIDSIG parsing from git verify-tag --raw output."""

    def test_single_valid_sig(self):
        raw = "[GNUPG:] VALIDSIG 038022B4EDF5F704B38DF6C7BE1DF7FA3C3BC996 2026-11-05\n"
        sigs = vrt.parse_valid_signatures(raw)
        self.assertEqual(sigs, ["038022B4EDF5F704B38DF6C7BE1DF7FA3C3BC996"])

    def test_no_valid_sig(self):
        raw = "[GNUPG:] GOODSIG 038022B4EDF5F704B38DF6C7BE1DF7FA3C3BC996\n"
        sigs = vrt.parse_valid_signatures(raw)
        self.assertEqual(sigs, [])

    def test_multiple_valid_sigs(self):
        raw = (
            "[GNUPG:] VALIDSIG AAAA BBBB\n"
            "[GNUPG:] VALIDSIG CCCC DDDD\n"
        )
        sigs = vrt.parse_valid_signatures(raw)
        self.assertEqual(len(sigs), 2)


class VerifyReleaseTagTests(unittest.TestCase):
    """Integration tests using a temp project with mocked git verify-tag."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        self.ce = self.project / ".contract-engineering"
        self.ce.mkdir()
        (self.project / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        self.attestation_path = self.ce / "release-attestation.yaml"
        self.key_path = self.ce / "release-signing-key.asc"
        self.key_path.write_text("dummy key", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_attestation(self, attestation):
        self.attestation_path.write_text(
            yaml.safe_dump(attestation), encoding="utf-8"
        )

    def _run(self, tag="v3.0.1", tag_commit=None, verify_output="", verify_rc=0):
        if tag_commit is None:
            tag_commit = "a" * 40  # matches _make_attestation default subject commit
        return vrt.verify_release_tag(
            tag=tag,
            tag_commit=tag_commit,
            attestation_path=self.attestation_path,
            key_path=self.key_path,
            project_root=self.project,
            git_verify_tag_fn=lambda t: (verify_output, verify_rc),
        )

    def test_valid_passes(self):
        commit = "a" * 40
        import hashlib
        real_hash = hashlib.sha256(
            (self.project / "CHANGELOG.md").read_bytes()
        ).hexdigest()
        att = _make_attestation(
            commit=commit,
            artifacts=[{"path": "CHANGELOG.md", "sha256": real_hash}],
        )
        self._write_attestation(att)
        # tag_commit == subject commit (single-commit model)
        raw = f"[GNUPG:] VALIDSIG {att['publisher']['authentication_ref']} 2026-11-05"
        result = self._run(tag_commit=commit, verify_output=raw, verify_rc=0)
        self.assertTrue(result.startswith("OK") or result == "OK")

    def test_unsigned_tag_fails(self):
        att = _make_attestation()
        self._write_attestation(att)
        with self.assertRaises(SystemExit) as ctx:
            self._run(verify_output="", verify_rc=1)
        self.assertIn("signature verification failed", str(ctx.exception))

    def test_wrong_fingerprint_fails(self):
        att = _make_attestation()
        self._write_attestation(att)
        raw = "[GNUPG:] VALIDSIG DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF 2026-11-05"
        with self.assertRaises(SystemExit) as ctx:
            self._run(verify_output=raw, verify_rc=0)
        self.assertIn("does not match publisher", str(ctx.exception))

    def test_no_valid_signature_fails(self):
        att = _make_attestation()
        self._write_attestation(att)
        raw = "[GNUPG:] GOODSIG 038022B4EDF5F704B38DF6C7BE1DF7FA3C3BC996"
        with self.assertRaises(SystemExit) as ctx:
            self._run(verify_output=raw, verify_rc=0)
        self.assertIn("exactly one valid signature", str(ctx.exception))

    def test_release_mismatch_fails(self):
        att = _make_attestation(release="3.0.0")
        self._write_attestation(att)
        raw = f"[GNUPG:] VALIDSIG {att['publisher']['authentication_ref']} 2026-11-05"
        with self.assertRaises(SystemExit) as ctx:
            self._run(tag="v3.0.1", verify_output=raw, verify_rc=0)
        self.assertIn("does not match attestation release", str(ctx.exception))

    def test_development_tag_fails(self):
        att = _make_attestation(release="3.0.1-dev")
        self._write_attestation(att)
        with self.assertRaises(SystemExit) as ctx:
            self._run(tag="v3.0.1-dev")
        self.assertIn("development tag", str(ctx.exception))

    def test_revoked_attestation_fails(self):
        att = _make_attestation(revocation_status="revoked")
        self._write_attestation(att)
        with self.assertRaises(SystemExit) as ctx:
            self._run()
        self.assertIn("revoked", str(ctx.exception))

    def test_unverified_attestation_fails(self):
        att = _make_attestation(result="fail")
        self._write_attestation(att)
        with self.assertRaises(SystemExit) as ctx:
            self._run()
        self.assertIn("not verified", str(ctx.exception))

    def test_artifact_hash_mismatch_fails(self):
        att = _make_attestation(
            artifacts=[{"path": "CHANGELOG.md", "sha256": "0" * 64}]
        )
        self._write_attestation(att)
        raw = f"[GNUPG:] VALIDSIG {att['publisher']['authentication_ref']} 2026-11-05"
        with self.assertRaises(SystemExit) as ctx:
            self._run(verify_output=raw, verify_rc=0)
        self.assertIn("hash mismatch", str(ctx.exception))

    def test_missing_artifact_fails(self):
        att = _make_attestation(
            artifacts=[{"path": "NONEXISTENT.md", "sha256": "b" * 64}]
        )
        self._write_attestation(att)
        raw = f"[GNUPG:] VALIDSIG {att['publisher']['authentication_ref']} 2026-11-05"
        with self.assertRaises(SystemExit) as ctx:
            self._run(verify_output=raw, verify_rc=0)
        self.assertIn("unsafe or missing", str(ctx.exception))

    def test_two_commit_model_passes(self):
        subject_commit = "a" * 40
        import hashlib
        real_hash = hashlib.sha256(
            (self.project / "CHANGELOG.md").read_bytes()
        ).hexdigest()
        att = _make_attestation(
            commit=subject_commit,
            artifacts=[{"path": "CHANGELOG.md", "sha256": real_hash}],
        )
        self._write_attestation(att)
        tag_commit = "e" * 40
        raw = f"[GNUPG:] VALIDSIG {att['publisher']['authentication_ref']} 2026-11-05"
        # Mock git rev-parse HEAD^ to return subject_commit
        with patch("scripts.verify_release_tag.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=subject_commit + "\n", returncode=0)
            result = vrt.verify_release_tag(
                tag="v3.0.1",
                tag_commit=tag_commit,
                attestation_path=self.attestation_path,
                key_path=self.key_path,
                project_root=self.project,
                git_verify_tag_fn=lambda t: (raw, 0),
            )
        self.assertTrue(result == "OK" or result.startswith("OK"))

    def test_two_commit_model_wrong_parent_fails(self):
        subject_commit = "a" * 40
        att = _make_attestation(commit=subject_commit)
        self._write_attestation(att)
        tag_commit = "e" * 40
        raw = f"[GNUPG:] VALIDSIG {att['publisher']['authentication_ref']} 2026-11-05"
        with patch("scripts.verify_release_tag.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="f" * 40 + "\n", returncode=0)
            with self.assertRaises(SystemExit) as ctx:
                vrt.verify_release_tag(
                    tag="v3.0.1",
                    tag_commit=tag_commit,
                    attestation_path=self.attestation_path,
                    key_path=self.key_path,
                    project_root=self.project,
                    git_verify_tag_fn=lambda t: (raw, 0),
                )
        self.assertIn("direct parent", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
