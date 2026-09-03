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
  tracker/
    index.yaml
    shards/
    events/
    archive/index.yaml
  execution-tracker.md
  work-packets/
  archive/
    execution-tracker-archive.md
    work-packets/
  evidence/
  handoffs/
  skill-feedback.md
```

The lock is pinned to the last published protocol commit. The six
`SKILL.md` files in `~/.factory/skills` or another harness's global directory
must pass the lock's version and SHA-256 checks before work starts.

Existing ignored `.factory/` records are historical Factory session records.
They are preserved for auditability but are not the canonical project ledger.
New work uses `.contract-engineering/`.

The active YAML tracker is deliberately bounded. Keep
`.contract-engineering/tracker/index.yaml` at 25 rows or fewer; move
task-specific rows to declared `.contract-engineering/tracker/shards/*.yaml`
files when it reaches the limit, with no more than 50 rows per task shard.
Terminal packets are compacted by moving their YAML and tracker row into the
archive partition after user confirmation. Markdown tracker files are
generated projections. Event history is stored separately so day-to-day agent
context stays short while preserving the complete audit trail.

## Starting work

From the repository root:

1. Run the preflight in `docs/protocol-configuration.md` with the current
   harness skill directory.
2. Read the tracker, the applicable skills, and the assigned packet.
3. Confirm the packet owner, reviewer, locks, dependencies, scope, and
   acceptance criteria.
4. For a new task, create a packet from `templates/work-packet.yaml` and
   register its row in `.contract-engineering/tracker/index.yaml` or the
   appropriate declared shard.
5. Complete the six-step baseline before editing.

The packet's `baseline_refs` must include:

- the project's `.contract-engineering/protocol.lock.yaml`;
- the source revision used as the worktree base;
- any approved design or requirements record.

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

Scope expansion creates a new packet or an explicit decision. It is not
silently added to the current packet.

## Handoffs and recovery

A handoff transfers work, not completion. The receiver checks the base
revision, current diff, validation evidence, scope, and unresolved items.
The receiver records `accepted` or `rejected` status.

### Batch acceptance

A user may accept several explicitly named packets in one interaction when
their handoffs and evidence are available for review. The coordinator must
still record an independent accepted handoff for each packet, preserve each
packet's limitations and unresolved items, release each packet's locks, and
reconcile each tracker row. Batch acceptance must not close a packet whose
evidence, validation, required gate, or handoff is missing.

If an agent stops unexpectedly:

1. Leave the packet in `Interrupted` or `Handoff` rather than `Complete`.
2. Preserve the worktree and current evidence.
3. Record the last known action and exact next command.
4. Resume the session or record a takeover with the previous owner, reason,
   and recovery plan.
5. Release the old lock only after the takeover is recorded.

An abandoned worktree is not cleanup-authorized until its packet and locks
have been reconciled.

### Tracker sharding and compaction

Use the active YAML index for a small cross-task view and one or more YAML
shards per large task, named `<TASK-ID>.yaml` and declared by the index.
Markdown files are generated projections, not a second state format. The
tracker validator reads the index and all declared shards, rejects duplicate
or orphan rows, and enforces the 25-row index and 50-row shard limits. Event
files hold append-only history. At closure, move terminal packet files and
rows to the archive; never delete them as a shortcut. Review active packets
every 14 days and resolve them through the existing state machine rather than
adding a stale status. See `docs/tracker-storage.md`.

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

An accepted batch of protocol packets may be committed together as one
unreleased development revision. This does not publish a new protocol
release. The release packet must subsequently record the independent review,
attestation, provenance, artifact hashes, consumer migration notes, and
rollback plan before any consumer lock moves to the new immutable ref.

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
