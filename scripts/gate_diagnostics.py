#!/usr/bin/env python3
"""Structured gate-failure diagnostics and adapter conformance contract.

Every gate failure emits a DiagnosticEnvelope with stable machine-readable
codes, severity, message, remediation steps, packet_id, gate_name, and a
blocking flag. Security diagnostics are always blocking (fail-closed) and
cannot be downgraded.

All adapters conform to the same required envelope fields defined in
ADAPTER_CONTRACT_FIELDS.
"""
from __future__ import annotations

import enum
import json
from dataclasses import dataclass, asdict
from typing import Any


class DiagnosticCode(enum.Enum):
    """Stable, machine-readable gate-failure codes."""

    SCOPE_VIOLATION = "GATE-SCOPE-001"
    MISSING_EVIDENCE = "GATE-EVIDENCE-001"
    STATE_VIOLATION = "GATE-STATE-001"
    SECURITY_FINDING = "GATE-SECURITY-001"
    SECURITY_CAPABILITY = "GATE-SECURITY-002"
    MISSING_DEPENDENCY = "GATE-DEPENDENCY-001"
    HASH_MISMATCH = "GATE-HASH-001"


# Codes that are always blocking (fail-closed)
SECURITY_CODES = frozenset({
    DiagnosticCode.SECURITY_FINDING,
    DiagnosticCode.SECURITY_CAPABILITY,
})

# Required fields every adapter must emit
ADAPTER_CONTRACT_FIELDS = (
    "code",
    "severity",
    "message",
    "remediation",
    "packet_id",
    "gate_name",
    "blocking",
)

# Remediation text for each code
_REMEDIATION = {
    DiagnosticCode.SCOPE_VIOLATION:
        "Review the packet's scope.in and scope.out. Move the change inside "
        "scope.in or record a scope-change decision before proceeding.",
    DiagnosticCode.MISSING_EVIDENCE:
        "Create or link the required evidence record. Run the packet's "
        "validation plan and capture the output in an evidence file.",
    DiagnosticCode.STATE_VIOLATION:
        "Check the packet's current state and the allowed transitions table. "
        "Transition through the correct intermediate state or correct the "
        "packet state before retrying.",
    DiagnosticCode.SECURITY_FINDING:
        "Treat as a blocking security finding. Perform threat modeling, "
        "apply mitigations, and re-run security verification before "
        "proceeding. Do not downgrade severity.",
    DiagnosticCode.SECURITY_CAPABILITY:
        "The adapter cannot prove a required security capability. Block the "
        "operation, record the limitation, and escalate for manual approval "
        "or capability provisioning.",
    DiagnosticCode.MISSING_DEPENDENCY:
        "Install or pin the missing dependency. Verify hashes against the "
        "requirements file and re-run validation.",
    DiagnosticCode.HASH_MISMATCH:
        "Recompute the changed-resource hashes against the declared content "
        "head. Update the handoff binding or restore the file to the declared "
        "state.",
}

# Severity defaults per code
_SEVERITY = {
    DiagnosticCode.SCOPE_VIOLATION: "error",
    DiagnosticCode.MISSING_EVIDENCE: "error",
    DiagnosticCode.STATE_VIOLATION: "error",
    DiagnosticCode.SECURITY_FINDING: "error",
    DiagnosticCode.SECURITY_CAPABILITY: "error",
    DiagnosticCode.MISSING_DEPENDENCY: "warning",
    DiagnosticCode.HASH_MISMATCH: "error",
}


@dataclass
class DiagnosticEnvelope:
    """Structured gate-failure diagnostic."""

    code: str
    severity: str
    message: str
    remediation: str
    packet_id: str
    gate_name: str
    blocking: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def emit_diagnostic(
    *,
    code: DiagnosticCode,
    packet_id: str,
    gate_name: str,
    message: str,
    blocking: bool | None = None,
) -> DiagnosticEnvelope:
    """Create a DiagnosticEnvelope from a gate failure.

    Security codes are always blocking regardless of the ``blocking`` argument.
    """
    is_security = code in SECURITY_CODES
    if is_security:
        effective_blocking = True  # fail-closed: cannot be downgraded
    elif blocking is not None:
        effective_blocking = blocking
    else:
        effective_blocking = _SEVERITY.get(code, "error") == "error"

    return DiagnosticEnvelope(
        code=code.value,
        severity=_SEVERITY.get(code, "error"),
        message=message,
        remediation=_REMEDIATION.get(code, "Review the gate requirements and retry."),
        packet_id=packet_id,
        gate_name=gate_name,
        blocking=effective_blocking,
    )


def format_diagnostic(diag: DiagnosticEnvelope, fmt: str = "json") -> str:
    """Format a diagnostic for different output targets.

    Args:
        diag: The diagnostic envelope to format.
        fmt: Output format - "json" (machine-readable), "human" (terminal),
             or "markdown" (documentation).
    """
    if fmt == "json":
        return json.dumps(diag.to_dict(), indent=2, sort_keys=True)
    if fmt == "human":
        lines = [
            f"[{diag.severity.upper()}] {diag.code} ({diag.gate_name})",
            f"  Packet: {diag.packet_id}",
            f"  Message: {diag.message}",
            f"  Remediation: {diag.remediation}",
            f"  Blocking: {diag.blocking}",
        ]
        return "\n".join(lines)
    if fmt == "markdown":
        lines = [
            f"### {diag.code} — {diag.gate_name}",
            f"- **Severity:** {diag.severity}",
            f"- **Packet:** {diag.packet_id}",
            f"- **Blocking:** {diag.blocking}",
            f"- **Message:** {diag.message}",
            f"- **Remediation:** {diag.remediation}",
        ]
        return "\n".join(lines)
    raise ValueError(f"unknown format: {fmt}")


def conform_adapter(
    *,
    adapter_name: str,
    code: DiagnosticCode,
    packet_id: str,
    gate_name: str,
    message: str,
) -> dict[str, Any]:
    """Emit a conformant diagnostic for an adapter.

    All adapters produce the same required envelope fields. This function
    validates conformance and returns the envelope as a dict.

    Args:
        adapter_name: One of "factory-droid", "generic", "hermes".
        code: The diagnostic code.
        packet_id: The packet identifier.
        gate_name: The gate that failed.
        message: Human-readable failure message.
    """
    diag = emit_diagnostic(
        code=code,
        packet_id=packet_id,
        gate_name=gate_name,
        message=message,
    )
    result = diag.to_dict()
    result["adapter"] = adapter_name

    # Verify conformance: all required fields present
    for field in ADAPTER_CONTRACT_FIELDS:
        assert field in result, f"{adapter_name}: missing required field {field}"

    return result
