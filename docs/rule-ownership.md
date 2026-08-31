# Protocol Rule Ownership

This document is the boundary map for the Contract-Driven Engineering
protocol. Each concern has one canonical owner. Other skills may reference
the concern, but they must not redefine its authoritative rules.

| Concern | Canonical owner | Primary records | Enforcement owner | Blocking authority |
| --- | --- | --- | --- | --- |
| Packet scope, state, dependencies, and gates | `phased-engineering-execution` | Work packet, tracker | Harness and record validator | Coordinator |
| Threat modeling, capabilities, secrets, and external effects | `security-assurance` | Threat model, security verification, incident | Harness security boundary | Security reviewer |
| Code architecture and implementation quality | `coding-principles` | Packet principles checks, cleanup scope | Harness and code checks | Code reviewer |
| Removal, deprecation, retention, and archive rollover | `cleanup-protocol` | Deprecation and cleanup records | Harness cleanup procedure | Reviewer or user by risk |
| Iteration sequencing, user verification, and closure | `project-lifecycle` | Closure record | Coordinator and harness | User or coordinator |
| Skill gaps, feedback, experiments, and skill versions | `skill-evolution` | Skill gap, feedback, update records | Protocol maintainer | User approval |
| Host installation, identity mapping, and native enforcement | Host adapter | Adapter inventory, consumer record | Target harness | Harness owner |
| Structural record validation | Harness implementation | Validator output, evidence | Target harness | Packet gate owner |

## Packet classes

Every packet is one of these classes:

- `single-domain`: one implementation or documentation responsibility.
- `cross-cutting`: one bounded protocol change that necessarily spans
  multiple owners; it must name each affected owner and why decomposition
  would create an inconsistent intermediate state.
- `parent-coordination`: sequencing and acceptance only; it does not implement
  child packet work.
- `child-implementation`: implementation delegated by a parent packet with an
  explicit dependency.

Cross-cutting does not mean ownerless. The packet still has one accountable
owner, and each secondary concern must remain subject to its canonical skill
and gate.

## Native harness enforcement

The harness is the enforcement authority for identity, capabilities,
approvals, scope, leases, runtime budgets, checkpoints, tool boundaries, and
external effects. A record declares intent; it does not grant permission.

If the harness cannot enforce a required control, it must record the missing
capability as a Skill Gap and block the affected operation. It must not
silently downgrade the rule to documentation.

Repository scripts, schemas, and CI checks may provide reference or
cross-check implementations, but they do not replace the harness's
responsibility to enforce the protocol during execution.
