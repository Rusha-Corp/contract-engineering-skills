"""Semantic gates for runtime blast-radius assessments.

The JSON schema validates shape. This module validates lifecycle freshness and
prevents inferred topology from substituting for accepted live evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .loaders import fail


ADOPTION_CLAIM_CUTOVER = "2026-11-23T00:00:00Z"
TERMINAL_STATES = {"Complete", "Cancelled"}
HIGH_EVIDENCE_STATES = {
    "Ready", "Implementing", "Validation", "Rework", "Handoff", "Complete"
}
LIVE_EVIDENCE_MAX_AGE_SECONDS = 24 * 60 * 60


def _timestamp(value: Any, field: str, path: Path) -> datetime:
    if not isinstance(value, str) or not value.strip():
        fail(f"{path}: {field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        fail(f"{path}: {field} must be an ISO-8601 timestamp")
    if parsed.tzinfo is None:
        fail(f"{path}: {field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _fresh(value: Any, field: str, path: Path, now: datetime) -> None:
    observed = _timestamp(value, field, path)
    age = (now - observed).total_seconds()
    if age < -300 or age > LIVE_EVIDENCE_MAX_AGE_SECONDS:
        fail(f"{path}: {field} is stale or outside the live-evidence window")


def _required(mapping: dict[str, Any], fields: tuple[str, ...], path: Path, prefix: str) -> None:
    for field in fields:
        value = mapping.get(field)
        if value is None or value == "" or value == []:
            fail(f"{path}: {prefix}.{field} is required")


def _pre_adoption_claim(packet: dict[str, Any]) -> bool:
    claimed = packet.get("claim_timestamp")
    return isinstance(claimed, str) and claimed < ADOPTION_CLAIM_CUTOVER


def _governed_without_assessment(packet: dict[str, Any]) -> bool:
    return packet.get("state") not in TERMINAL_STATES | {"Planned"}


def _validate_rollout(
    path: Path, assessment: dict[str, Any], state: str
) -> None:
    couplings = assessment.get("couplings", [])
    rollout = assessment.get("rollout", [])
    if not rollout:
        fail(f"{path}: high-risk assessment requires a rollout order")
    incompatible = any(
        item.get("compatibility") == "incompatible"
        for item in couplings
        if isinstance(item, dict)
    )
    phases = [step.get("phase") for step in rollout if isinstance(step, dict)]
    if incompatible and phases != ["expand", "migrate", "contract"]:
        fail(f"{path}: incompatible reductions require expand -> migrate -> contract rollout")
    if any(
        step.get("status") in {"complete", "verified"} and not step.get("evidence_refs")
        for step in rollout
    ):
        fail(f"{path}: completed rollout steps require evidence")
    if state == "Complete" and any(
        step.get("status") != "verified" or not step.get("evidence_refs")
        for step in rollout
    ):
        fail(f"{path}: expand -> migrate -> contract steps require verified evidence")


def blast_radius_evidence_refs(
    packet: dict[str, Any],
) -> list[tuple[str, str]]:
    """Return nested evidence IDs for storage-backed existence validation."""
    assessment = packet.get("blast_radius")
    if not isinstance(assessment, dict):
        return []
    references: list[tuple[str, str]] = []
    for field in ("inference_review", "live_scope", "post_deploy_verification"):
        section = assessment.get(field)
        if isinstance(section, dict):
            for ref in section.get("evidence_refs", []):
                if isinstance(ref, str):
                    references.append((f"blast_radius.{field}", ref))
    for step in assessment.get("rollout", []):
        if isinstance(step, dict):
            for ref in step.get("evidence_refs", []):
                if isinstance(ref, str):
                    references.append(("blast_radius.rollout", ref))
    return references

def validate_blast_radius_semantics(
    packet: dict[str, Any], path: Path, *, now: datetime | None = None
) -> None:
    """Validate one packet's declared assessment and lifecycle evidence."""
    assessment = packet.get("blast_radius")
    if assessment is None:
        if _governed_without_assessment(packet):
            fail(f"{path}: blast_radius is required for a newly governed active packet")
        return
    if not isinstance(assessment, dict):
        fail(f"{path}: blast_radius must be a mapping")
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if assessment.get("version") != 1:
        fail(f"{path}: blast_radius.version must be 1")
    status = assessment.get("status")
    risk = assessment.get("risk")
    if status not in {"complete", "unknown", "no_runtime_impact"}:
        fail(f"{path}: invalid blast_radius.status")
    if risk not in {"low", "medium", "high"}:
        fail(f"{path}: invalid blast_radius.risk")
    if assessment.get("packet_revision") != packet.get("revision", 0):
        fail(f"{path}: blast_radius is stale for the material packet revision")
    _timestamp(assessment.get("assessed_at"), "blast_radius.assessed_at", path)

    if status == "no_runtime_impact":
        if risk != "low" or not str(assessment.get("rationale", "")).strip():
            fail(f"{path}: no_runtime_impact requires low risk and an explicit rationale")
        if assessment.get("components") or assessment.get("couplings"):
            fail(f"{path}: no_runtime_impact cannot declare runtime components or couplings")
        return
    if status == "unknown":
        if risk != "high" or not assessment.get("unknowns"):
            fail(f"{path}: unknown runtime impact requires high risk and named unknowns")
        if packet.get("state") in HIGH_EVIDENCE_STATES and not _pre_adoption_claim(packet):
            fail(f"{path}: unknown blast_radius cannot enter Ready or later governed states")
        return

    state = packet.get("state")
    if risk == "medium" and state in {"Handoff", "Complete"}:
        review = assessment.get("inference_review", {})
        if (
            review.get("status") != "completed"
            or not review.get("evidence_refs")
            or not review.get("reviewed_at")
        ):
            fail(f"{path}: medium-risk handoff requires completed inference_review evidence")
        _timestamp(
            review.get("reviewed_at"),
            "blast_radius.inference_review.reviewed_at",
            path,
        )
    if risk != "high" or state not in HIGH_EVIDENCE_STATES:
        return

    if not assessment.get("components"):
        fail(f"{path}: high-risk assessment requires runtime components")
    if not assessment.get("couplings"):
        fail(f"{path}: high-risk assessment requires coupling evidence")
    if any(
        item.get("provenance") != "verified"
        for item in assessment["couplings"]
        if isinstance(item, dict)
    ):
        fail(f"{path}: high-risk coupling evidence must be verified, not inferred")

    live = assessment.get("live_scope", {})
    _required(
        live,
        ("environments", "source_revision", "live_revision", "observed_at", "evidence_refs"),
        path,
        "blast_radius.live_scope",
    )
    if live.get("source_revision") != assessment.get("source_revision"):
        fail(f"{path}: live_scope source revision does not match the assessed revision")
    if state != "Complete":
        _fresh(live.get("observed_at"), "blast_radius.live_scope.observed_at", path, current_time)
    else:
        _timestamp(live.get("observed_at"), "blast_radius.live_scope.observed_at", path)
    _validate_rollout(path, assessment, state)

    if state == "Complete":
        post = assessment.get("post_deploy_verification", {})
        _required(
            post,
            ("entry_point", "source_revision", "live_revision", "verified_at", "evidence_refs"),
            path,
            "blast_radius.post_deploy_verification",
        )
        if (
            post.get("source_revision") != assessment.get("source_revision")
            or post.get("live_revision") != live.get("live_revision")
        ):
            fail(f"{path}: post_deploy_verification revisions do not match the rollout")
        _timestamp(
            post.get("verified_at"),
            "blast_radius.post_deploy_verification.verified_at",
            path,
        )
