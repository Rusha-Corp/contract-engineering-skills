---
name: coding-principles
version: 1.2.0
description: Enforce DRY, SOLID, KISS, YAGNI, composition, defensive coding, and cross-packet architecture alignment during coding implementation and validation.
license: MIT
compatibility: Factory Droid, Hermes Agent, and any agent harness that reads SKILL.md files
---

## Revision history

- 1.2.0 (2026-08-30): Added project protocol-lock and cross-harness
  synchronization guidance.
- 1.1.0 (2026-08-30): Added compatibility, evolutionary architecture, and
  fitness-function guidance while refining YAGNI for necessary enabling work.

# Coding Principles

Use this skill for coding-domain packets during `Implementing` and
`Validation` states. It complements
`phased-engineering-execution/SKILL.md`; it does not replace packet ownership,
design gates, data gates, cleanup, or handoff requirements.

## Core rule

**A packet that passes tests but violates architecture principles is not
complete.**

Principles are review and validation gates. Record violations in
`cleanup_scope`, `skill_gaps`, or the packet decision log instead of silently
accepting them.

Before coding work, pass the consuming project's protocol-lock preflight.
Use the skill version selected by `protocol.lock.yaml`, and keep coding
packets, evidence, and handoffs relative to its `project.protocol_root`,
which defaults to `.contract-engineering`. A legacy `.factory` root must be
explicitly recorded in the lock.

## Principle checks

### DRY

Search the existing codebase, completed packets, and prior handoffs in the
same domain before writing new logic. Reuse established abstractions and
config-driven sources of truth. Flag duplicated utilities, mappings, fixtures,
or workflows in `cleanup_scope`, including duplication introduced by the
current packet. Cross-packet DRY requires reading prior domain handoffs before
claiming a packet; record a `skill_gap` if an existing abstraction is
inadequate rather than creating a competing pattern silently.

### SOLID

**Single Responsibility:** Each module, function, and packet should have one
reason to change. Split a packet if its scope spans three or more unrelated
domains, and create separate packets with explicit dependencies.

**Open/Closed:** Prefer extension over modification when adding behavior.
Use registries, adapters, configuration, composition, or well-scoped
interfaces instead of branching through stable code paths.

**Liskov Substitution:** Subtypes and implementations must preserve the
contracts of the abstractions they replace. Check input, output, error, and
lifecycle behavior at every substitution boundary.

**Interface Segregation:** Keep interfaces focused on the consumers that need
them. Do not force components, services, or tests to depend on unrelated
methods or broad convenience interfaces.

**Dependency Inversion:** Depend on stable interfaces and inject
dependencies, don't hardcode service construction, environment values,
storage locations, or infrastructure clients inside business logic.

### KISS

Choose the simplest viable approach that satisfies the acceptance criteria,
existing architecture, and validation plan. If you need to explain it to a
junior engineer, it's too complex. At the design gate, the reviewer must
explicitly confirm: `simplest viable approach`.

### YAGNI

Do not add speculative product behavior, flags, abstractions, compatibility
paths, or configuration for future use. Necessary migration, compatibility,
security, observability, and safe-removal work is allowed when recorded in an
approved decision or child packet with acceptance criteria. Record unrelated
future ideas as deferred packets, not code in the current packet.

### Composition over inheritance

Favor wrappers, decorators, higher-order functions, adapters, and injected
collaborators over new inheritance hierarchies. Any new inheritance must be
justified in the packet decision record, including why composition would not
preserve the required contract.

### Fail fast and defensive programming

Validate inputs and responses at system boundaries. Preserve actionable
errors, use explicit failure states, and do not swallow exceptions. A fallback
must be documented, bounded, and covered by a test that proves it is safe.

### Explicit over implicit

Avoid global state mutations, monkey-patching, implicit coercion, hidden
side effects, and magic conventions. Make dependencies, transformations,
permissions, organization scope, and lifecycle transitions explicit.

