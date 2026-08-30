---
name: phased-engineering-execution
version: 1.1.0
description: Break engineering work into owned packets and execute it through evidence-based phases, gates, validation, and handoffs.
---

## Revision history

- 1.1.0 (2026-08-30): Added deprecation/removal lifecycle, sunset criteria,
  exceptions, and explicit scope handling for enabling work.

# Phased Engineering Execution

Use for multi-step engineering work, shared resources, formal handoffs, browser audits, design approval, or data validation.

## Core rule

No implementation begins until the task has a baseline, an owner, explicit scope, an approved design when required, and a passed data correctness gate when data affects the result.

## Shared identifiers

Use these immutable formats everywhere:

```text
Task:     <PROJECT>-T<NNN>
Packet:   <TASK-ID>-P<NNN>
Evidence: <PACKET-ID>-EV<NNN>
Decision: <PACKET-ID>-DEC<NNN>
Handoff:  <PACKET-ID>-HO<NNN>
SkillGap: <PROJECT>-SG<NNN>
Closure:  <TASK-ID>-CLS<NNN>
```

Never reuse an identifier after supersession or cancellation.

## Required records

- `.factory/execution-tracker.md` is the task status source of truth.
- `.factory/work-packets/<PACKET-ID>.yaml` is the packet source of truth.
- Evidence, decisions, handoffs, cleanup records, and skill gaps are linked by ID.
- Chat is not the sole record of ownership, scope, approval, blocker, or completion.

## Packet schema

```yaml
packet_id: PROJECT-T001-P001
task_id: PROJECT-T001
phase: P0_FOUNDATIONS
domain: coding|browser|design|data|documentation
title: "Short measurable title"
objective: "Verifiable outcome"
scope:
  in: []
  out: []
owner: "agent-or-user"
reviewer: "agent-or-user"
cleanup_owner: "agent-or-user"
dependencies: []
locks: []
claim_timestamp: ""
baseline_refs: []
design_decision_ref: null
data_gate_ref: null
acceptance_criteria: []
validation_plan: []
cleanup_scope:
  dead_refs: []
  stale_refs: []
  temp_refs: []
skill_gaps: []
stability: stable|beta|experimental|deprecated
deprecation_refs: []
migration_dependencies: []
removal_criteria: []
exception_refs: []
sunset_target: ""
state: Planned
evidence_refs: []
handoff_ref: null
```

`cleanup_scope` and `skill_gaps` are inventories and references only. Cleanup execution belongs to `cleanup-protocol`; gap review belongs to `skill-evolution`.

### Deprecation and removal planning

Any public or shared surface that is being replaced or removed SHALL have a
deprecation record before implementation begins. This includes APIs, routes,
configuration keys, environment variables, K8s resources, contracts,
dependencies, feature flags, and shared abstractions.

Each deprecation record SHALL identify the replacement, owner, affected
consumers, migration steps, announcement date, review date, sunset target,
removal criteria, evidence, and rollback or retention plan. A deprecation
window is a default, not a universal constant: its duration is selected by
consumer impact and risk, and an exception must be approved and expire.

Required lifecycle:

```text
Active -> Deprecated -> Migration -> SunsetEligible -> RemovalReview
RemovalReview -> Removed -> Verified
Migration -> RetainedByException -> Migration
RemovalReview -> RetainedByException
```

`RetainedByException` requires an owner, reason, success measure, review date,
expiry date, and rollback plan. A public or shared surface SHALL NOT be
removed while known consumers remain, the removal criteria are unmet, or an
exception has expired.

## Baseline procedure

Complete exactly these six steps before implementation:

1. Record source revision, environment, toolchain, configuration, and dependency versions.
2. Inventory affected files, routes, services, data sources, permissions, and navigation targets.
3. Inventory likely dead code, stale artifacts, temporary files, orphaned tests, and unused dependencies.
4. Capture current behavior, tests, screenshots, accessibility snapshots, fixtures, and data samples as immutable evidence.
5. Separate observed facts, assumptions, known limitations, and unavailable fixtures.
6. Register packets, owners, locks, acceptance criteria, and required Design and Data gates in the tracker.

## Ownership and locks

