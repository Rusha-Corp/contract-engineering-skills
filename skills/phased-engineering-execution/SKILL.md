---
name: phased-engineering-execution
version: 2.8.0
description: Break engineering work into owned packets and execute it through evidence-based phases, gates, validation, and handoffs.
license: MIT
compatibility: Factory Droid, Hermes Agent, and any agent harness that reads SKILL.md files
---

## Revision history

- 2.8.0 (2026-11-13): Added an optional Explore step before P0 Foundations
  (T029). Added living spec guidance — spec documents may be updated after
  packet archive with versioning so prior state is recoverable (T030).
  Added ACDD — tests from acceptance_contract.criteria before implementation
  code (T031). Added mutation testing to validation rules (T032). Added
  risk-tiered review depth (T033).
- 2.8.0 (2026-11-13): Added mutation testing to the validation rules.
  Coding-domain packets SHOULD run mutation testing and record the score;
  a low score does not hard-block but is flagged for reviewer attention.
  Adapted from AIDLC's evals practice.
- 2.8.0 (2026-11-13): Added risk-tiered review depth. Low-risk packets get
  light review (automated checks + single reviewer), high-risk packets get
  deep review (multi-reviewer, manual evidence inspection). Adapted from
  AIDLC's playbook rule that verification is the constraint.
- 2.7.0 (2026-11-05): Added code-health gate to baseline and finish
  steps: inventory file size and dead code at baseline, record decisions
  in cleanup_scope at handoff. Moved packet schema, acceptance contract,
  approval gates, and handoff schema into references/ files to stay under
  500 lines. Requires lock v2 for per-file hashing of skill folders.
- 2.6.0 (2026-10-21): Require a human-signed owner on every new packet.
  Introduced the `implementor` role for agent identity, separating the
  human authority (owner) from the agent executor (implementor). The
  human owner signs scope authorization and handoff acceptance.
- 2.5.0 (2026-09-03): Made YAML tracker partitions canonical, added generated
  Markdown projections, append-only task event streams, bounded shard
  validation, and database-backed consumer guidance.
- 2.4.0 (2026-09-01): Added structured acceptance contracts, bounded tracker
  sharding, 14-day active packet review cadence, and release-gate correctness
  for version-tag pushes.
- 2.3.0 (2026-08-30): Added explicit batch acceptance and task-closure
  guidance while preserving per-packet evidence, handoffs, and release gates.
- 2.2.0 (2026-08-30): Added agent identity, trust-boundary, runtime-budget,
  durable-execution, evaluation, and reproducibility gates.
- 2.1.0 (2026-08-30): Added project protocol-lock and cross-harness
  preflight guidance.
- 2.0.0 (2026-08-30): Added the `open_questions` packet field required for
  spec-to-packet traceability.
- 1.1.0 (2026-08-30): Added deprecation/removal lifecycle, sunset criteria,
  exceptions, and explicit scope handling for enabling work.

# Phased Engineering Execution

Use for multi-step engineering work, shared resources, formal handoffs, browser audits, design approval, or data validation.

## Core rule

No implementation begins until the task has a baseline, a **human owner** who has signed the scope authorization, explicit scope, an approved design when required, and a passed data correctness gate when data affects the result.

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

- `docs/rule-ownership.md` defines the single canonical owner for each
  protocol concern and the allowed packet classes.
- `protocol.lock.yaml` selects the immutable protocol source and skill
  versions for the consuming project.
- `tracker/index.yaml` is the canonical active task-status index, relative to
  the configured project protocol root. Declared `tracker/shards/*.yaml`
  contain bounded task projections; `tracker/events/*.yaml` contains
  append-only task history.
- `execution-tracker.md` is a generated human-readable projection, not the
  canonical status source.
- `work-packets/<PACKET-ID>.yaml` is the packet source of truth, relative to
  the configured project protocol root.