## Evolutionary architecture and compatibility

For important architecture boundaries, prefer small measurable fitness
functions over prose-only claims. Useful checks include contract schema and
dependency validation, layer/import rules, rendered K8s invariants, API
compatibility tests, and stale deprecation detection.

When changing a public or shared boundary, use a parallel migration where
practical: introduce the replacement, migrate consumers, observe compatibility,
then remove the old path in a separate packet. Document stability, versioning,
deprecation, and sunset behavior in the interface contract. Keep changes small
and reversible so a failed migration can be rolled back without restoring
unrelated work.

## Cross-packet architecture alignment

Before implementation:

1. Read `src/architecture.md` or `ARCHITECTURE.md` if either exists.
2. Read the `domain` field and handoff of every recent completed packet in the
   same domain.
3. Reuse prior abstractions, identifiers, evidence, and validation patterns.
4. Record a `skill_gap` when prior abstractions are inadequate, contradictory,
   or missing.

During validation, run the project's import graph check and layer violation
check when available. If no project command exists, record that fact and use
the nearest static dependency analysis available. Cross-packet violations
must block completion until corrected or explicitly accepted by the reviewer.

## Second packet rule

If this is the second or later agent packet in a domain, the agent **must**
read the first packet's handoff, reuse its abstractions, and record a
`skill_gap` if those abstractions are inadequate. Do not silently create
competing patterns. This rule supplements, and does not override, ownership,
locks, dependencies, or scope rules in
`phased-engineering-execution/SKILL.md`.

## Validation integration

Add a `principles` section to the packet `validation_plan`, using the existing
execution skill's list-based validation format:

```yaml
validation_plan:
  - id: PROJECT-T001-P001-VAL001
    kind: type-check
    command: "npm run type-check"
    expected: "exit 0"
  - id: PROJECT-T001-P001-VAL002
    kind: principles
    skill: "coding-principles"
    checks:
      - "Existing abstractions and completed same-domain handoffs were read"
      - "DRY, SOLID, KISS, YAGNI, composition, and explicit-boundary checks passed"
      - "Deprecation, compatibility, fitness-function, and dependency-freshness checks passed where applicable"
      - "Import graph and layer violation checks passed or are documented unavailable"
    expected: "no unresolved principle violations"
```

The packet remains in `Validation` or moves to `Rework` when a principles
check fails. A passing test suite is not sufficient evidence for this check.

## Cleanup integration

Map principle violations into the cleanup protocol:

| Violation                                                        | Cleanup risk                                      |
| ---------------------------------------------------------------- | ------------------------------------------------- |
| Duplicated utilities, mappings, or fixtures                      | Medium                                            |
| God modules or SOLID single-responsibility breaches              | High when blast radius is broad, otherwise medium |
| Speculative YAGNI code or unused configuration                   | Low                                               |
| Hidden global state, hardcoded dependencies, or layer violations | Medium or high based on blast radius              |

Record candidates in `cleanup_scope` before removal. Execute cleanup only
under `cleanup-protocol/SKILL.md`, after validation, with required reviewer or
user approval.

## Safeguards

- Never add a new abstraction before searching for an existing one.
- Never mark a packet complete solely because tests pass.
- Never silently expand acceptance criteria with speculative features.
- Never bypass dependency injection with hardcoded service or infrastructure
  construction.
- Never hide exceptions, mutate global state, or cross an architecture layer
  without an explicit approved decision.

## Cross-skill references

- Packet states, schema, gates, and handoffs:
  `phased-engineering-execution/SKILL.md`
- Security threat modeling and verification:
  `security-assurance/SKILL.md`
- Cleanup risk tiers and execution:
  `cleanup-protocol/SKILL.md`
- Skill gaps and versioned updates:
  `skill-evolution/SKILL.md`
- Iteration sequencing and closure:
  `project-lifecycle/SKILL.md`
