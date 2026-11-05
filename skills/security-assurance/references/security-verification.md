# Security Verification Gate

This reference is part of the `security-assurance` skill.
The skill's SKILL.md is the normative source; this file provides the
detailed security verification gate specification.

Required for every packet before it transitions from `Validation` to
`Handoff`, regardless of domain. This gate runs in addition to the
validation plan in `phased-engineering-execution/SKILL.md`.

## Required checks

```yaml
security_verification:
  packet_id: PROJECT-T001-P001
  gate_version: 1
  performed_at: ""
  performed_by: ""
  checks:
    - id: SEC-001
      kind: secret-scan
      tool: "gitleaks 8.24.3"
      scope: "git-history, working-tree"
      result: pass|fail
      evidence_ref: ""
    - id: SEC-002
      kind: dependency-review
      tool: "github dependency-review"
      scope: "changed dependencies"
      result: pass|fail
      findings: []
      evidence_ref: ""
    - id: SEC-003
      kind: sast
      tool: "codeql"
      scope: "changed files"
      result: pass|fail
      findings: []
      evidence_ref: ""
    - id: SEC-004
      kind: threat-model-verification
      scope: "threat model mitigations"
      result: pass|fail
      unverified_mitigations: []
      evidence_ref: ""
    - id: SEC-005
      kind: trust-boundary-validation
      scope: "external content, tool output, agent messages"
      result: pass|fail
      injection_attempts: []
      evidence_ref: ""
  finding_summary:
    critical: 0
    high:0
    moderate:0
    low:0
  disposition: pass|blocked|exception
  exception_ref: ""
  approval_ref: ""
```

## Finding lifecycle

Every finding has a severity, owner, due date, affected revision,
disposition, and evidence reference:

| Severity | Blocking | Remediation window |
| --- | --- | --- |
| Critical | Blocks merge and release | Immediate |
| High | Blocks merge and release | Before merge |
| Moderate | Does not block merge | 7 days |
| Low | Does not block merge | 30 days |

Exceptions require a recorded scope, rationale, compensating control,
independent approval, expiration no later than 30 days, and a linked
remediation issue. Expired exceptions fail closed. See `docs/code-security.md`
for the full finding lifecycle.

## Gate rules

- The gate fails if any check returns `fail` and the finding is critical or
  high severity.
- The gate fails if the threat model has unverified mitigations for high or
  critical risks.
- The gate fails if a secret scan detects a live credential.
- The gate fails if a dependency has a high or critical vulnerability without
  an approved exception.
- The gate passes with moderate or low findings only when each has an owner,
  due date, and remediation plan recorded.
- A passing gate is not a security certification; it is evidence that the
  required checks were performed and findings were dispositioned.
