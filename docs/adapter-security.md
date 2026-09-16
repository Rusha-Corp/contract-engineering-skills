# Adapter Security Model

## Overview

Adapters translate the protocol's gate-failure diagnostics into host-specific
output while preserving blocking semantics. Every adapter conforms to a single
diagnostic contract defined in `scripts/gate_diagnostics.py`.

## Diagnostic envelope

All gate failures emit a `DiagnosticEnvelope` with these required fields:

| Field | Type | Description |
| --- | --- | --- |
| `code` | string | Stable machine-readable code (e.g. `GATE-SCOPE-001`) |
| `severity` | string | `error`, `warning`, or `info` |
| `message` | string | Human-readable failure description |
| `remediation` | string | Actionable steps to resolve the failure |
| `packet_id` | string | The packet that triggered the gate |
| `gate_name` | string | The gate that failed |
| `blocking` | bool | Whether the failure blocks further work |

## Error code registry

| Code | Severity | Blocking | Description |
| --- | --- | --- | --- |
| `GATE-SCOPE-001` | error | yes | Packet edited outside declared scope |
| `GATE-EVIDENCE-001` | error | yes | Required evidence record is missing |
| `GATE-STATE-001` | error | yes | Illegal state machine transition |
| `GATE-SECURITY-001` | error | yes | Security finding detected |
| `GATE-SECURITY-002` | error | yes | Required security capability not proven |
| `GATE-DEPENDENCY-001` | warning | no | Missing or unpinned dependency |
| `GATE-HASH-001` | error | yes | Content hash mismatch |

## Fail-closed policy

Security diagnostics (`GATE-SECURITY-001`, `GATE-SECURITY-002`) are always
blocking. The `emit_diagnostic` function enforces this: even if a caller
passes `blocking=False`, the envelope remains blocking. Adapters must not
downgrade or hide security failures.

## Adapter conformance

An adapter conforms when:

1. It emits all required envelope fields for every gate failure.
2. It preserves the `blocking` flag without downgrading.
3. Security diagnostics remain `severity=error` and `blocking=true`.
4. It does not hide, suppress, or alter the diagnostic code.

The conformance test in `tests/test_gate_diagnostics.py` verifies all four
requirements for every supported adapter.

## Supported adapters

- **factory-droid**: Emits JSON diagnostics to the Factory Droid hook output.
- **generic**: Emits human-readable or JSON diagnostics to any host.
- **hermes**: Emits JSON diagnostics through the Hermes skill interface.

All adapters call `conform_adapter()` from `scripts/gate_diagnostics.py`,
which validates the envelope before returning it.

## Usage

```python
from scripts.gate_diagnostics import emit_diagnostic, DiagnosticCode, format_diagnostic

diag = emit_diagnostic(
    code=DiagnosticCode.SCOPE_VIOLATION,
    packet_id="CENG-T013-P005",
    gate_name="scope-gate",
    message="packet edited file outside scope.in",
)
print(format_diagnostic(diag, "json"))
print(format_diagnostic(diag, "human"))
```
