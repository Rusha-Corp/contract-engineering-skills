# Security policy

## Reporting a vulnerability

Do not open a public issue or paste a secret, exploit, token, or private
evidence into a pull request. Use GitHub's private Security Advisory reporting
path for this repository. Include a redacted description, affected revision,
impact, reproduction steps that do not contain live credentials, and a safe
contact path.

If private reporting is unavailable, notify the repository owners through an
existing private channel and mark the report restricted. Do not publish
details until the owner confirms remediation and disclosure timing.

## Repository controls

Security-sensitive changes require CODEOWNERS review and the repository's
independent approval process. The security workflow runs CodeQL, dependency
review, OpenSSF Scorecard, workflow invariant checks, and protocol validation.
Pull-request jobs use read-only permissions, do not receive repository secrets,
and do not use privileged pull-request triggers.

Findings are triaged by the repository owner:

- critical or high findings block merge or release;
- moderate findings require an owner and remediation plan within 7 days;
- low findings require an owner and remediation plan within 30 days.

An exception requires a recorded scope, rationale, compensating control,
independent approval, expiration no later than 30 days, and a linked
remediation issue. Expired exceptions fail closed.