Every packet has one owner, one reviewer, one cleanup owner, dependencies, claim timestamp, exclusive resource locks, and a release condition. The cleanup owner may not remove resources owned by an active packet. A stale lock requires a takeover note in the tracker, with the prior owner, reason, and recovery plan.

## Approval gates

### Design Gate

Required for layout, behavior, workflow, architecture, schema, or user-facing interaction changes. Link an existing approved design or record a `Decision` with proposal, alternatives considered, acceptance criteria, and approver. Missing approval enters `DesignBlocked`.

### Data Correctness Gate

Required when APIs, databases, configuration, fixtures, analytics, or rendered values affect the result. Record source/version, request or query, filters, organization scope, permissions, expected schema, mapping, samples or row counts, loading/empty/error/permission/stale/retry behavior, and reproducible results. Failure enters `DataBlocked`; presentation work must not hide unverified data.

## Packet state machine

```mermaid
stateDiagram-v2
    [*] --> Planned
    Planned --> Claimed: owner and locks
    Claimed --> DesignReview: design required
    Claimed --> DataReview: design approved or not required
    DesignReview --> DesignBlocked: approval missing
    DesignReview --> DataReview: approved
    DesignBlocked --> DesignReview: proposal revised
    DataReview --> DataBlocked: evidence fails
    DataReview --> Ready: gate passes
    DataBlocked --> DataReview: data corrected
    Ready --> Implementing
    Implementing --> Validation
    Validation --> Rework: validation fails
    Rework --> Implementing: scope remains valid
    Validation --> Handoff: validation passes
    Handoff --> Rework: receiver rejects
    Handoff --> Complete: receiver accepts
    Complete --> Deprecated: replacement required
    Deprecated --> Migration: consumers identified
    Migration --> SunsetEligible: removal criteria met
    Migration --> RetainedByException: approved exception
    RetainedByException --> Migration: exception review
    SunsetEligible --> RemovalReview: evidence review
    RemovalReview --> Removed: approval and validation
    RemovalReview --> RetainedByException: risk or consumer remains
    Removed --> Verified: regression and runtime checks
    Complete --> [*]
```

## Phased execution

1. **Baseline:** capture six-step baseline and register packets.
2. **P0 Foundations:** resolve shared primitives, contracts, routing, navigation, and blockers.
3. **Data Gate:** validate sources, schemas, permissions, fixtures, mappings, and failure states.
4. **P1 Implementation:** implement only approved, claimed packet scope.
5. **P2 Design Gaps:** resolve missing states or designs, obtain approval, then implement.
6. **P3 Cleanup:** after validation, execute the approved cleanup and removal scope through `cleanup-protocol`.
7. **Final Integration Audit:** rerun cross-packet, regression, accessibility, responsive, data, and documentation checks.
8. **Task Closure:** complete user verification, skill review, closure record, and archive decisions.

Each phase has entry criteria, exit criteria, evidence, and coordinator review.

## Spec mode integration

Droid sessions default to spec mode: every write is gated behind an approved spec (ExitSpecMode). Spec mode is the front gate; this skill is the ledger behind it. The mapping is mandatory whenever a session runs in spec mode:

1. **During spec planning** — requirements gathered via AskUser, scope-in/out, and acceptance criteria are exactly the packet's `open_questions`, `scope`, and `acceptance_criteria`. Write them once, in the spec.
2. **On spec approval (first write)** — if the work is multi-step, touches shared resources, or needs a handoff, the agent's FIRST action after approval is to create the packet YAML with the approved spec's file path in `baseline_refs` (and `design_decision_ref` when the spec decided a design), set `claim_timestamp` and locks, and register it in the tracker at state `Claimed` (transitioning to `Implementing` once coding starts). The approved spec counts as the Design Gate artifact; a separate Decision record is only needed if the design changes during implementation.
3. **Small single-file specs** — no packet. Instead add one line to the tracker's session log noting the spec path and resulting commit. Keeps the ledger cheap enough to actually maintain.
4. **Before ending any task or session** — update packet state and tracker row. A task may never be called complete with a stale tracker. Merged code with a tracker row still saying Implementing/Validation is a process failure, not a formality.

## Agent procedure

### Start

1. Read the tracker, requirements, applicable skills, and assigned packet.
2. Confirm owner, reviewer, cleanup owner, dependencies, locks, gates, and scope.
3. Claim the packet and complete the baseline before editing.
4. Confirm all applicable Skill versions are pinned in the tracker or packet.

