#!/usr/bin/env python3
"""File-backed packet leases with expiry and fencing tokens."""

from __future__ import annotations

import argparse
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


class LeaseError(ValueError):
    """Raised when a lease cannot be claimed or validated."""


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class LeaseManager:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.directory = self.root / "leases"

    def _path(self, packet_id: str) -> Path:
        return self.directory / f"{packet_id}.yaml"

    def _load(self, packet_id: str) -> dict[str, Any] | None:
        path = self._path(packet_id)
        if not path.is_file():
            return None
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(value, dict):
            raise LeaseError(f"{path}: lease must be a mapping")
        return value

    def _write(self, packet_id: str, lease: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(packet_id)
        stored = dict(lease)
        token = stored.pop("fencing_token", "")
        if token.startswith("epoch:"):
            stored["fencing_epoch"] = int(token.split(":", 1)[1])
        fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                yaml.safe_dump(stored, stream, sort_keys=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def claim(
        self,
        packet_id: str,
        holder: str,
        *,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        previous = self._load(packet_id)
        if previous and previous.get("release", {}).get("status") == "active":
            expires_at = _parse(previous["expires_at"])
            if expires_at > now:
                raise LeaseError(f"packet lease is active until {previous['expires_at']}")
            previous["release"]["status"] = "expired"
        previous_epoch = int(previous.get("fencing_epoch", 0)) if previous else 0
        fencing_epoch = previous_epoch + 1
        lease = {
            "lease_version": 1,
            "packet_id": packet_id,
            "holder": {"agent_id": holder, "harness": "local", "session_id": holder},
            "issued_at": _iso(now),
            "expires_at": _iso(now + timedelta(seconds=ttl_seconds)),
            "heartbeat_at": _iso(now),
            "renewal_count": 0,
            "fencing_token": f"epoch:{fencing_epoch}",
            "fencing_epoch": fencing_epoch,
            "takeover": {
                "status": "completed" if previous else "none",
                "prior_holder": (
                    previous.get("holder", {}).get("agent_id", "") if previous else ""
                ),
                "reason": "expired lease takeover" if previous else "",
                "recovery_plan": "revalidate packet scope and revision",
                "takeover_ref": None,
            },
            "release": {"status": "active", "released_at": "", "release_ref": None},
        }
        self._write(packet_id, lease)
        return lease

    def validate(
        self,
        packet_id: str,
        fencing_token: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        lease = self._load(packet_id)
        if not lease:
            raise LeaseError("packet lease is missing")
        if lease.get("release", {}).get("status") != "active":
            raise LeaseError("packet lease is not active")
        expected_token = f"epoch:{lease.get('fencing_epoch', 0)}"
        if fencing_token != expected_token:
            raise LeaseError("fencing token is rejected")
        if _parse(lease["expires_at"]) <= now:
            raise LeaseError("packet lease is expired")
        return lease

    def renew(
        self,
        packet_id: str,
        fencing_token: str,
        *,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        lease = self.validate(packet_id, fencing_token, now=now)
        lease["expires_at"] = _iso(now + timedelta(seconds=ttl_seconds))
        lease["heartbeat_at"] = _iso(now)
        lease["renewal_count"] = int(lease.get("renewal_count", 0)) + 1
        self._write(packet_id, lease)
        return lease

    def release(
        self,
        packet_id: str,
        fencing_token: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        lease = self.validate(packet_id, fencing_token, now=now)
        lease["release"] = {
            "status": "released",
            "released_at": _iso(now),
            "release_ref": None,
        }
        self._write(packet_id, lease)
        return lease


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".contract-engineering"))
    parser.add_argument("packet")
    parser.add_argument("holder")
    parser.add_argument("--ttl-seconds", type=int, default=900)
    args = parser.parse_args()
    lease = LeaseManager(args.root).claim(
        args.packet, args.holder, ttl_seconds=args.ttl_seconds
    )
    public = dict(lease)
    public.pop("fencing_token", None)
    print(yaml.safe_dump(public, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