- Terminal packet files and rows are retained in
  `archive/work-packets/` and `tracker/archive/index.yaml` after cleanup
  rollover; they are not duplicated in the active partition.
- The active YAML tracker index is capped at 25 packet rows. Additional
  active rows belong in declared task shards under
  `tracker/shards/<TASK-ID>.yaml`, with a 50-row cap per shard. The validator
  treats the index and shards as one partition and rejects duplicate, orphan,
  state-mismatched, or over-limit rows.
- Evidence, decisions, handoffs, cleanup records, and skill gaps are linked
  by ID relative to that same root.
- Chat is not the sole record of ownership, scope, approval, blocker, or completion.

The default project protocol root is `.contract-engineering`. Resolve it from
`project.protocol_root` in `protocol.lock.yaml`; a legacy project may
explicitly set it to `.factory` while migrating.

## Packet schema and acceptance contract

See [`references/packet-schema.md`](references/packet-schema.md) for the full
packet YAML schema, structured acceptance contract specification, and deprecation
and removal planning.

## Baseline procedure

Complete exactly these six steps before implementation:

1. Record the protocol lock ref, skill versions and hashes, source revision,
   environment, toolchain, configuration, and dependency versions.
2. Inventory affected files, routes, services, data sources, permissions, and navigation targets.
3. **Inventory file sizes and dead code:** identify any file in `scope.in`
   that exceeds the configured line limit (default 500). Identify dead code,
   stale artifacts, temporary files, orphaned tests, and unused dependencies
   in the affected scope. Record findings in `cleanup_scope`.
4. Capture current behavior, tests, screenshots, accessibility snapshots, fixtures, and data samples as immutable evidence.
5. Separate observed facts, assumptions, known limitations, and unavailable fixtures.
6. Register packets, owners, locks, acceptance criteria, and required Design
   and Data gates in `tracker/index.yaml` or its declared task shard. Append
   significant transitions to the task event stream.

## Ownership and locks

Every packet has one owner, one reviewer, one cleanup owner, dependencies, claim timestamp, exclusive resource locks, and a release condition. The cleanup owner may not remove resources owned by an active packet. A stale lock requires a takeover note in the tracker, with the prior owner, reason, and recovery plan.

The `packet_class` must match `docs/rule-ownership.md`. A
`cross-cutting` packet must name the affected concern owners and explain why
separate child packets would create an inconsistent intermediate state.
`parent-coordination` packets may sequence and accept work but must not
implement a child packet's scope.

For concurrent or side-effecting work, represent ownership with
`templates/packet-lease.yaml`. A lease has an expiry, heartbeat, atomic
renewal/release, and fencing token. An expired or revoked lease blocks writes
until takeover is recorded. Worktree isolation does not replace logical
ownership or protect external resources.

## Approval gates

See [`references/approval-gates.md`](references/approval-gates.md) for the
full specification of the Design, Data Correctness, Action Authorization,
Trust Boundary, Runtime Control, Durable Execution, Evaluation, and
Reproducibility gates.

## Packet state machine

The native harness must allow only these packet transitions:

| From | Allowed next states | Required condition |
| --- | --- | --- |
| `Planned` | `Claimed`, `Cancelled` | owner/lease or user disposition |
| `Claimed` | `DesignReview`, `DataReview`, `Ready`, `Interrupted`, `Cancelled` | claim, locks, and required gates |
| `DesignReview` | `DesignBlocked`, `DataReview` | authenticated design decision |
| `DesignBlocked` | `DesignReview`, `Cancelled` | revised proposal or disposition |
| `DataReview` | `DataBlocked`, `Ready` | data gate result |
| `DataBlocked` | `DataReview`, `Cancelled` | corrected evidence or disposition |
| `Ready` | `Implementing`, `Interrupted`, `Cancelled` | implementation authorization |
| `Implementing` | `Validation`, `Interrupted`, `Rework` | scoped changes and checkpoint |
| `Validation` | `Rework`, `Handoff`, `Interrupted` | validation results |
| `Rework` | `Implementing`, `Cancelled` | scope remains valid or disposition |
| `Handoff` | `Rework`, `Complete` | receiver rejection or authenticated acceptance |
| `Interrupted` | `Claimed`, `Implementing`, `Cancelled` | recovery review and fresh claim |
| `Cancelled` | none | terminal disposition |
| `Complete` | none in the packet lifecycle | archive/deprecation is a separate governed process |

