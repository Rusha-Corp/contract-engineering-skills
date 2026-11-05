"""Protocol lock validation: ref, release, skill pins, project root."""

from __future__ import annotations

from pathlib import Path

from .constants import BASE_REVISION, SHA256
from .loaders import fail, load_yaml


def validate_project_lock(root: Path) -> None:
    lock_path = root / "protocol.lock.yaml"
    lock = load_yaml(lock_path)
    if not isinstance(lock, dict) or lock.get("lock_version") != 1:
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
    if not lock.get("project", {}).get("protocol_root"):
        fail(f"{lock_path}: project.protocol_root is required")
