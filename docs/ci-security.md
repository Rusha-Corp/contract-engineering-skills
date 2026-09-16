# CI Security Gates

## Overview

CI pipelines consume the protocol's gate diagnostics to enforce fail-closed
security behavior. Every CI adapter must emit the shared diagnostic envelope
and preserve blocking outcomes.

## CI gate sequence

1. **Preflight**: Verify protocol lock, skill hashes, and validator root.
2. **Scope gate**: Check that all changed files are inside the packet's
   `scope.in`. Emit `GATE-SCOPE-001` on violation.
3. **Evidence gate**: Verify required evidence records exist and reference
   real validation output. Emit `GATE-EVIDENCE-001` on missing evidence.
4. **State gate**: Verify the packet's state transition is legal. Emit
   `GATE-STATE-001` on illegal transitions.
5. **Security gate**: Run threat-model and security-verification checks.
   Emit `GATE-SECURITY-001` for findings and `GATE-SECURITY-002` for
   missing capabilities. Both are always blocking.
6. **Dependency gate**: Verify pinned dependencies and hashes. Emit
   `GATE-DEPENDENCY-001` for missing or unpinned dependencies.
7. **Hash gate**: Verify changed-resource hashes match the declared content
   head. Emit `GATE-HASH-001` on mismatch.

## Fail-closed enforcement

Security gates are always blocking. A CI pipeline must not:

- Downgrade a security diagnostic to non-blocking.
- Suppress or hide a security diagnostic from output.
- Continue execution after a blocking security diagnostic.

The `emit_diagnostic` function in `scripts/gate_diagnostics.py` enforces this
at the source: security codes always produce `blocking=true` regardless of
caller input.

## CI adapter conformance

A CI adapter conforms when it passes the adapter conformance test in
`tests/test_gate_diagnostics.py`. The test verifies:

- All required envelope fields are present.
- Blocking status is preserved.
- Security diagnostics remain `error` severity and `blocking=true`.
- No adapter hides or downgrades a gate failure.

## Integration

```python
from scripts.gate_diagnostics import conform_adapter, DiagnosticCode

output = conform_adapter(
    adapter_name="generic",
    code=DiagnosticCode.SECURITY_FINDING,
    packet_id="CENG-T013-P005",
    gate_name="security-gate",
    message="critical vulnerability in dependency",
)
# output is a dict with all required fields
# blocking is always True for security codes
```
