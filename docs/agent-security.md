# Agent Identity, Capabilities, and Authorization

This contract applies to every agent, human, CI job, or host adapter that
claims or executes a packet. It defines who is acting, what the actor may do,
and which approvals are required. Host adapters provide the identity and
approval mechanism; they do not weaken this contract.

The security gate is selected from packet metadata, not from a task
identifier. It is mandatory when the packet uses the `security` domain,
declares a high or critical risk tier, declares external effects, requests
network, external, secret, or destructive capabilities, or is a classified
packet whose scope touches a security-sensitive path such as workflows,
adapters, security documents, schemas, or agent templates.

## Actor record

Record the following fields in each packet:

```yaml
actor:
  agent_id: "stable host-issued identifier"
  harness: "factory-droid|ide|cli|ci|human"
  model: "provider/model/version or human"
  session_id: "host session or run identifier"
capabilities:
  - read:repository
  - write:packet-scope
risk_tier: low|medium|high|critical
approval_policy: automatic|reviewer|user|two_person
external_effects: []
```

`agent_id` identifies the actor, not the task. `session_id` identifies one
execution attempt. A resumed attempt keeps the packet identity but records a
new session and a recovery reference. Never use a display name as the only
identity.

The actor record is metadata, not permission by itself. The host must enforce
the capabilities or explicitly record that enforcement is unavailable and
block actions that require unavailable controls. The limitation or incident
record must be referenced by the packet before the blocked action can be
reconsidered.

## Capability rules

Use the smallest capability set that satisfies the packet. This is the
least privilege baseline:

- `read:repository` for inspection;
- `write:packet-scope` for files in `scope.in`;
- `execute:local-validation` for approved local checks;
- `network:allowlisted` for named endpoints;
- `external:prepare` for an unsubmitted draft;
- `external:mutate` for a submitted or irreversible external action;
- `destructive:approved` only for a specifically named destructive operation;
- `secrets:use` only when the packet names the secret class, purpose, and
  approved storage path. Never place the secret value in a packet or log.

Capabilities do not imply one another. Read access does not grant write,
network, secret, or external-mutation access. A tool or child agent may
receive only a subset of the parent actor's capabilities.

## Risk and approval matrix

| Tier | Typical action | Minimum approval |
| --- | --- | --- |
| `low` | Read-only inspection, local parsing, reversible untracked draft | `automatic` |
| `medium` | Scoped file changes, local builds, reversible dependency or config edits | `reviewer` |
| `high` | Shared contract changes, credential use, production-like data, external draft, broad migration | `user` |
| `critical` | Irreversible deletion, production mutation, permission grant, release revocation, or high-impact external action | `two_person` |

The packet may choose a stricter policy. It may not choose a weaker policy for
the tier. If risk is unclear, use the higher tier.

Approval is tied to a concrete action, scope, actor, and revision. A general
request to “implement” does not approve a critical external effect. Approval
must be recorded in the packet, decision, handoff, or host audit record before
the action.

## Separation of duties

For high and critical work:

1. The actor cannot approve its own action.
2. The reviewer must be a distinct human or independently controlled agent.
3. The release actor must not be the sole author and approver of a protocol
   release.
4. A takeover records the prior actor, reason, capabilities transferred, and
   new approval.

If a host cannot provide independent review, the packet remains blocked or
requires explicit user acceptance of the limitation. That acceptance does not
authorize a capability the host cannot enforce.

## External effects

List every expected effect outside the worktree, including network writes,
messages, pull requests, deployments, purchases, access changes, deletions,
and credential operations. Each effect records:

```yaml
external_effects:
  - effect_id: EFFECT-001
    target: ""
    operation: read|prepare|mutate|delete|publish
    data_classification: public|internal|confidential|restricted
    declared: true
    reversible: true
    approval_ref: ""
    rollback: ""
```

Agents must preview and obtain the required approval immediately before
`mutate`, `delete`, or `publish`. Preparation is not publication. Unlisted
external effects are unauthorized.

## Failure and audit rules

- Missing or unverifiable actor identity blocks packet claim.
- Capability escalation blocks the action and creates an incident record.
- Expired approval or session invalidates pending external effects.
- Every approval denial, capability failure, and unauthorized attempt is
  retained as evidence without storing secrets.
- A packet cannot be marked complete until actor metadata, approvals, and
  external effects reconcile with the handoff.
