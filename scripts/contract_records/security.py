"""Security semantic validation for work packets."""

from __future__ import annotations

from typing import Any

from .constants import (
    EXECUTION_CONTROL_REFS,
    FORBIDDEN_CAPABILITIES,
    SECURITY_SCOPE_PATTERNS,
)
from .loaders import fail, path_matches


def validate_evidence_policy(policy: dict[str, Any], source: str = "evidence policy") -> None:
    required = {
        "evidence_policy_version",
        "classification",
        "contains_sensitive_data",
        "redaction",
        "secret_scan",
        "access",
        "retention",
        "telemetry",
    }
    missing = required - policy.keys()
    if missing:
        fail(f"{source}: missing evidence policy fields: {sorted(missing)}")
    if policy["classification"] not in {
        "public",
        "internal",
        "confidential",
        "restricted",
    }:
        fail(f"{source}: invalid classification")
    redaction = policy["redaction"]
    scan = policy["secret_scan"]
    access = policy["access"]
    retention = policy["retention"]
    telemetry = policy["telemetry"]
    if not isinstance(redaction, dict) or not isinstance(scan, dict):
        fail(f"{source}: redaction and secret_scan must be mappings")
    if not isinstance(access, dict) or not isinstance(retention, dict):
        fail(f"{source}: access and retention must be mappings")
    if not isinstance(telemetry, dict):
        fail(f"{source}: telemetry must be a mapping")
    if redaction.get("required") is not True or redaction.get("performed") is not True:
        fail(f"{source}: evidence redaction is incomplete")
    if not redaction.get("reviewer") or not redaction.get("method"):
        fail(f"{source}: evidence redaction reviewer and method are required")
    if scan.get("required") is not True or scan.get("result") != "pass":
        fail(f"{source}: evidence secret scan did not pass")
    if not scan.get("tool"):
        fail(f"{source}: evidence secret scan tool is required")
    if not isinstance(access.get("allowed_roles"), list):
        fail(f"{source}: evidence access roles must be a list")
    if access.get("storage") not in {
        "repository",
        "encrypted_archive",
        "restricted_store",
    }:
        fail(f"{source}: invalid evidence storage")
    if not isinstance(access.get("encryption_at_rest"), bool) or not isinstance(
        access.get("encryption_in_transit"), bool
    ):
        fail(f"{source}: evidence encryption flags must be boolean")
    if retention.get("class") not in {"standard", "extended", "archive"}:
        fail(f"{source}: invalid evidence retention class")
    if policy["classification"] in {"confidential", "restricted"}:
        if access.get("storage") not in {"encrypted_archive", "restricted_store"}:
            fail(f"{source}: sensitive evidence requires encrypted storage")
        if access.get("encryption_at_rest") is not True:
            fail(f"{source}: sensitive evidence requires encryption at rest")
    if telemetry.get("raw_content_allowed") is not False:
        fail(f"{source}: raw telemetry content must be denied")


def validate_security_semantics(packet: dict[str, Any]) -> None:
    """Enforce security controls from packet metadata, not task identifiers."""
    scope = packet.get("scope", {}).get("in", [])
    security_surface = any(
        path_matches(str(candidate), pattern)
        for candidate in scope
        for pattern in SECURITY_SCOPE_PATTERNS
    )
    trigger = (
        packet.get("domain") == "security"
        or packet.get("risk_tier") in {"high", "critical"}
        or bool(packet.get("external_effects"))
        or any(
            str(capability).startswith(
                ("network:", "external:", "secrets:", "destructive:")
            )
            for capability in packet.get("capabilities", [])
        )
        or ("packet_class" in packet and security_surface)
    )
    if not trigger:
        return
    required = {"capabilities", "risk_tier", "approval_policy", "external_effects"}
    missing = required - packet.keys()
    if missing:
        fail(f"{packet['packet_id']}: missing security fields: {sorted(missing)}")
    if packet["risk_tier"] not in {"low", "medium", "high", "critical"}:
        fail(f"{packet['packet_id']}: invalid risk tier")
    if packet["approval_policy"] not in {"automatic", "reviewer", "user", "two_person"}:
        fail(f"{packet['packet_id']}: invalid approval policy")
    actor = packet.get("implementor") or packet.get("actor")
    if not isinstance(actor, dict) or not {
        "agent_id",
        "harness",
        "model",
        "session_id",
    } <= actor.keys():
        fail(f"{packet['packet_id']}: implementor (or actor) identity is incomplete")
    if not isinstance(packet["capabilities"], list):
        fail(f"{packet['packet_id']}: capabilities must be a list")
    excessive = FORBIDDEN_CAPABILITIES.intersection(packet["capabilities"])
    if excessive:
        fail(f"{packet['packet_id']}: forbidden capabilities: {sorted(excessive)}")
    if packet["risk_tier"] in {"high", "critical"} and packet["approval_policy"] == "automatic":
        fail(f"{packet['packet_id']}: high-risk work cannot use automatic approval")
    for effect in packet["external_effects"]:
        # Completed records from before structured external effects were
        # introduced remain readable until an explicit migration packet
        # updates them. New classified packets must use structured effects.
        if packet["state"] == "Complete" and "packet_class" not in packet:
            continue
        if not isinstance(effect, dict):
            fail(f"{packet['packet_id']}: external effects must be structured")
        required_effect = {
            "effect_id",
            "target",
            "operation",
            "data_classification",
            "approval_ref",
            "rollback",
        }
        missing_effect = required_effect - effect.keys()
        if missing_effect:
            fail(
                f"{packet['packet_id']}: external effect missing fields: "
                f"{sorted(missing_effect)}"
            )
        if not effect.get("declared") or not effect.get("approval_ref"):
            fail(f"{packet['packet_id']}: external effect is missing declaration or approval")
        if effect.get("reversible") is not True:
            fail(f"{packet['packet_id']}: external effect must be reversible or separately approved")
    if packet["state"] != "Complete" and packet["risk_tier"] in {"high", "critical"}:
        for name in EXECUTION_CONTROL_REFS:
            value = packet.get(name)
            if not value:
                fail(f"{packet['packet_id']}: missing applicable control reference {name}")
    if "evidence_policy" in packet:
        policy = packet["evidence_policy"]
        if not isinstance(policy, dict):
            fail(f"{packet['packet_id']}: evidence_policy must be a mapping")
        validate_evidence_policy(policy, packet["packet_id"])
