#!/usr/bin/env python3
"""Release tag verification guard (CENG-T023-P001).

This script extracts the stable-release-gate logic from the inline Python in
.protocol-validation.yml into a reusable, testable module. Both CI and the
local pre-push hook call it, ensuring the same checks run before and after
publication.

Usage:
    python scripts/verify_release_tag.py [--tag vX.Y.Z] [--project-root PATH]

When --tag is omitted, the script derives the tag from GITHUB_REF_NAME (CI)
or from the most recent annotated tag on HEAD (local pre-push).

Exit code 0 means the release tag is valid; non-zero means a check failed.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import yaml


def parse_valid_signatures(raw: str) -> list[str]:
    """Extract VALIDSIG fingerprints from git verify-tag --raw output."""
    return [
        line.split()[2]
        for line in raw.splitlines()
        if line.startswith("[GNUPG:] VALIDSIG ")
    ]


def _git_verify_tag(tag: str) -> tuple[str, int]:
    """Run git verify-tag --raw and return (output, returncode)."""
    result = subprocess.run(
        ["git", "verify-tag", "--raw", tag],
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr, result.returncode


def verify_release_tag(
    *,
    tag: str,
    tag_commit: str,
    attestation_path: Path,
    key_path: Path,
    project_root: Path,
    git_verify_tag_fn: Optional[Callable[[str], tuple[str, int]]] = None,
) -> str:
    """Verify a release tag against its attestation.

    Returns "OK" on success, raises SystemExit on failure.
    """
    if git_verify_tag_fn is None:
        git_verify_tag_fn = _git_verify_tag

    # --- Load attestation ---
    if not attestation_path.is_file():
        raise SystemExit("release attestation is missing")
    attestation = yaml.safe_load(attestation_path.read_text())

    # --- Required top-level fields ---
    required = ("subject", "publisher", "provenance", "review", "verification", "revocation")
    missing = [f for f in required if not attestation.get(f)]
    if missing:
        raise SystemExit(f"release attestation is incomplete: {missing}")

    # --- Independent approval / exception ---
    review = attestation["review"]
    if not review.get("independent_approver"):
        exception_ref = review.get("exception_ref")
        if not exception_ref:
            raise SystemExit("release attestation lacks independent approval or an exception")
        exception_path = attestation_path.parent / "decisions" / f"{exception_ref}.yaml"
        if not exception_path.is_file():
            raise SystemExit(f"release exception is missing: {exception_path}")
        exception = yaml.safe_load(exception_path.read_text())
        required_exception = (
            "proposal", "controls", "review_owner", "review_at",
            "success_measure", "status", "approved_by", "approved_at",
            "expires_at", "rollback_ref",
        )
        missing_ex = [f for f in required_exception if not exception.get(f)]
        if missing_ex or exception.get("status") != "approved":
            raise SystemExit(f"release exception is incomplete or not approved: {exception_ref}")
        try:
            approved_at = datetime.fromisoformat(str(exception["approved_at"]).replace("Z", "+00:00"))
            expires_at = datetime.fromisoformat(str(exception["expires_at"]).replace("Z", "+00:00"))
            review_at = datetime.fromisoformat(str(exception["review_at"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise SystemExit(f"release exception timestamps are invalid: {exception_ref}") from exc
        now = datetime.now(timezone.utc)
        if approved_at.tzinfo is None or expires_at.tzinfo is None or review_at.tzinfo is None:
            raise SystemExit(f"release exception timestamps must include timezone: {exception_ref}")
        if expires_at <= approved_at or expires_at <= now or review_at > expires_at:
            raise SystemExit(f"release exception is expired or has invalid review window: {exception_ref}")
        if not re.fullmatch(r"[0-9a-f]{40}", str(exception["rollback_ref"])):
            raise SystemExit(f"release exception rollback_ref must be an immutable commit: {exception_ref}")

    # --- Verification result ---
    if attestation["verification"].get("result") != "pass":
        raise SystemExit("release attestation is not verified")

    # --- Revocation status ---
    if attestation["revocation"].get("status") != "active":
        raise SystemExit("release attestation is revoked or unknown")

    # --- Tag format ---
    if not tag.startswith("v"):
        raise SystemExit("stable release gate requires a version tag")
    if "-" in tag.removeprefix("v"):
        raise SystemExit(f"tag {tag} is a development tag, not a stable release")

    # --- Release name match ---
    expected_release = tag.removeprefix("v")
    if attestation["subject"].get("release") != expected_release:
        raise SystemExit(
            f"tag {tag} does not match attestation release "
            f"{attestation['subject'].get('release')}"
        )

    # --- Subject commit ---
    subject_commit = attestation["subject"].get("commit")
    if not subject_commit:
        raise SystemExit("release attestation lacks subject commit")

    # --- Commit relationship (single or two-commit model) ---
    if tag_commit and tag_commit != subject_commit:
        parent = subprocess.run(
            ["git", "rev-parse", "HEAD^"],
            capture_output=True, text=True,
        ).stdout.strip()
        if not parent or parent != subject_commit:
            raise SystemExit(
                f"tag commit {tag_commit} does not match attestation "
                f"subject commit {subject_commit} and subject is not "
                f"the direct parent of the tag"
            )

    # --- Publisher fields ---
    publisher = attestation.get("publisher", {})
    if not publisher.get("identity") or not publisher.get("signing_system"):
        raise SystemExit("release attestation lacks publisher identity or signing system")
    if not publisher.get("signature_ref"):
        raise SystemExit("release attestation lacks publisher signature reference")

    # --- Tag signature verification ---
    status, rc = git_verify_tag_fn(tag)
    if rc != 0:
        raise SystemExit("release tag signature verification failed")
    valid_signatures = parse_valid_signatures(status)
    if len(valid_signatures) != 1:
        raise SystemExit("release tag must have exactly one valid signature")
    publisher_key = publisher.get("authentication_ref")
    if not publisher_key or valid_signatures[0] != publisher_key:
        raise SystemExit("release tag signature does not match publisher authentication_ref")

    # --- Provenance ---
    provenance = attestation.get("provenance", {})
    if not provenance.get("source_commit"):
        raise SystemExit("release attestation lacks provenance source commit")
    if provenance["source_commit"] != subject_commit:
        raise SystemExit(
            f"provenance source_commit {provenance['source_commit']} "
            f"does not match subject commit {subject_commit}"
        )

    # --- Artifact hashes ---
    artifacts = attestation["subject"].get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise SystemExit("release attestation lacks artifact hashes")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise SystemExit("release artifact entry must be a mapping")
        artifact_path = artifact.get("path")
        expected_hash = artifact.get("sha256")
        if (
            not isinstance(artifact_path, str)
            or not isinstance(expected_hash, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        ):
            raise SystemExit("release artifact entry has invalid path or hash")
        path = Path(artifact_path)
        if path.is_absolute() or ".." in path.parts:
            raise SystemExit(f"release artifact path is unsafe or missing: {path}")
        resolved = project_root / path
        if not resolved.is_file():
            raise SystemExit(f"release artifact path is unsafe or missing: {path}")
        actual_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise SystemExit(f"release artifact hash mismatch: {path}")

    return "OK"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a release tag against its attestation.")
    parser.add_argument("--tag", help="Tag name (e.g. v3.0.1). Defaults to GITHUB_REF_NAME.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    ce = project_root / ".contract-engineering"
    attestation_path = ce / "release-attestation.yaml"
    key_path = ce / "release-signing-key.asc"

    tag = args.tag or os.environ.get("GITHUB_REF_NAME", "")
    if not tag:
        raise SystemExit("no tag specified and GITHUB_REF_NAME is unset")

    tag_commit = os.environ.get("GITHUB_SHA", "")

    # Import the signing key into the local keyring if present.
    if key_path.is_file():
        subprocess.run(
            ["gpg", "--batch", "--no-tty", "--import", str(key_path)],
            capture_output=True,
        )

    result = verify_release_tag(
        tag=tag,
        tag_commit=tag_commit,
        attestation_path=attestation_path,
        key_path=key_path,
        project_root=project_root,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
