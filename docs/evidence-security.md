# Evidence Security and Privacy

Packets, evidence, handoffs, screenshots, logs, prompts, tool output, and
telemetry are project records. They may contain confidential source, personal
data, customer data, credentials, or proprietary model context. Treat them as
data assets, not harmless notes.

## Classification

Every evidence item declares one classification:

- `public`: safe for unrestricted publication;
- `internal`: project information for authorized team members;
- `confidential`: proprietary source, customer, vendor, or model information;
- `restricted`: secrets, credentials, regulated data, or high-impact security
  material.

Use the highest classification present. If classification is unknown, use
`confidential` until a reviewer resolves it.

## Capture rules

Before recording evidence:

1. Capture only the minimum data needed to prove the acceptance criterion.
2. Prefer identifiers, hashes, counts, schemas, and redacted excerpts over
   raw payloads.
3. Never record passwords, API keys, session cookies, private keys, or bearer
   tokens.
4. Do not copy customer or regulated data when a synthetic fixture or
   aggregate proves the result.
5. Record the source, classification, access policy, retention class, and
   redaction status in `templates/evidence-policy.yaml`.

Screenshots and terminal captures follow the same rules as text. Shell
commands must not echo secrets. If a secret appears, stop, contain it, rotate
or revoke it when required, and create an incident record.

## Redaction and scanning

Evidence is not complete until required redaction and secret scanning pass.
Redaction must be reviewed for re-identification risk, including values that
are unique in combination. A failed or unavailable scanner is a limitation,
not a pass.

The repository uses Gitleaks 8.24.3 for local and CI scanning. The CI scanner
checks Git history and the complete checked-out working tree, including any
generated files present during the job. It runs with redacted output and does
not upload scan reports or comment on pull requests. Use the same pinned
version locally:

```sh
gitleaks detect --source . --redact --exit-code 1 --config .gitleaks.toml
gitleaks dir . --redact --exit-code 1 --config .gitleaks.toml
```

The evidence-policy template is a required contract, not a suggestion. Each
instantiated policy must declare classification, sensitive-data status,
redaction status and reviewer, scanner and result, access/storage and
encryption, retention, telemetry capture, and incident linkage. Restricted or
confidential evidence belongs in an approved encrypted store with authorized
roles and an audit trail.

Do not rely on repository visibility as access control. Restricted evidence
belongs in an approved encrypted store with authorized roles and an audit
trail. The repository should contain a reference, hash, or sanitized summary
when full evidence cannot be safely committed.

## Telemetry

Raw prompts, responses, tool arguments, and tool results are prohibited by
default. Store stable IDs, hashes, classifications, outcomes, timing,
resource counts, and redacted metadata instead. Raw content requires explicit
approval, a named purpose, access restrictions, and an expiry.

Telemetry export failures must not silently disable safety or audit events.
Record the failure and use a bounded local buffer or stop the affected
operation according to risk.

## Retention and disposal

Use the cleanup protocol's retention classes, but apply the stricter legal,
contractual, security, or project requirement. Keep restricted evidence only
as long as necessary for incident response, audit, or approved retention.
Disposal of evidence with active incidents, legal holds, or open packets is
blocked. Archive before deletion when required, and record disposal approval.

## Incident linkage

Link evidence containing a suspected leak, injection, unauthorized access,
or compromised artifact to an incident. Preserve chain of custody, access
history, hashes, and timestamps without spreading the sensitive content.