No transition may skip a required gate or infer acceptance from a changed
tracker row. `Complete` requires a receiver-accepted handoff bound to the
packet revision, scope digest, changed-resource hashes, approval, and
validation evidence. `Interrupted` and `Cancelled` require a reason,
disposition, and recovery or closure path.

Deprecation, migration, sunset, and removal are governed by
`cleanup-protocol` records after packet completion; they are not packet
states.

Active packet records require a 14-day review cadence. An owner must resume,
recover as `Interrupted`, cancel, or hand off an unchanged packet at review;
`Stale` is not a packet state. Terminal packet YAML and its tracker row move
to the archive only after user confirmation or iteration closure, preserving
the handoff and evidence references.

## Living specs

Spec documents referenced in a packet's `baseline_refs` or
`design_decision_ref` are not frozen at archive time. A spec may be updated
after its packet is archived to reflect new understanding, corrected
requirements, or evolved design context — without re-opening the archived
packet.

### Rules

1. **Versioning:** every post-archive spec update records the prior version.
   The simplest mechanism is a revision history section at the top of the
   spec file (date, author, summary). The prior state is recoverable from
   git history and the spec's own changelog.
2. **No packet re-open:** updating a spec does not change the archived
   packet's state, evidence, or handoff. The packet remains terminal. The
   spec update is a documentation change, not a lifecycle event.
3. **Link the update:** if the spec change is significant, record it in the
   task event stream with the spec path, date, and summary. This keeps the
   canonical ledger traceable without re-opening the packet.
4. **Scope:** the update applies to the spec document only. Code, schema, or
   configuration changes triggered by the spec update require a new packet
   in the relevant task or a follow-up task.

### When to update a living spec

- The system evolved and the spec's assumptions are no longer accurate
- A later packet discovered information that should be reflected in the
  earlier spec for future readers
- The spec contains an error that would mislead a future agent

### When not to

- The change is trivial (typo, formatting) — just fix it without ceremony
- The spec describes a terminal decision that is still correct — leave it

## Phased execution

