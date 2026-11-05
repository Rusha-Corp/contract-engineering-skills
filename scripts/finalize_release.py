#!/usr/bin/env python3
"""Scripted release finalization (CENG-T026-P001).

The protocol lock must never be pinned to a commit that a later rebase can
strand.  This script runs AFTER release content lands on main in final form.
Given the content commit (default HEAD), it:

1. verifies the content commit is an ancestor-or-equal of HEAD;
2. verifies every pinned skill hash (and lock-v2 per-file hash) against the
   content commit's tree;
3. rewrites ``protocol.lock.yaml``'s ``protocol.ref`` and
   ``development.ref`` to the content commit's full SHA;
4. recomputes the attestation's artifact SHA-256 hashes from the content
   commit's tree; sets ``subject.commit``, ``provenance.source_commit``, and
   ``builder_digest``; writes ``attestation_version: 2`` and drops
   ``transparency_ref`` (hosted validation is published in the GitHub
   Release body, not the signed attestation — the run is triggered by the
   tag the attestation lives in and can never be cited from within it);
5. sanity-checks point-in-time timestamps (nothing in the future) and
   refuses to write an attestation that still contains PENDING placeholders.

It then prints the follow-up commands.  The lock and attestation changes
must be committed together as ONE commit whose parent is the content
commit — the only shape both the stable gate (subject = direct parent of
the tag) and the lock verifier (ref ancestor-or-equal of HEAD) accept.

Usage:
    python scripts/finalize_release.py [--project-root PATH] [--content-sha SHA]
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Point-in-time attestation fields: none may lie in the future.  expires_at
# is deliberately excluded — an expiry is supposed to be in the future.
_POINT_IN_TIME_KEYS = frozenset({
    "issued_at", "approved_at", "verified_at", "revocation_checked_at", "signed_at",
})


def _git(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(project), *args], capture_output=True, text=True
    )


def _rev_parse(project: Path, revision: str) -> str:
    result = _git(project, "rev-parse", "--verify", revision)
    if result.returncode != 0:
        raise SystemExit(
            f"cannot resolve {revision!r} to a single object: {result.stderr.strip()}"
        )
    lines = result.stdout.strip().splitlines()
    if len(lines) != 1:
        raise SystemExit(f"revision {revision!r} is ambiguous: {lines}")
    return lines[0]


def _show_bytes(project: Path, sha: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(project), "show", f"{sha}:{path}"], capture_output=True
    )
    if result.returncode != 0:
        raise SystemExit(f"path is missing at content commit {sha[:12]}: {path}")
    return result.stdout


def _find_pending_values(node, path: str = "") -> list[str]:
    """Return dotted paths of every value that is a PENDING placeholder."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(
                _find_pending_values(value, f"{path}.{key}" if path else str(key))
            )
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_find_pending_values(value, f"{path}[{index}]"))
    elif isinstance(node, str) and node.strip().upper().startswith("PENDING"):
        found.append(path)
    return found


def _check_no_future_timestamps(attestation: dict) -> None:
    stack = [(attestation, "")]
    now = datetime.now(timezone.utc)
    while stack:
        node, path = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                child = f"{path}.{key}" if path else str(key)
                if key in _POINT_IN_TIME_KEYS:
                    stamp = str(value).replace("Z", "+00:00")
                    try:
                        parsed = datetime.fromisoformat(stamp)
                    except ValueError as exc:
                        raise SystemExit(
                            f"attestation timestamp {child}={value!r} is invalid"
                        ) from exc
                    if parsed.tzinfo is None:
                        raise SystemExit(
                            f"attestation timestamp {child}={value!r} must include a timezone"
                        )
                    if parsed > now:
                        raise SystemExit(
                            f"attestation timestamp {child}={value!r} is in the future"
                        )
                else:
                    stack.append((value, child))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                stack.append((value, f"{path}[{index}]"))


