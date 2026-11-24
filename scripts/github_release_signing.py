#!/usr/bin/env python3
"""Authorize a release signer through GitHub role and public-key evidence."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from typing import Any, Callable


_API_TIMEOUT_SECONDS = 20
_API_MAX_OUTPUT_BYTES = 5_000_000
_API_MAX_PAGES = 10
_ALLOWED_ROLES = {"maintain", "admin"}


def _github_api(path: str) -> Any:
    """Read one bounded public GitHub API response through the authenticated CLI."""
    try:
        result = subprocess.run(
            ["gh", "api", "--hostname", "github.com", path],
            capture_output=True,
            text=True,
            timeout=_API_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemExit("GitHub authorization query failed") from exc
    if result.returncode != 0:
        raise SystemExit("GitHub authorization query failed")
    if len(result.stdout.encode("utf-8")) > _API_MAX_OUTPUT_BYTES:
        raise SystemExit("GitHub authorization response exceeded its output bound")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("GitHub authorization response was not valid JSON") from exc


def _repository_owner_name(repository: str) -> tuple[str, str]:
    if not isinstance(repository, str):
        raise SystemExit("release subject repository must be a canonical GitHub HTTPS URL")
    match = re.fullmatch(
        r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?",
        repository,
    )
    if not match:
        raise SystemExit("release subject repository must be a canonical GitHub HTTPS URL")
    return match.group(1), match.group(2)


def _unexpired(value: Any, now: datetime) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return expiry.tzinfo is not None and expiry.astimezone(timezone.utc) > now


def _select_raw_key(keys: list[Any], fingerprint: str, now: datetime) -> str:
    suffix = fingerprint[-16:]
    for key in keys:
        if not isinstance(key, dict) or key.get("revoked") is not False:
            continue
        if not _unexpired(key.get("expires_at"), now):
            continue
        raw_key = key.get("raw_key")
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        subkeys = key.get("subkeys", [])
        if not isinstance(subkeys, list):
            continue
        candidates = [key, *subkeys]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if str(candidate.get("key_id", "")).upper() != suffix:
                continue
            if candidate.get("can_sign") is not True or candidate.get("revoked") is not False:
                continue
            if not _unexpired(candidate.get("expires_at"), now):
                continue
            return raw_key
    raise SystemExit(
        "GitHub account has no registered signing-capable, unrevoked, unexpired key "
        "matching the attestation fingerprint"
    )


def authorize_maintainer(
    *,
    repository: str,
    username: str,
    fingerprint: str,
    api_fn: Callable[[str], Any] | None = None,
    now: datetime | None = None,
) -> str:
    """Return the maintainer's armored public key or fail closed."""
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", username):
        raise SystemExit("publisher identity must be a valid GitHub username")
    if not re.fullmatch(r"[0-9A-F]{40}", fingerprint):
        raise SystemExit("publisher GitHub key fingerprint must be 40 uppercase hex characters")
    owner, name = _repository_owner_name(repository)
    api = api_fn or _github_api
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    permission = api(f"repos/{owner}/{name}/collaborators/{username}/permission")
    if not isinstance(permission, dict):
        raise SystemExit("GitHub repository permission response was invalid")
    if str(permission.get("user", {}).get("login", "")).lower() != username.lower():
        raise SystemExit("GitHub repository permission identity does not match the publisher")
    if permission.get("role_name") not in _ALLOWED_ROLES:
        raise SystemExit("release publisher must have the GitHub maintain or admin role")

    keys: list[Any] = []
    for page in range(1, _API_MAX_PAGES + 1):
        batch = api(f"users/{username}/gpg_keys?per_page=100&page={page}")
        if not isinstance(batch, list):
            raise SystemExit("GitHub public-key response was invalid")
        keys.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise SystemExit("GitHub public-key inventory exceeded its pagination bound")
    return _select_raw_key(keys, fingerprint, current_time)
