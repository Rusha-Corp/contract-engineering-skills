# Agent Incident Response

Use `templates/agent-incident.yaml` for any event that may affect
authorization, secrets, data correctness, protocol integrity, external
systems, or safe agent operation. Do not wait for certainty before
containing a credible high-impact event.

## Incident lifecycle

```text
Detected -> Contained -> Investigating -> Remediated -> Verified -> Closed
```

`Detected` records the signal and initial scope. `Contained` prevents further
harm. `Investigating` establishes facts and preserves evidence. `Remediated`
applies the approved fix or rollback. `Verified` independently confirms the
fix. `Closed` records user/security disposition, residual risk, and
postmortem actions.

## Triggers

Open an incident for:

- protocol-lock, skill, adapter, or release compromise;
- prompt injection or tool poisoning that affects scope, capability, approval,
  secrets, or external effects;
- unauthorized tool or external action;
- secret, restricted-data, or sensitive-evidence exposure;
- runaway agent, failed emergency stop, budget bypass, or stale lease;
- destructive or data-correctness error;
- tampered, revoked, or unverifiable provenance;
- repeated evaluation or observability failures that hide safety behavior.

## First response

1. Stop new packet claims and affected agents.
2. Trigger cancellation or quarantine; verify that child processes and
   external operations are stopped or isolated.
3. Revoke or rotate exposed credentials and disable compromised tools or
   releases when required.
4. Preserve redacted events, checkpoints, approvals, hashes, timestamps, and
   affected revisions.
5. Record affected projects, packets, actors, tools, data classes, and
   consumers without spreading sensitive content.
6. Notify the user, security owner, or consumers according to severity.

Containment actions may precede complete diagnosis. Do not destroy evidence
or “clean up” the worktree before the incident owner releases it.

## Investigation and remediation

Reconcile packet scope, actor capabilities, approval records, runtime budget,
lease, checkpoint, evaluation, event, evidence, and release provenance.
Classify facts, assumptions, unknowns, and affected time windows. Determine
whether the event was isolated, replayed, or propagated to other consumers.

Every remediation has an owner, approval, rollback, validation, and due date.
Security, credential, production, and release actions require the applicable
risk-tier approval. A fix is not verified merely because the triggering
command no longer reproduces.

## Closure

Close only after:

- containment and remediation are complete;
- credentials, tools, releases, and consumers are reconciled;
- evidence is retained under the privacy policy;
- an independent verifier confirms the result;
- residual risk and user/security disposition are recorded;
- a postmortem adds regression evaluation or protocol changes where needed.

Link the incident to affected packets and add a regression case to the
evaluation suite for confirmed agent failures.
