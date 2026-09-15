---
name: contract-design
description: Create or revise a Contract Engineering design contract after Superpowers brainstorming.
---

# Contract Design

Use Superpowers `brainstorming` and `writing-plans` for discovery and planning.
This skill translates the approved direction into
`.contract-engineering/designs/<TASK-ID>/design.yaml` and its artifact manifest.

## Rules

1. Read the protocol lock, tracker, approved design inputs, and claimed packet.
2. Record problem, users, constraints, alternatives, trust boundaries, data
   flows, security decisions, rollback, and required artifacts.
3. Create canonical source artifacts and derived sanitized artifacts where the
   design type requires them.
4. Request design, architecture, security, data, compatibility, operations,
   and visual reviews as applicable.
5. Stop before approval. Only the authenticated user can approve a design
   revision. Do not create implementation packets until admission passes.

Repository validators and CI are authoritative.