1. **Baseline:** capture six-step baseline and register packets.
2. **Explore (optional):** before P0, an agent may explore the codebase and
   produce a non-binding plan document. See [Explore step](#explore-step)
   below.
3. **P0 Foundations:** resolve shared primitives, contracts, routing, navigation, and blockers.
3. **Data Gate:** validate sources, schemas, permissions, fixtures, mappings, and failure states.
4. **P1 Implementation:** implement only approved, claimed packet scope. Write tests from the packet's `acceptance_contract.criteria` before implementation code (ACDD — see [Acceptance-criteria-driven development](#acceptance-criteria-driven-development) below).
5. **P2 Design Gaps:** resolve missing states or designs, obtain approval, then implement.
6. **P3 Cleanup:** after validation, execute the approved cleanup and removal scope through `cleanup-protocol`. Record `cleanup_scope.size_reviews` and `cleanup_scope.dead_code_review` decisions.
7. **Final Integration Audit:** rerun cross-packet, regression, accessibility, responsive, data, and documentation checks.
8. **Task Closure:** complete user verification, skill review, closure record, and archive decisions.

Each phase has entry criteria, exit criteria, evidence, and coordinator review.

## Explore step

The Explore step is an optional, non-binding phase that sits between Baseline
and P0 Foundations. It lets an agent read the codebase, identify relevant
patterns, and shape a plan before committing to a design packet.

### Purpose

OpenSpec's explore-before-propose practice shows that a short, no-stakes
exploration reduces rework: the agent discovers constraints, existing
abstractions, and likely failure modes before the design gate, so the first
design proposal is better grounded.

### What it is

- **Optional:** the agent may skip Explore and go straight to P0 Foundations.
- **Non-binding:** the plan document has no gate, no reviewer approval, and no
  state transition. It does not block the lifecycle.
- **No gated artifact:** the plan is not a Decision, not evidence, and not a
  packet state. It is a thinking aid — the agent may discard it entirely.
- **Pre-P0:** Explore happens after Baseline (packets registered) and before
  P0 Foundations (shared primitives resolved).

### What it produces

A plan document (markdown or notes) that may include:

- Relevant files, modules, and existing abstractions discovered
- Candidate approaches and their trade-offs
- Risks, unknowns, and open questions to resolve during P0
- A tentative implementation sequence

The document is not linked to the packet YAML and does not appear in the
tracker. If the agent's findings are significant enough to gate on, they
belong in a Decision record during P0, not in the explore plan.

### When to use it

Use Explore when the task touches unfamiliar code, has multiple viable
approaches, or has dependencies that are not yet understood. Skip it for
small, well-understood changes where the design is obvious from the baseline.

## Acceptance-criteria-driven development

ACDD (acceptance-criteria-driven development) is a practice for the P1
Implementation phase: tests are written from the packet's
`acceptance_contract.criteria` **before** the implementation code, not after.
This is adapted from AIDLC's ACDD practice.

### Procedure

1. **Read the acceptance contract.** Before writing any implementation code,
   read every criterion in `acceptance_contract.criteria`. Each criterion has
   an `id`, `statement`, `expected_result`, `verification_method`, and
   `failure_result`.
2. **Write a test for each criterion.** For each criterion, write a test (or
   test case) that would pass if the `expected_result` is met and fail if the
   `failure_result` occurs. The test maps directly to the criterion's `id`
   so traceability is automatic.
3. **Run the tests — they should fail.** The tests fail because the
   implementation does not exist yet. This confirms the tests are meaningful.
4. **Implement the code.** Write the minimum code to make the tests pass.
   The acceptance criteria define done, not the agent's intuition.
5. **Verify all criteria pass.** Every criterion's test must pass before
   transitioning to Validation.

### When to apply ACDD

ACDD applies to coding-domain packets with executable acceptance criteria
(`verification_method: execute`). For review-only criteria
(`verification_method: review` or `inspect`), the "test" is a checklist item
or review note, not an executable test.

### When not to apply

- **Design-only packets:** no implementation code, no tests needed.
- **Documentation packets:** the criteria are verified by review, not by
  executing code.
- **Packets with no acceptance_contract:** fall back to the standard
  implement-then-test workflow.

### Relationship to TDD

ACDD is a specialization of TDD. TDD says "write a test, see it fail, write
code to pass it." ACDD adds: "the test comes from the acceptance contract,
not from the developer's guess about what to test." This ensures the
implementation is grounded in the criteria the reviewer will check.

## Host integration

Host-specific approval and execution mechanisms are adapters around this
protocol. The host adapter must map its planning or approval mechanism to the
packet baseline, design decision, acceptance criteria, and evidence fields.
The core protocol does not require a particular coding assistant, CLI, IDE, or
workflow engine.

1. **During spec planning** — requirements gathered via AskUser, scope-in/out, and acceptance criteria are exactly the packet's `open_questions`, `scope`, and `acceptance_criteria`. Write them once, in the spec.
2. **On spec approval (first write)** — if the work is multi-step, touches shared resources, or needs a handoff, the agent's FIRST action after approval is to create the packet YAML with the approved spec's file path in `baseline_refs` (and `design_decision_ref` when the spec decided a design), set `claim_timestamp` and locks, and register it in `tracker/index.yaml` or the appropriate shard at state `Claimed` (transitioning to `Implementing` once coding starts). Append the transition to the task event stream. The approved spec counts as the Design Gate artifact; a separate Decision record is only needed if the design changes during implementation.
3. **Small single-file specs** — no packet. Instead add one event to the task event stream noting the spec path and resulting commit. Keeps the canonical ledger compact.
4. **Before ending any task or session** — update packet state, canonical tracker row, and event stream, then regenerate the Markdown projection. A task may never be called complete with a stale tracker.

### Batch acceptance and task closure

A reviewer may accept a coherent batch of packets in one interaction when the
packets are named explicitly and their scopes, evidence, and dependencies have
already been reviewed. Batch acceptance is a coordination convenience, not a
new packet state or a replacement for individual records.

For every packet in an accepted batch, the coordinator SHALL:

1. verify that the packet has its own evidence references and handoff;
2. record the receiver's accepted status and packet-specific notes in that
   handoff;
3. preserve documented limitations, skipped checks, and unresolved items;
4. move only packets whose acceptance criteria, evidence, and required gates
   are satisfied to `Complete`;
5. release that packet's locks and reconcile its canonical tracker row and
   generated projection atomically.

One packet's acceptance must not close another packet that lacks evidence,
handoff, required validation, or a recorded receiver decision. A task may
therefore contain a mix of completed, blocked, ready, and in-progress packets
after a batch acceptance.

## Agent procedure

### Start

1. Read and pass the project's protocol-lock preflight, then read the active
   tracker index, relevant task shard/events, requirements, applicable skills,
   and assigned packet.
2. Confirm the human owner's signed authorization, implementor identity,
   capabilities, risk tier, approval policy, owner, reviewer, cleanup owner,
   dependencies, locks, gates, and scope.
3. Claim the packet and complete the baseline before editing. Include the
   protocol lock path in `baseline_refs`.
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

Record state transition, changed resources, commands and results, evidence,
limitations, unresolved items, rollback notes, released locks, and the exact
next action. An interrupted agent leaves enough context for another agent to
resume without repeating exploration.

**Code-health at handoff:** before transitioning to `Handoff`, record
`cleanup_scope.dead_code_review` with both `baseline` and `handoff`
checkpoints. Every `cleanup_scope.dead_refs` entry must have a decision
(`remove`, `deprecate`, `retain`, `archive`, `false_positive`, or
`needs_evidence`). A `needs_evidence` decision blocks `Complete`. Every
changed file exceeding the configured line limit (default 500) must have a
`cleanup_scope.size_reviews` entry with a decision (`decompose`, `retain`
with rationale, or `defer` with `follow_up_ref`). The recorded decision is
hard-gated by the validator; whether to actually split or remove is the
agent's judgment, checked by the reviewer.

## Handoff schema

See [`references/handoff-schema.md`](references/handoff-schema.md) for the
full handoff YAML schema specification.

## Risk-tiered review

Review depth scales with risk. Authoring is cheap; verification is the
constraint. A flat "deep review everything" policy wastes reviewer capacity
on low-risk work and leaves less time for high-risk work. Adapted from
AIDLC's playbook rule.

### Risk tiers

| Tier | Trigger | Review depth |
| --- | --- | --- |
| **Low** | Documentation-only, single-file skill text, no code, no data, no external effects | Automated checks (validators, linters) + single reviewer approval |
| **Medium** | Code changes in a single domain, schema additions (non-breaking), new tests | Automated checks + single reviewer + targeted manual evidence review |
| **High** | Cross-cutting changes, security-domain, data migrations, external effects, breaking schema changes, production deployments | Automated checks + two independent reviewers + full manual evidence inspection |

### How to assign

The packet's `domain`, `packet_class`, and `scope` determine the tier. The
agent records the tier in the handoff:

```yaml
risk_tier: low|medium|high
```

If the agent and reviewer disagree on the tier, the higher tier wins.

### What changes by tier

- **Low:** the reviewer checks that automated validators pass and the change
  matches the packet scope. No line-by-line code review required.
- **Medium:** the reviewer additionally inspects the changed files and
  evidence to confirm the acceptance criteria are met.
- **High:** two reviewers independently check the change. At least one must
  be independent of the actor (not the same person who approved the design).
  The reviewer(s) inspect all evidence manually, including security and data
  correctness gates.

### Relationship to existing gates

Risk-tiered review does not replace gates. It adjusts the depth of human
review at handoff. All gates (Design, Data, Threat Model, Security
Verification) still run regardless of tier. The tier controls how much
manual inspection the reviewer performs on top of the gates.

## Validation rules

- **Coding:** type-check, lint, targeted tests, integration tests, build when
  applicable, and mutation testing when tooling is available (see
  [Mutation testing](#mutation-testing) below).
- **Browser:** direct URLs, reload, required viewports, keyboard navigation, real anchors, accessibility snapshots, console/network errors, and screenshots.
- **Design:** approved desktop/mobile artifacts, design tokens, interaction states, responsive behavior, and accessibility intent.
- **Data:** source, schema, filters, permissions, mapping, values, samples or row counts, and loading/empty/error/permission/stale/retry behavior, and reproducible results.
- **Documentation:** source links, terminology, examples, version references, and cross-reference checks.

## Mutation testing

Mutation testing measures test quality by injecting small defects (mutations)
into the code and checking whether the tests catch them. Tests that pass
despite mutations are asserting nothing meaningful. Adapted from AIDLC's
evals practice.

### When to run

Coding-domain packets SHOULD run mutation testing when tooling is available
for the language and framework (e.g., Stryker for JavaScript/TypeScript,
mutmut for Python, PIT for Java). It is not required when no mutation testing
tool supports the project's language or when the packet touches only
non-executable code (documentation, configuration schemas).

### How to record

Record the mutation score in the packet's evidence:

```yaml
validation_plan:
  - id: PROJECT-T001-P001-VAL001
    kind: test
    skill: phased-engineering-execution
    checks:
      - "mutation score >= 60% (or recorded limitation if tooling unavailable)"
    expected: "mutation score meets threshold or limitation is documented"
```

### Thresholds

- **60% or above:** acceptable. The test suite catches most injected defects.
- **Below 60%:** flagged for reviewer attention. The agent SHOULD document
  which survivors are expected (e.g., equivalent mutations) and which indicate
  a real gap. The reviewer decides whether to accept or send to Rework.
- **No score (tooling unavailable):** record the limitation in evidence. The
  packet is not blocked, but the reviewer is aware that mutation quality was
  not measured.

### Why not a hard gate

Mutation testing tooling is not universally available, and mutation scores
vary by domain (UI code typically scores lower than business logic). A hard
gate would block packets in environments without tooling. Instead, the score
is evidence for the reviewer to evaluate.

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

### Shared protocol release boundary

Changes to this repository's skills, templates, adapters, or guidance may be
committed as an unreleased development revision after their packet validation
passes. A consuming project's lock SHALL continue to reference the last
published immutable release until the replacement release is reviewed and
published. Do not update a consumer lock to an uncommitted or merely pushed
development revision.

Before publishing a replacement release, record the changed skill versions,
per-file hashes, migration notes, consumer impact, validation evidence,
independent release review, attestation, provenance, and rollback reference.
After publication, synchronize every harness installation from the same
immutable ref and rerun preflight before resuming work under the new lock.

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

- Cleanup mechanics: `cleanup-protocol/SKILL.md`
- Skill gap review: `skill-evolution/SKILL.md`
- Iteration orchestration: `project-lifecycle/SKILL.md`
- Coding principles: `coding-principles/SKILL.md`
- Security assurance: `security-assurance/SKILL.md`
