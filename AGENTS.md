# Agent instructions

This repository develops itself under the Contract-Driven Engineering
protocol.

## Before work

1. Read `.contract-engineering/protocol.lock.yaml`.
2. Run the preflight in `docs/protocol-configuration.md` with the harness's
   actual global skill directory.
3. Read `.contract-engineering/execution-tracker.md` and the applicable
   governed skills.
4. Work only from a claimed packet. Create or update the packet before
   editing if the task is not already tracked.

The project protocol root is `.contract-engineering`. The Factory global
skill directory is `~/.factory/skills`; other harnesses may use another
global directory but must use this same project lock and project records.

## Work isolation

- One coding packet uses one branch and one Git worktree.
- Never edit another packet's worktree or a global installed `SKILL.md`.
- Honor packet `scope.in` and `scope.out`; scope changes require a recorded
  decision before editing.
- Treat packet locks as ownership leases. Do not take over an active lock
  without a recovery note.

## Completion

Before handoff, run the packet validation plan, check the diff against
packet scope, record evidence, and write a structured handoff with the base
revision, head revision, changed resources, failures, unresolved items, and
next action. A packet is not complete because an agent says it is done.
The receiver must accept the handoff before the packet is closed.

For the complete self-hosting workflow, read
`docs/repository-development.md`.
