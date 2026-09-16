"""Stable, fail-closed diagnostics for repository gate failures."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Iterable

REQUIRED_FIELDS = (
    "code", "severity", "message", "remediation", "packet_id",
    "gate_name", "blocking",
)

DIAGNOSTIC_CODES = {
    "GATE-SCOPE-001": "scope violation",
    "GATE-EVIDENCE-001": "missing evidence",
    "GATE-STATE-001": "state machine violation",
    "GATE-SECURITY-001": "security finding",
    "GATE-DEPENDENCY-001": "missing dependency",
    "GATE-HASH-001": "hash mismatch",
}
SECURITY_CODES = {"GATE-SECURITY-001"}


@dataclass(frozen=True)
class DiagnosticEnvelope:
    code: str
    severity: str
    message: str
    remediation: tuple[str, ...]
    packet_id: str | None
    gate_name: str
    blocking: bool

    def to_dict(self) -> dict:
        result = asdict(self)
        result["remediation"] = list(self.remediation)
        return result


def emit_diagnostic(
    code: str,
    message: str,
    remediation: Iterable[str],
    *,
    packet_id: str | None = None,
    gate_name: str = "repository",
    severity: str = "error",
    blocking: bool | None = None,
) -> DiagnosticEnvelope:
    if code not in DIAGNOSTIC_CODES:
        raise ValueError(f"unknown diagnostic code: {code}")
    if severity not in {"error", "warning", "info"}:
        raise ValueError(f"invalid diagnostic severity: {severity}")
    steps = tuple(str(step) for step in remediation if str(step).strip())
    if not steps:
        raise ValueError("remediation must contain an actionable step")
    if code in SECURITY_CODES:
        severity, blocking = "error", True
    elif blocking is None:
        blocking = severity == "error"
    return DiagnosticEnvelope(
        code, severity, str(message), steps, packet_id, str(gate_name), bool(blocking)
    )


def format_diagnostic(diagnostic: DiagnosticEnvelope, output: str = "human") -> str:
    if output == "json":
        return json.dumps(diagnostic.to_dict(), sort_keys=True)
    if output == "markdown":
        steps = "\n".join(f"- {step}" for step in diagnostic.remediation)
        return (
            f"### {diagnostic.code} ({diagnostic.severity})\n\n"
            f"{diagnostic.message}\n\n**Remediation**\n{steps}"
        )
    if output == "human":
        return f"[{diagnostic.code}] {diagnostic.message} Remediation: {'; '.join(diagnostic.remediation)}"
    raise ValueError(f"unsupported diagnostic format: {output}")
