"""GitHub-maintainer release signing and attestation-v3 tests."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from scripts import github_release_signing as grs
from scripts import verify_release_tag as vrt
from tests.test_release_tag import _make_attestation


NOW = datetime(2026, 11, 24, tzinfo=timezone.utc)


def _key(fingerprint: str, **changes):
    key = {
        "key_id": fingerprint[-16:],
        "can_sign": True,
        "revoked": False,
        "expires_at": None,
        "raw_key": "PUBLIC KEY",
        "subkeys": [],
    }
    key.update(changes)
    return key


def _api(username="maintainer", role="maintain", keys=None):
    def call(path: str):
        if path.endswith("/permission"):
            return {"role_name": role, "user": {"login": username}}
        if "gpg_keys" in path:
            return keys if "page=1" in path else []
        raise AssertionError(path)
    return call


class MaintainerAuthorizationTests(unittest.TestCase):
    def test_two_different_maintainer_keys_pass(self):
        for username, fingerprint in (("alice", "A" * 40), ("bob", "B" * 40)):
            with self.subTest(username=username):
                raw = grs.authorize_maintainer(
                    repository="https://github.com/Rusha-Corp/contract-engineering-skills.git",
                    username=username,
                    fingerprint=fingerprint,
                    api_fn=_api(username, keys=[_key(fingerprint)]),
                    now=NOW,
                )
                self.assertEqual(raw, "PUBLIC KEY")

    def test_signing_subkey_matches_primary_raw_key(self):
        fingerprint = "C" * 40
        primary = _key(
            "D" * 40,
            can_sign=False,
            subkeys=[{
                "key_id": fingerprint[-16:],
                "can_sign": True,
                "revoked": False,
                "expires_at": None,
            }],
        )
        raw = grs.authorize_maintainer(
            repository="https://github.com/test/repo",
            username="maintainer",
            fingerprint=fingerprint,
            api_fn=_api(keys=[primary]),
            now=NOW,
        )
        self.assertEqual(raw, "PUBLIC KEY")

    def test_second_key_page_is_bounded_and_supported(self):
        fingerprint = "E" * 40
        filler = [_key(f"{index:040X}") for index in range(100)]
        def api(path: str):
            if path.endswith("/permission"):
                return {"role_name": "admin", "user": {"login": "maintainer"}}
            if "&page=1" in path:
                return filler
            if "&page=2" in path:
                return [_key(fingerprint)]
            return []
        raw = grs.authorize_maintainer(
            repository="https://github.com/test/repo",
            username="maintainer",
            fingerprint=fingerprint,
            api_fn=api,
            now=NOW,
        )
        self.assertEqual(raw, "PUBLIC KEY")

    def test_write_only_role_fails(self):
        with self.assertRaisesRegex(SystemExit, "maintain or admin"):
            grs.authorize_maintainer(
                repository="https://github.com/test/repo",
                username="maintainer",
                fingerprint="A" * 40,
                api_fn=_api(role="write", keys=[_key("A" * 40)]),
                now=NOW,
            )

    def test_permission_identity_mismatch_fails(self):
        with self.assertRaisesRegex(SystemExit, "identity"):
            grs.authorize_maintainer(
                repository="https://github.com/test/repo",
                username="maintainer",
                fingerprint="A" * 40,
                api_fn=_api(username="someone-else", keys=[_key("A" * 40)]),
                now=NOW,
            )

    def test_unregistered_key_fails(self):
        with self.assertRaisesRegex(SystemExit, "no registered"):
            grs.authorize_maintainer(
                repository="https://github.com/test/repo",
                username="maintainer",
                fingerprint="A" * 40,
                api_fn=_api(keys=[]),
                now=NOW,
            )

    def test_revoked_and_expired_keys_fail(self):
        changes = (
            {"revoked": True},
            {"expires_at": "2026-11-23T00:00:00Z"},
            {"can_sign": False},
            {"subkeys": None},
        )
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaisesRegex(SystemExit, "no registered"):
                    grs.authorize_maintainer(
                        repository="https://github.com/test/repo",
                        username="maintainer",
                        fingerprint="A" * 40,
                        api_fn=_api(keys=[_key("A" * 40, **change)]),
                        now=NOW,
                    )

    def test_api_failure_fails_closed(self):
        def fail(path: str):
            raise SystemExit("GitHub authorization query failed")
        with self.assertRaisesRegex(SystemExit, "query failed"):
            grs.authorize_maintainer(
                repository="https://github.com/test/repo",
                username="maintainer",
                fingerprint="A" * 40,
                api_fn=fail,
                now=NOW,
            )

    @patch("scripts.github_release_signing.subprocess.run")
    def test_api_output_bound_fails(self, run):
        run.return_value = MagicMock(returncode=0, stdout="x" * 5_000_001, stderr="")
        with self.assertRaisesRegex(SystemExit, "output bound"):
            grs._github_api("users/maintainer/gpg_keys")


class AttestationV3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        self.ce = self.project / ".contract-engineering"
        self.ce.mkdir()
        (self.project / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        self.attestation_path = self.ce / "release-attestation.yaml"
        self.key_path = self.ce / "release-signing-key.asc"

    def tearDown(self):
        self.tmp.cleanup()

    def _attestation(self, fingerprint="A" * 40, username="maintainer"):
        digest = hashlib.sha256((self.project / "CHANGELOG.md").read_bytes()).hexdigest()
        att = _make_attestation(
            attestation_version=3,
            release="3.2.0",
            auth_ref=f"github:{username}",
            signature_ref=f"gpg:tag:v3.2.0:{fingerprint}",
            artifacts=[{"path": "CHANGELOG.md", "sha256": digest}],
            transparency_ref=None,
        )
        att["publisher"]["identity"] = username
        att["publisher"]["github_key_fingerprint"] = fingerprint
        return att

    def _run(self, att, raw_signature=None, authorizer=None, importer=None):
        self.attestation_path.write_text(yaml.safe_dump(att), encoding="utf-8")
        fingerprint = att["publisher"]["github_key_fingerprint"]
        raw = raw_signature or f"[GNUPG:] VALIDSIG {fingerprint} 2026-11-24"
        return vrt.verify_release_tag(
            tag="v3.2.0",
            tag_commit=att["subject"]["commit"],
            attestation_path=self.attestation_path,
            key_path=self.key_path,
            project_root=self.project,
            git_verify_tag_fn=lambda tag: (raw, 0),
            github_authorizer_fn=authorizer or (lambda **kwargs: "PUBLIC KEY"),
            github_key_import_fn=importer or (lambda homedir, raw_key: None),
        )

    def test_two_maintainer_fingerprints_pass(self):
        for fingerprint in ("A" * 40, "F" * 40):
            with self.subTest(fingerprint=fingerprint):
                self.assertEqual(self._run(self._attestation(fingerprint)), "OK")

    def test_wrong_signature_fingerprint_fails(self):
        with self.assertRaisesRegex(SystemExit, "GitHub publisher key"):
            self._run(
                self._attestation("A" * 40),
                raw_signature=f"[GNUPG:] VALIDSIG {'B' * 40} 2026-11-24",
            )

    def test_signature_reference_mismatch_fails(self):
        att = self._attestation()
        att["publisher"]["signature_ref"] = "gpg:tag:v3.2.0:" + "B" * 40
        with self.assertRaisesRegex(SystemExit, "signature_ref"):
            self._run(att)

    def test_authentication_reference_mismatch_fails(self):
        att = self._attestation()
        att["publisher"]["authentication_ref"] = "github:someone-else"
        with self.assertRaisesRegex(SystemExit, "authentication_ref"):
            self._run(att)

    def test_authorization_failure_blocks_artifact_acceptance(self):
        def denied(**kwargs):
            raise SystemExit("maintain role required")
        with self.assertRaisesRegex(SystemExit, "maintain role"):
            self._run(self._attestation(), authorizer=denied)

    def test_tampered_artifact_still_fails(self):
        att = self._attestation()
        att["subject"]["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(SystemExit, "hash mismatch"):
            self._run(att)

    def test_temporary_keyring_is_removed(self):
        locations = []
        def importer(homedir, raw_key):
            locations.append(homedir)
        self.assertEqual(self._run(self._attestation(), importer=importer), "OK")
        self.assertEqual(len(locations), 1)
        self.assertFalse(locations[0].exists())

    def test_legacy_v2_never_calls_github(self):
        fingerprint = "038022B4EDF5F704B38DF6C7BE1DF7FA3C3BC996"
        digest = hashlib.sha256((self.project / "CHANGELOG.md").read_bytes()).hexdigest()
        att = _make_attestation(
            attestation_version=2,
            release="3.2.0",
            auth_ref=fingerprint,
            signature_ref=f"gpg:tag:v3.2.0:{fingerprint}",
            artifacts=[{"path": "CHANGELOG.md", "sha256": digest}],
            transparency_ref=None,
        )
        self.attestation_path.write_text(yaml.safe_dump(att), encoding="utf-8")
        def unexpected(**kwargs):
            raise AssertionError("GitHub must not be called for legacy attestations")
        result = vrt.verify_release_tag(
            tag="v3.2.0",
            tag_commit=att["subject"]["commit"],
            attestation_path=self.attestation_path,
            key_path=self.key_path,
            project_root=self.project,
            git_verify_tag_fn=lambda tag: (f"[GNUPG:] VALIDSIG {fingerprint}", 0),
            github_authorizer_fn=unexpected,
        )
        self.assertEqual(result, "OK")


if __name__ == "__main__":
    unittest.main()
