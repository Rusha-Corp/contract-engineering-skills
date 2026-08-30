---
name: skill-evolution
version: 1.2.0
description: Keep skills and project guidance current by recording gaps, reviewing patterns, and applying user-approved updates.
---

## Revision history

- 1.2.0 (2026-08-30): Added project protocol-root and cross-harness
  synchronization guidance.
- 1.1.0 (2026-08-30): Distinguished invariants, procedures, and experiments,
  and added measured practice evolution.

# Skill Evolution

Skills distinguish three layers:

- **Invariants:** safety, authorization, data correctness, and traceability
  rules that may not be bypassed without explicit user approval.
- **Default procedures:** the recommended workflow, tools, thresholds, and
  evidence format.
- **Experiments:** bounded, reversible alternatives used to test whether a
  procedure improves outcomes.

Only the invariant layer is fixed by default. Procedures may evolve through
the practice-experiment workflow below.

## Core principle

Skills are living documents. Never silently work around a deficiency. Record the gap, expose its impact, and obtain a user decision.

## When to use

- At every task or iteration closure.
- When a skill mismatches the work or causes a blocker.
- During monthly pattern reviews.
- During quarterly audits and version refreshes.

Project packets, trackers, evidence, handoffs, and `skill-feedback.md` are
relative to `project.protocol_root` in the consuming project's
`protocol.lock.yaml`, defaulting to `.contract-engineering`. A legacy
`.factory` root must be explicitly recorded there.

## Skill gap triggers

Record a `SkillGap` when any of these occurs:

1. A required scenario is not covered.
2. A field, term, or instruction is unclear.
3. A field, rule, or section is redundant.
4. A state machine lacks a real workflow state.
5. Cleanup misses a debris or retention category.
6. The baseline cannot capture the technology or evidence needed.
7. Validation does not match the domain or risk.
8. A required tool, dependency, environment, or fixture is unavailable.
9. The user must override a rule because it is unsafe or counterproductive.
10. A decision, packet, handoff, or closure format causes ambiguity or repeated work.
11. A coding principle (DRY, SOLID, KISS, YAGNI) proved harmful or inadequate
    for a specific task.

## Skill index example

The active skill index should include each responsibility once, using the
canonical hyphenated identifier:

```yaml
skills:
  - phased-engineering-execution
  - cleanup-protocol
  - coding-principles
  - project-lifecycle
  - skill-evolution
```

## Skill gap schema

```yaml
skill_gap_id: PROJECT-SG001
task_id: PROJECT-T001
packet_id: PROJECT-T001-P001
discovered_at: ""
skill_file: ""
gap_type: missing|unclear|outdated|redundant|mismatch
severity: low|medium|high
description: ""
impact: ""
proposed_change: ""
evidence_refs: []
outcome_metric: ""
review_date: ""
user_notified: false
user_decision: pending|action|defer|reject
action_owner: ""
decision_ref: null
```

## Feedback procedure

1. **Discover:** Detect the mismatch during baseline, design, implementation, validation, cleanup, handoff, or closure.
2. **Record:** Add a complete `SkillGap` to the active packet and the
   project's `skill-feedback.md`.
3. **Handoff:** Include the gap ID, impact, and workaround status in the packet handoff.
4. **Review:** Aggregate gaps at closure and review recurring patterns monthly or sooner for high severity.
5. **Action:** Present each gap to the user for `action`, `defer`, or `reject`; update skills only after approval.
6. **Track:** Record the update, version, verification, owner, and resolution in the accumulator.

### Practice experiments

When a proposed rule is uncertain, do not install it as a permanent mandate.
Record a bounded experiment with an owner, scope, hypothesis, success metric,
expiry date, and rollback. Run it on a small number of packets, compare the
result with the prior procedure, and decide `retain`, `revise`, or `reject`.
Record the decision and evidence in the feedback accumulator.

Workarounds must be temporary, explicit, and linked to the gap. A workaround is not closure.

## Review cadence

| Cadence   | Trigger                              | Required action                                           |
| --------- | ------------------------------------ | --------------------------------------------------------- |
| Per-task  | Every task closure                   | Aggregate gaps and obtain a user decision                 |
| Monthly   | Calendar month or three similar gaps | Analyze patterns and batch safe updates                   |
| Quarterly | Calendar quarter                     | Audit all skills, examples, links, versions, and archives |

## Versioning rules

- Use semantic versions in each skill front matter.
- Increment the major version for scope, state machine, schema, or safeguard changes.
- Increment the minor version for new capabilities or materially expanded procedures.
- Increment the patch version for wording, examples, or link corrections.
- Add a dated revision entry for every approved update.
- Archive superseded skills with a redirect note; never leave two active names for one responsibility.
- Pin project usage to a skill version in the tracker or constitution.

## Skill update checklist

```yaml
update_id: PROJECT-SKILL-UPD001
skill_file: ""
timestamp: ""
triggered_by: []
changes:
  added: []
  modified: []
  removed: []
from_version: ""
to_version: ""
user_approved: false
verification:
  examples_updated: false
  schemas_checked: false
  cross_references_checked: false
  no_broken_links: false
  rendered_diagrams_checked: false
  trial_result: ""
  outcome_metric_met: false
```

## Accumulator: `skill-feedback.md`

```markdown
# Skill Feedback Log

## Active Gaps

| ID  | Skill | Type | Severity | Status | Owner |
| --- | ----- | ---- | -------- | ------ | ----- |

## Resolved Gaps

| ID  | Skill | Resolution | Version | Date | Closed by |
| --- | ----- | ---------- | ------- | ---- | --------- |

## Patterns

- Recurring gap themes:
- Skills needing major revision:
- New skill requests:
- Review date:
```

## Safeguards

- Never silently workaround a skill deficiency.
- Never update a skill without the required user approval.
- Never mark a gap resolved without evidence and a versioned change record.
- Never let the feedback accumulator grow without monthly review and resolution states.
- Never archive a skill without a redirect to its replacement.
- Never introduce a rule that contradicts the execution, cleanup, or lifecycle contracts.
- If a gap affects safety, data correctness, or user authorization, block the affected packet until resolved or explicitly accepted by the user.

## Cross-skill references

- Gap inventory field: `phased-engineering-execution/SKILL.md`
- Closure orchestration: `project-lifecycle/SKILL.md`
