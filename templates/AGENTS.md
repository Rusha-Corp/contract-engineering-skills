# Contract-Driven Engineering

This file is a repository-level bootstrap for consumers of the
Contract-Driven Engineering protocol. Copy it to the consuming repository's
`AGENTS.md`, or adapt it to the host's equivalent project-instruction file
(`CLAUDE.md`, `.cursorrules`, and so on). Keep the full rules in the pinned
protocol skills and linked project documents; do not duplicate them here.

## Before editing

1. Read `.contract-engineering/protocol.lock.yaml` (or the `protocol_root`
   declared by that lock).
2. Run the preflight in `docs/protocol-configuration.md` with this harness's
   actual global skill directory.
3. Read the execution tracker, applicable governed skills, and the assigned
   work packet.
4. Work only from a claimed packet. Create or update the packet and tracker
   entry before editing when the task is not already tracked.
5. At cleanup or iteration closure, roll terminal packet files and tracker
   rows into the configured archive partition as described by the
   `cleanup-protocol` skill. Use native harness tooling; no Python runtime or
   repository archive command is required.
6. Keep `execution-tracker.md` at 25 rows or fewer. Shard larger task views
   into `tracker-shards/<TASK-ID>.md` with at most 50 rows per shard; the
   validator checks uniqueness, ownership, and archive partitioning.

## Scope and ownership

- Treat the packet's `scope.in` and `scope.out` as authoritative.
- Do not take over an active packet lock without a recorded recovery note.
- Use one branch and worktree per coding packet; do not edit global installed
  skills or another packet's worktree.
- Record design, data, authorization, trust-boundary, and security decisions
  in the project records rather than relying on chat.
- Review active packets every 14 days. Resume, interrupt with a recovery note,
  cancel, or hand off them; never create a `Stale` state or archive active
  work.

## Validation and handoff

Before handoff, run the packet's complete validation plan, compare the diff
with packet scope, record evidence and limitations, and write a structured
handoff containing the base revision, head revision, changed resources,
failures, unresolved items, rollback notes, and next action. A packet is not
complete until its receiver accepts the handoff and the tracker and packet
agree on the terminal state.
