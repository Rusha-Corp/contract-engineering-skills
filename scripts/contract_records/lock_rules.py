"""Protocol lock validation: ref, release, skill pins, project root.

Supports lock_version 1 (SKILL.md-only hashing) and lock_version 2
(per-file hashing with a files map for each skill folder).
"""

from __future__ import annotations

from pathlib import Path

from .constants import BASE_REVISION, SHA256
from .loaders import fail, load_yaml


def validate_project_lock(root: Path) -> None:
    lock_path = root / "protocol.lock.yaml"
    lock = load_yaml(lock_path)
    if not isinstance(lock, dict):
        fail(f"{lock_path}: unsupported lock schema")
    version = lock.get("lock_version")
    if version not in (1, 2):
        fail(f"{lock_path}: unsupported lock schema")
    protocol = lock.get("protocol", {})
    if not BASE_REVISION.fullmatch(str(protocol.get("ref", ""))):
        fail(f"{lock_path}: protocol.ref must be an immutable commit SHA")
    if not protocol.get("repository") or not protocol.get("release"):
        fail(f"{lock_path}: protocol repository and release are required")
    skills = lock.get("skills", {})
    required = {
        "phased-engineering-execution",
        "cleanup-protocol",
        "project-lifecycle",
        "skill-evolution",
        "coding-principles",
        "security-assurance",
    }
    if set(skills) != required:
        fail(f"{lock_path}: lock must contain exactly the governed skills")
    for name, pin in skills.items():
        if not pin.get("version") or not SHA256.fullmatch(str(pin.get("sha256", ""))):
            fail(f"{lock_path}: invalid pin for {name}")
        # lock_version 2 adds optional per-file hashing.
        if version == 2:
            files = pin.get("files")
            if files is not None:
                if not isinstance(files, dict):
                    fail(f"{lock_path}: invalid files map for {name}")
                for file_path, file_hash in files.items():
                    if not SHA256.fullmatch(str(file_hash)):
                        fail(f"{lock_path}: invalid file hash for {name}/{file_path}")
    if not lock.get("project", {}).get("protocol_root"):
        fail(f"{lock_path}: project.protocol_root is required")