def _verify_skills(project: Path, sha: str, lock: dict) -> None:
    for name, pin in (lock.get("skills") or {}).items():
        content = _show_bytes(project, sha, f"skills/{name}/SKILL.md")
        actual = hashlib.sha256(content).hexdigest()
        if actual != pin.get("sha256"):
            raise SystemExit(
                f"lock skill hash mismatch at content commit {sha[:12]}: {name} "
                f"(lock pins {pin.get('sha256')}, tree has {actual})"
            )
        for rel_path, expected in (pin.get("files") or {}).items():
            file_bytes = _show_bytes(project, sha, f"skills/{name}/{rel_path}")
            actual_file = hashlib.sha256(file_bytes).hexdigest()
            if actual_file != expected:
                raise SystemExit(
                    f"lock per-file hash mismatch at content commit {sha[:12]}: "
                    f"{name}/{rel_path} (lock pins {expected}, tree has {actual_file})"
                )


def finalize_release(project_root: Path | str = ".", content_sha: str = "HEAD") -> str:
    """Pin the lock and rewrite the attestation for the content commit."""
    project = Path(project_root).resolve()
    ce = project / ".contract-engineering"
    lock_path = ce / "protocol.lock.yaml"
    attestation_path = ce / "release-attestation.yaml"
    for required in (lock_path, attestation_path):
        if not required.is_file():
            raise SystemExit(f"missing protocol record: {required}")

    # Peel the content revision to a commit: an annotated tag name must pin
    # the commit it points to, not the tag object (merge-base and git show
    # peel tags, so anything less would silently write the wrong SHA).
    sha = _rev_parse(project, f"{content_sha}^{{commit}}")
    ancestor = _git(project, "merge-base", "--is-ancestor", sha, "HEAD")
    if ancestor.returncode != 0:
        raise SystemExit(
            f"content commit {sha} is not an ancestor of HEAD; finalize only "
            "after release content lands on main in final form"
        )

    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    _verify_skills(project, sha, lock)

    lock["protocol"]["ref"] = sha
    if isinstance(lock.get("development"), dict) and "ref" in lock["development"]:
        lock["development"]["ref"] = sha
    lock_path.write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")

    attestation = yaml.safe_load(attestation_path.read_text(encoding="utf-8"))
    _check_no_future_timestamps(attestation)

    attestation["attestation_version"] = 2
    verification = attestation.get("verification") or {}
    verification.pop("transparency_ref", None)
    attestation["verification"] = verification
    attestation["subject"]["commit"] = sha
    provenance = attestation.get("provenance") or {}
    provenance["source_commit"] = sha
    provenance["builder_digest"] = f"git-tree:{_rev_parse(project, sha + '^{tree}')}"
    attestation["provenance"] = provenance
    artifacts = attestation["subject"].get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise SystemExit("release attestation lacks artifact entries")
    for artifact in artifacts:
        artifact["sha256"] = hashlib.sha256(
            _show_bytes(project, sha, artifact["path"])
        ).hexdigest()

    pending = _find_pending_values(attestation)
    if pending:
        raise SystemExit(
            f"attestation still contains PENDING placeholders; fill before finalizing: {pending}"
        )
    attestation_path.write_text(
        yaml.safe_dump(attestation, sort_keys=False), encoding="utf-8"
    )

    tag = f"v{attestation['subject'].get('release')}"
    return (
        f"finalized release {tag} for content commit {sha}\n"
        "lock protocol.ref/development.ref and attestation subject, provenance, "
        "and artifact hashes were rewritten in the working tree.\n"
        "next steps:\n"
        "  git add .contract-engineering/protocol.lock.yaml "
        ".contract-engineering/release-attestation.yaml\n"
        f"  git commit -m 'release: {tag} attestation — finalize commit SHA and artifact hashes'\n"
        "  GITHUB_REF_NAME=<tag> GITHUB_SHA=$(git rev-parse HEAD) "
        "python scripts/verify_release_tag.py --tag <tag>\n"
        f"  git tag -s -a {tag} -m 'Release {tag}'\n"
        f"  git push origin main {tag}\n"
        "The lock and attestation changes must land in ONE commit whose parent "
        "is the content commit."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize a protocol release after content lands on main."
    )
    parser.add_argument("--project-root", default=".", type=Path)
    parser.add_argument("--content-sha", default="HEAD")
    args = parser.parse_args()
    print(
        finalize_release(
            project_root=args.project_root, content_sha=args.content_sha
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
