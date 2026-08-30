# Repository code security

## CI checks

`.github/workflows/security.yml` runs on pull requests, pushes to `main`,
scheduled review, and manual dispatch. It is read-only and does not execute
pull-request code with secrets or write permissions.

| Control | Tool | Blocking policy |
| --- | --- | --- |
| Python SAST | GitHub CodeQL, `security-extended` queries | Any high or critical result |
| Changed dependency vulnerabilities | GitHub Dependency Review | High or critical severity |
| Dependency licenses | Dependency Review | Denied licenses or unknown license |
| Repository security posture | OpenSSF Scorecard | Failing required checks are triaged before release |
| Workflow security | Local invariant guard | Mutable actions, missing permissions/timeout, or privileged PR trigger |
| Contract provenance | Contract record validator | Invalid lock, record, reference, or scope |

The dependency and license checks operate on pull requests. Scheduled and main
branch runs cover the repository’s current state and full history where the
scanner supports it. SARIF is written only to the ephemeral runner for this
read-only workflow; it is not uploaded or published by default.

All third-party actions use full commit SHAs. Workflow jobs have explicit
permissions, bounded timeouts, cancellation of superseded runs, and
`persist-credentials: false` on checkouts. Any action or dependency update
requires review of its source, resolved revision, permissions, and rollback.

## Review and protection requirements

Repository administrators must configure, and periodically test:

- required status checks for protocol validation, secret scanning, and security;
- required CODEOWNERS review for `.github/`, `.contract-engineering/`,
  `scripts/`, `schemas/`, `templates/`, and release metadata;
- no force-pushes or branch deletion on the default branch;
- no approval of a pull request by its author;
- signed or otherwise authenticated release tags and protected release paths;
- restricted workflow and repository-administration bypasses with audit logs.

An emergency bypass requires a named approver, reason, affected checks, start
and end time, compensating validation, and a follow-up incident or review.
Bypasses never waive secret rotation, artifact verification, or release
revocation.

## Finding lifecycle

Every finding has a severity, owner, due date, affected revision, disposition,
and evidence reference. Critical and high findings block merge and release.
Moderate findings require remediation within 7 days; low findings within 30
days. Exceptions are time-bounded to 30 days or less and require independent
approval and a compensating control. The security owner rechecks open findings
weekly and closes an exception only after the underlying control passes.
