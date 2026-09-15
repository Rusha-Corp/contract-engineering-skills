# Contract Engineering supervisor workflow

The supervisor coordinates, but does not replace, the repository validators
or user approval.

## Order of operations

```text
Superpowers brainstorming
→ Contract design
→ User design and visual review
→ Superpowers writing-plans
→ Packet creation
→ Packet admission
→ Superpowers implementation
→ Validation, evidence, and handoff
→ Receiver acceptance
```

The supervisor must stop when a design is missing, an artifact hash is stale,
a required review is pending, packet scope is uncovered, a dependency is
incomplete, a lock conflicts, or a handoff lacks evidence.

Superpowers remains separately installed and owns brainstorming, plans,
worktrees, TDD, debugging, subagents, reviews, and branch finishing.
Contract Engineering owns design contracts, visual review, admission,
packet scope, resources, evidence, handoffs, and audit records.

## Rollback

Revert to the last accepted packet handoff. Preserve the superseded records,
release locks through the state machine, and do not delete evidence or mutate
the Superpowers installation.
