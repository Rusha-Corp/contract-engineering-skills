# Developing This Repository

This repository is both the protocol source and a consumer of its own
protocol. Its development records are therefore committed under
`.contract-engineering/`, while host-specific skill installations remain
outside the repository.

## Canonical project state

The tracked project control plane is:

```text
.contract-engineering/
  protocol.lock.yaml
  execution-tracker.md
  semantic-contracts/
  work-packets/
  evidence/
  handoffs/
  skill-feedback.md
```

The lock is pinned to the last published protocol commit. The five
`SKILL.md` files in `~/.factory/skills` or another harness's global directory
must pass the lock's version and SHA-256 checks before work starts.

Existing ignored `.factory/` records are historical Factory session records.
They are preserved for auditability but are not the canonical project ledger.
New work uses `.contract-engineering/`.

## Starting work

From the repository root:

1. Run the preflight in `docs/protocol-configuration.md` with the current
   harness skill directory.
2. Read the tracker, the applicable skills, and the assigned packet.
3. Confirm the packet owner, reviewer, locks, dependencies, scope, and
   acceptance criteria.
4. For a new task, create a packet from `templates/work-packet.yaml` and
   register it in `.contract-engineering/execution-tracker.md`.
5. Complete the six-step baseline before editing.

For semantic-bearing work, the baseline also identifies affected terms,
boundaries, invariants, states, assumptions, consumers, and open questions.
Use `docs/semantics.md` and link the semantic contract from the packet.

The packet's `baseline_refs` must include:

- the project's `.contract-engineering/protocol.lock.yaml`;
- the source revision used as the worktree base;
- any approved design or requirements record.
- the semantic contract or decision record when the packet affects or defines
  system meaning.

## Parallel work

Concurrent coding packets use separate branches and worktrees:

```bash
git worktree add ../contract-engineering-skills-CENG-T003-P002 \
  -b agent/CENG-T003-P002
```

The worktree path and branch belong in the packet or session record. Agents
must not share a mutable checkout for concurrent coding work. Documentation
packets may share a checkout only when their scopes do not overlap and the
packet locks are clear.

Use packet locks for logical ownership even when worktrees provide physical
isolation. A worktree prevents file overwrites; it does not prevent two
agents from making incompatible changes to the same contract.

## Scope and validation

Before handoff:

1. Compare changed paths with the packet's allowed scope.
2. Confirm forbidden paths and unrelated files were untouched.
3. Run the packet's complete local validation plan.
4. Record commands, results, limitations, and evidence references.
5. Write the handoff with base revision, head revision, changed resources,
   failures, unresolved items, rollback notes, and next action.
6. Classify and redact evidence using `templates/evidence-policy.yaml`; never
   place credentials, session material, or unnecessary raw sensitive content
   in tracked records.
7. Link any safety, authorization, data, release, or agent-operation incident
   using `templates/agent-incident.yaml` before resuming affected work.
8. For semantic-bearing packets, state verified meanings, remaining ambiguity,
   semantic maturity, compatibility impact, and the next clarification action.

Scope expansion creates a new packet or an explicit decision. It is not
silently added to the current packet.

## Handoffs and recovery

A handoff transfers work, not completion. The receiver checks the base
revision, current diff, validation evidence, scope, and unresolved items.
The receiver records `accepted` or `rejected` status.

If an agent stops unexpectedly:

1. Leave the packet in `Interrupted` or `Handoff` rather than `Complete`.
2. Preserve the worktree and current evidence.
3. Record the last known action and exact next command.
4. Resume the session or record a takeover with the previous owner, reason,
   and recovery plan.
5. Release the old lock only after the takeover is recorded.

An abandoned worktree is not cleanup-authorized until its packet and locks
have been reconciled.

## Updating the protocol itself

Protocol changes are a two-stage operation:

1. Work against the currently locked published ref.
2. Update skills, templates, adapters, and migration guidance in a scoped
   packet.
3. Validate and publish the new protocol release.
4. In a follow-up lock update, change `protocol.ref`, release, versions, and
   hashes together.
5. Synchronize every harness installation and rerun preflight.

Do not make a lock point to an uncommitted worktree state. During a protocol
change, the lock describes the last stable release until the replacement is
published.

## Completion

The repository packet is complete only when:

- acceptance criteria pass;
- evidence is linked;
- the reviewer accepts the handoff;
- the diff is within scope;
- required protocol preflight passes;
- no unresolved high-severity gap is hidden in chat;
- locks are released or transferred;
- the tracker and packet agree on the terminal state.
