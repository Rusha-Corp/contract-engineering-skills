"""Tests for scripts/finalize_release.py.

Finalize is the scripted release-finalization step that fixes lock ref
drift: the lock is only pinned after release content lands on main in
final form.  Given the content commit (default HEAD), it rewrites
protocol.lock.yaml's pinned refs and the attestation's subject, provenance,
and artifact hashes, producing the single commit shape whose parent is the
content commit — the only shape both the stable gate and the lock verifier
accept.
"""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

SPEC = importlib.util.spec_from_file_location(
    "finalize_release", ROOT / "scripts" / "finalize_release.py"
)
assert SPEC and SPEC.loader
finalize = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(finalize)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _init_repo(directory: Path) -> Path:
    subprocess.run(
        ["git", "-C", str(directory), "init", "-q"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(directory), "config", "user.email", "t@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(directory), "config", "user.name", "Test"],
        check=True,
    )
    return directory


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


class FixtureRepo:
    """A minimal protocol repo: lock, attestation, skills, changelog."""

    def __init__(self, base: Path):
        self.repo = _init_repo(base)
        self.ce = base / ".contract-engineering"
        self.ce.mkdir()
        (self.ce / "work-packets").mkdir()

    def write(self, path: str, content: str) -> None:
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def blob(self, path: str) -> bytes:
        return (self.repo / path).read_bytes()


LOCK_TEMPLATE = """\
lock_version: 2
protocol:
  repository: https://github.com/test/repo.git
  ref: {old_ref}
  release: 3.1.0
skills:
  demo-skill:
    version: 1.0.0
    sha256: {skill_hash}
    files:
      SKILL.md: {skill_hash}
      references/guide.md: {guide_hash}
project:
  protocol_root: .contract-engineering
development:
  status: released
  ref: {old_ref}
  based_on_release: 3.1.0
"""


ATTESTATION_TEMPLATE = """\
attestation_version: 1
attestation_id: TEST-ATT001
issued_at: '2026-11-05T09:00:00Z'
expires_at: '2028-11-04T00:00:00Z'
subject:
  repository: https://github.com/test/repo.git
  commit: {old_subject}
  release: 3.2.0
  artifacts:
  - path: CHANGELOG.md
    sha256: 0000000000000000000000000000000000000000000000000000000000000000
publisher:
  identity: Test
  identity_type: human
  authentication_ref: 038022B4EDF5F704B38DF6C7BE1DF7FA3C3BC996
  workflow: test
  signing_system: gpg
  signature_ref: gpg:tag:v3.2.0:038022B4EDF5F704B38DF6C7BE1DF7FA3C3BC996
provenance:
  builder: test
  builder_digest: git-tree:0000000000000000000000000000000000000000
  source_repository: https://github.com/test/repo.git
  source_commit: {old_subject}
  dependencies: []
  reproducible: true
review:
  author: droid
  independent_approver: Test
  approval_ref: TEST-APPROVAL
  approved_at: '2026-11-05T09:00:00Z'
verification:
  verified_at: '2026-11-05T09:00:00Z'
  verifier: droid
  result: pass
  transparency_ref: PENDING_HOSTED_VALIDATION
  revocation_checked_at: '2026-11-05T09:00:00Z'
revocation:
  status: active
  revocation_ref: null
  rollback_ref: 1111111111111111111111111111111111111111
"""


def _make_fixture(base: Path) -> FixtureRepo:
    fx = FixtureRepo(base)
    fx.write("skills/demo-skill/SKILL.md", "# demo\n")
    fx.write("skills/demo-skill/references/guide.md", "# guide\n")
    fx.write("CHANGELOG.md", "# Changelog\n\n## 3.2.0\n")
    skill_hash = hashlib.sha256(fx.blob("skills/demo-skill/SKILL.md")).hexdigest()
    guide_hash = hashlib.sha256(
        fx.blob("skills/demo-skill/references/guide.md")
    ).hexdigest()
    old_ref = _commit(fx.repo, "base release v3.1.0")
    fx.write(
        ".contract-engineering/protocol.lock.yaml",
        LOCK_TEMPLATE.format(
            old_ref=old_ref, skill_hash=skill_hash, guide_hash=guide_hash
        ),
    )
    fx.write(
        ".contract-engineering/release-attestation.yaml",
        ATTESTATION_TEMPLATE.format(old_subject=old_ref),
    )
    fx.write(
        ".contract-engineering/work-packets/TEST-P001.yaml",
        "packet_id: TEST-P001\nstate: Handoff\n",
    )
    content_sha = _commit(fx.repo, "release content v3.2.0")
    return fx, content_sha


class FinalizeReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        made = _make_fixture(self.base)
        self.fx = made[0]
        self.content_sha = made[1]

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, content_sha=None):
        return finalize.finalize_release(
            project_root=self.base,
            content_sha=content_sha or self.content_sha,
        )

    def _lock(self) -> dict:
        return yaml.safe_load(
            (self.ce_path("protocol.lock.yaml")).read_text(encoding="utf-8")
        )

    def _attestation(self) -> dict:
        return yaml.safe_load(
            (self.ce_path("release-attestation.yaml")).read_text(encoding="utf-8")
        )

    def ce_path(self, name: str) -> Path:
        return self.base / ".contract-engineering" / name

    def test_pins_lock_refs_to_content_commit(self):
        self._run()
        lock = self._lock()
        self.assertEqual(lock["protocol"]["ref"], self.content_sha)
        self.assertEqual(lock["development"]["ref"], self.content_sha)

    def test_rewrites_attestation_subject_provenance_and_hashes(self):
        self._run()
        att = self._attestation()
        self.assertEqual(att["subject"]["commit"], self.content_sha)
        self.assertEqual(att["provenance"]["source_commit"], self.content_sha)
        content_tree = _git(self.fx.repo, "rev-parse", f"{self.content_sha}^{{tree}}")
        self.assertEqual(att["provenance"]["builder_digest"], f"git-tree:{content_tree}")
        changelog_hash = hashlib.sha256(
            subprocess.check_output(
                ["git", "-C", str(self.base), "show", f"{self.content_sha}:CHANGELOG.md"]
            )
        ).hexdigest()
        artifacts = {a["path"]: a["sha256"] for a in att["subject"]["artifacts"]}
        self.assertEqual(artifacts["CHANGELOG.md"], changelog_hash)

    def test_writes_version_two_without_transparency_ref(self):
        self._run()
        att = self._attestation()
        self.assertEqual(att["attestation_version"], 2)
        self.assertNotIn("transparency_ref", att["verification"])

    def test_fails_when_content_commit_is_not_ancestor_of_head(self):
        # A side commit that exists in the repo but is a descendant of HEAD,
        # not an ancestor: finalizing against it must fail.
        _git(self.fx.repo, "checkout", "-q", "-b", "side")
        self.fx.write("SIDE.md", "side branch only\n")
        side_sha = _commit(self.fx.repo, "side branch commit")
        _git(self.fx.repo, "checkout", "-q", "-")
        with self.assertRaises(SystemExit) as ctx:
            self._run(content_sha=side_sha)
        self.assertIn("ancestor", str(ctx.exception))

    def test_fails_on_skill_hash_mismatch_at_content_commit(self):
        lock = self._lock()
        lock["skills"]["demo-skill"]["sha256"] = "f" * 64
        lock["skills"]["demo-skill"]["files"]["SKILL.md"] = "f" * 64
        self.ce_path("protocol.lock.yaml").write_text(
            yaml.safe_dump(lock), encoding="utf-8"
        )
        with self.assertRaises(SystemExit) as ctx:
            self._run()
        self.assertIn("hash", str(ctx.exception).lower())

    def test_fails_on_future_timestamps(self):
        att = self._attestation()
        att["issued_at"] = "2030-01-01T00:00:00Z"
        self.ce_path("release-attestation.yaml").write_text(
            yaml.safe_dump(att), encoding="utf-8"
        )
        with self.assertRaises(SystemExit) as ctx:
            self._run()
        self.assertIn("future", str(ctx.exception).lower())

    def test_content_sha_tag_name_pins_commit_not_tag_object(self):
        # Regression: an annotated tag name must pin the commit it points to,
        # not the tag object SHA.  merge-base and git show peel tags, so the
        # old code silently wrote the tag object SHA into the lock refs and
        # attestation subject; the stable gate then failed downstream with a
        # confusing two-commit-model error.
        _git(
            self.fx.repo,
            "tag",
            "-a",
            "v-content",
            "-m",
            "content tag",
            self.content_sha,
        )
        self._run(content_sha="v-content")
        lock = self._lock()
        self.assertEqual(lock["protocol"]["ref"], self.content_sha)
        att = self._attestation()
        self.assertEqual(att["subject"]["commit"], self.content_sha)

    def test_prints_followup_commands(self):
        summary = self._run()
        self.assertIn("git commit", summary)
        self.assertIn("git tag", summary)
        self.assertIn("verify_release_tag.py", summary)


if __name__ == "__main__":
    unittest.main()
