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

## Scope and ownership

- Treat the packet's `scope.in` and `scope.out` as authoritative.
- Declare `semantic_scope` on new packets. If work affects or defines meaning,
  link an approved semantic contract and keep its uncertainty and evolution
  visible.
- Do not take over an active packet lock without a recorded recovery note.
- Use one branch and worktree per coding packet; do not edit global installed
  skills or another packet's worktree.
- Record design, data, authorization, trust-boundary, and security decisions
  in the project records rather than relying on chat.

## Validation and handoff

Before handoff, run the packet's complete validation plan, compare the diff
with packet scope, record evidence and limitations, and write a structured
handoff containing the base revision, head revision, changed resources,
failures, unresolved items, rollback notes, and next action. A packet is not
complete until its receiver accepts the handoff and the tracker and packet
agree on the terminal state.