### Work

1. Modify only packet-scoped resources.
2. Use project sources of truth and existing architecture.
3. Update tests and evidence as behavior changes.
4. Record decisions, blockers, scope changes, cleanup refs, and skill gaps immediately.
5. Create a new packet for discovered work instead of silently expanding scope.
6. If safe delivery requires migration, compatibility, security, observability,
   or cleanup work outside the packet, record a scoped decision or child packet.
   Do not silently add speculative product scope.
7. If this is a coding-domain packet, load and follow
   `coding-principles/SKILL.md`.

### Finish or hand off

Record state transition, changed resources, commands and results, evidence, limitations, unresolved items, rollback notes, released locks, and the exact next action. An interrupted agent leaves enough context for another agent to resume without repeating exploration.

## Handoff schema

```yaml
handoff_id: PROJECT-T001-P001-HO001
packet_id: PROJECT-T001-P001
sender: "agent"
receiver: "agent-or-user"
summary: "What changed and why"
changed_resources: []
validation_results: []
evidence_refs: []
skill_gaps: []
unresolved_items: []
rollback_notes: []
requested_next_action: ""
receiver_status: pending|accepted|rejected
receiver_notes: ""
```

A handoff is complete only after the receiver records acceptance or rejection with reasons.

## Validation rules

- **Coding:** type-check, lint, targeted tests, integration tests, and build when applicable.
- **Browser:** direct URLs, reload, required viewports, keyboard navigation, real anchors, accessibility snapshots, console/network errors, and screenshots.
- **Design:** approved desktop/mobile artifacts, design tokens, interaction states, responsive behavior, and accessibility intent.
- **Data:** source, schema, filters, permissions, mapping, values, samples or row counts, and loading/empty/error/permission/stale/retry behavior, and reproducible results.
- **Documentation:** source links, terminology, examples, version references, and cross-reference checks.

### Pre-push validation rule (mandatory)

CI runs cost money, and a red run wastes both money and wall-clock time.
Pushing code that a local command could have failed is a process violation,
not bad luck.

1. Every work packet's `acceptance_criteria` and `validation_plan` MUST cover
   the full local validation suite for its domain — lint, typecheck, tests,
   and build where applicable — and these MUST be executed and recorded in
   `evidence_refs` BEFORE any commit is pushed. "Should pass in CI" is not
   evidence.
2. If a validation step genuinely cannot run locally (no Docker, no cluster),
   record that limitation in the packet before pushing; CI then becomes the
   first check of that step, not the only one.
3. A CI failure on a step that was locally runnable sends the packet to
   `Rework`, and the tracker post-mortem names the skipped step.
4. Timing-sensitive tests must be deterministic (injected clocks, no real
   sleeps) so local green reliably predicts CI green.

Complete a packet only when acceptance criteria pass, evidence is linked, the
reviewer accepts the handoff, deprecation/removal criteria are satisfied or
explicitly dispositioned, and locks are released.

For coding-domain packets, include a principles validation step in the
packet's `validation_plan`:

```yaml
validation_plan:
  - id: PROJECT-T001-P001-VAL001
    kind: principles
    skill: "coding-principles"
    checks:
      - "same-domain handoffs and existing abstractions were reviewed"
      - "principle violations are absent or recorded for approved cleanup"
      - "import graph and layer checks passed or are documented unavailable"
    expected: "no unresolved principle violations"
```

## Safeguards

- Never overwrite another agent's uncommitted work.
- Never bypass a dependency or failed gate.
- Never claim behavior or data validity without reproducible evidence.
- Never add hardcoded configuration when a source of truth exists.
- Never perform cleanup during active implementation.
- Never remove shared resources without rollback notes and required approval.
- Keep scoped validation during work and full validation at phase boundaries.

## Cross-skill references

- Cleanup mechanics: `~/.factory/skills/cleanup-protocol/SKILL.md`
- Skill gap review: `~/.factory/skills/skill-evolution/SKILL.md`
- Iteration orchestration: `~/.factory/skills/project-lifecycle/SKILL.md`
- Coding principles: `~/.factory/skills/coding-principles/SKILL.md`
