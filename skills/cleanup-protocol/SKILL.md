---
name: cleanup-protocol
version: 2.4.0
description: Remove dead code, stale artifacts, and temporary debris after validation using risk-tiered, auditable procedures.
license: MIT
compatibility: Factory Droid, Hermes Agent, and any agent harness that reads SKILL.md files
---

## Revision history

- 2.4.0 (2026-09-03): Made YAML tracker partitions canonical and Markdown
  files generated projections; added event-stream and database-consumer
  archive guidance.
- 2.3.0 (2026-09-01): Added bounded tracker index cap, task-shard support,
  14-day active packet review cadence, and terminal-only compaction rules.
- 2.2.0 (2026-08-30): Added evidence classification, redaction, secret,
  access, encryption, telemetry, and incident-linkage controls.
- 2.1.0 (2026-08-30): Added project protocol-root and cross-harness
  synchronization guidance.
- 2.0.0 (2026-08-30): Added the required deprecation review date to the
  record schema.
- 1.1.0 (2026-08-30): Added deprecation records, surface-specific dead-code
  evidence, removal gates, and separated inventory from execution.

# Cleanup Protocol

Use this skill only after implementation validation, during P3 Cleanup, or at iteration end.

## Project record root

Read `protocol.lock.yaml` before cleanup. Unless the lock sets another
`project.protocol_root`, project trackers, work packets, evidence, handoffs,
cleanup records, archives, and feedback are relative to
`.contract-engineering`. A legacy `.factory` root is valid only when it is
explicitly recorded in the lock. Never clean a global skill directory as if
it were project records.

## When to use

- After a packet reaches `Validation` with passing results.
- During the execution framework's `P3 Cleanup` phase.
- Before iteration closure and tracker archival.
- When active packet, evidence, or generated-file directories show bloat.

## Inventory before action

### Dead code

Identify and record:

- unreachable functions, classes, modules, and routes;
- orphaned tests and fixtures;
- unused exports and imports;
- deprecated or unused dependencies;
- commented-out code blocks;
- empty or boilerplate-only files.
- duplicate utilities introduced by DRY violations.

Record candidates in the packet's `cleanup_scope.dead_refs` with evidence, risk, and proposed action. Candidate inventory is separate from execution; do not describe a removed item as merely identified.

### Stale artifacts

Identify and record:

- outdated baselines, screenshots, accessibility snapshots, and data samples;
- superseded evidence;
- temporary environment files, feature flags, and debug configurations;
- build debris and generated outputs outside intended directories;
- superseded decisions, trackers, and handoffs.

Record candidates in `cleanup_scope.stale_refs`.

### Deprecation records

Use a deprecation record for any public or shared surface that is replaced,
made obsolete, or scheduled for removal. The record must include:

```yaml
deprecation_id: PROJECT-DEP001
target: ""
target_type: api|route|config|env|k8s|contract|dependency|feature_flag|code
status: Active|Deprecated|Migration|SunsetEligible|RemovalReview|Removed|Verified|RetainedByException
owner: ""
reviewer: ""
replacement: ""
affected_consumers: []
announced_at: ""
review_date: ""
sunset_target: ""
removal_criteria: []
migration_steps: []
evidence_refs: []
rollback_plan: ""
exception_ref: null
```

Deprecation is not removal. Mark the target `Deprecated` first, provide a
replacement and migration path, observe or confirm consumers, and only then
move to `SunsetEligible` and `RemovalReview`. Public API records should also
update interface documentation, mark the OpenAPI item as deprecated, and use
the HTTP `Deprecation` and `Sunset` response headers when applicable.

### Dead-code proof and decisions

Every candidate must receive one decision: `remove`, `deprecate`, `retain`,
`archive`, `false_positive`, or `needs_evidence`. The evidence must match the
surface:

- Code: repository references, imports, exports, generated files, and tests.
- Dependency: direct and transitive consumers, lockfile impact, license and
  security status, and replacement availability.
- Route or API: repository consumers, interface documentation, access metrics,
  client migration status, and compatibility tests.
- Configuration or environment variable: manifests, templates, runtime
  usage, documentation, and deployment consumers.
- Feature flag: owner, flag category, enabled-state evidence, and expiry.
- K8s or infrastructure resource: rendered references, live consumers,
  ownership, rollback, and migration impact.

Static search is evidence, not proof, for externally consumed surfaces.

## Risk tiers

| Risk   | Examples                                                              | Authority              | Required rollback                             |
| ------ | --------------------------------------------------------------------- | ---------------------- | --------------------------------------------- |
| Low    | Unused export, empty file, superseded screenshot                      | Agent may remove       | Git revert or restore from archive            |
| Medium | Orphaned test, dependency pruning, tracker archive                    | Reviewer approval      | Git revert, restore test, or archive restore  |
| High   | Shared utility, config, API removal, destructive data or state change | User approval required | Written rollback steps and preserved evidence |

High-risk approval must be recorded in the cleanup checklist before execution.

## Execution rules

1. Never delete or modify cleanup candidates during active implementation.
2. Record every candidate in `cleanup_scope` before action.
3. Preserve auditability by archiving trackers and evidence before deletion.
4. Update imports, references, manifests, and tests when removing code.
5. Confirm no active packet, lock, or handoff references an artifact before archiving.
6. Run targeted validation after each removal group and full validation before closure.
7. Treat principle violations, such as god modules from SOLID-S breaches, as
   medium or high risk depending on blast radius.
8. Never remove a public or shared surface until its removal gates pass.

### Removal gates

Before removing a candidate:

1. No active packet, lock, handoff, or known consumer depends on it.
2. Migration steps and replacement validation are complete.
3. The deprecation window has elapsed, or an explicit non-expired exception
   is recorded.
4. Runtime/access evidence is clean where the surface is externally reachable.
5. Rollback, evidence retention, and user/reviewer approval match the risk tier.
6. Targeted validation passes after the removal group.
7. Full validation passes before closure.

Removal is a separate action from deprecation and should normally be a small,
reversible change. Never automate destructive deletion from a static candidate
list.

## Tracker lifecycle

| Tracker state                                 | Location                         | Action                                    |
| --------------------------------------------- | -------------------------------- | ----------------------------------------- |
| Active (`Planned`, `Claimed`, `Implementing`) | `work-packets/`         | Keep active                               |
| Complete, pending closure                     | `work-packets/`         | Retain until user verification            |
| Complete and user-confirmed                   | `archive/work-packets/` | Move packet and row to the archive ledger |
| Cancelled or superseded                       | `archive/work-packets/` | Move packet and row with reason           |
| Closure record                                | `closure/`              | Retain per evidence policy                |
| Archived and beyond retention                 | Archive storage                  | Delete only under the applicable approval |

The canonical archive tracker is `tracker/archive/index.yaml`. The
`archive/execution-tracker-archive.md` file is its generated human-readable
projection. It contains terminal packet rows; the active YAML index and
shards contain only live or not-yet-closed work.

The active YAML tracker index has a 25-row cap. Once it reaches 26 rows, move
task-specific active rows into a declared
`tracker/shards/<TASK-ID>.yaml`; each shard has a 50-row cap. Shards are not
archives:
active packet YAML remains in `work-packets/`, and every packet appears in
exactly one active index/shard or the archive index. The tracker validator
enforces these bounds and partition invariants. Append-only transition history
belongs in `tracker/events/<TASK-ID>.yaml`, not in the active projection.

Review active packets every 14 days. Resolve an unchanged packet through the
normal state machine, using `Interrupted` with a recovery note when work is
paused. Do not create a `Stale` state and do not archive a packet until it is
terminal and user-confirmed.

### Tracker rollover

At cleanup or iteration closure, use native file and YAML tooling to perform
the following procedure:

1. Identify packets in `work-packets/` whose state is `Complete` or
   `Cancelled` and whose closure/user-confirmation requirements are satisfied.
2. Confirm each packet has a matching row in the active YAML index or shard and
   is not already present in `archive/work-packets/`.
3. Create `archive/work-packets/` and `tracker/archive/index.yaml` when
   needed.
4. Move each packet YAML to `archive/work-packets/` and move, rather than
   copy, its row to `tracker/archive/index.yaml`.
5. Verify that no archived row remains in the active YAML tracker, every archived
   packet has an archive row, and the packet state is terminal. A `Complete`
   packet must retain its handoff reference.
6. Regenerate both Markdown projections and run tracker validation.
7. If verification fails, restore the moved files and rows before continuing.

The procedure is harness-native. Use the harness's file and YAML capabilities
to perform the operation and verify the invariants; no Python runtime or
repository archive command is required. Evidence and handoffs are not moved
by tracker rollover and continue to follow their own retention rules.

## Evidence retention

- `standard`: retain 30 days after closure, then archive.
- `extended`: retain 90 days for complex refactors, compliance, production incidents, or regulated data.
- `archive`: move to long-term storage immediately after closure.
- Mark superseded evidence stale immediately, but retain it until the retention rule permits removal.

Evidence also SHALL declare its classification, redaction status, secret-scan
result, access policy, storage/encryption status, retention class, and any
incident reference. Secrets, session material, and unnecessary raw customer
or model content must never be committed. Restricted evidence belongs in an
approved encrypted store; the repository keeps only a sanitized summary or
verified reference when appropriate. See `templates/evidence-policy.yaml` and
`docs/evidence-security.md`.

## Baseline refresh

If an iteration lasts more than 14 days, capture a new baseline, link it as new immutable evidence, and mark the previous baseline stale. Do not append indefinitely to an expired baseline.

## Dependency pruning

During or after the Data Gate, verify package imports, API consumers,
environment variables, config keys, routes, and generated references. Record
the candidate and decision first. Execute removal only after implementation
validation, unless an approved migration packet explicitly requires earlier
removal. Prove there are no active consumers, update lockfiles and imports,
and run relevant validation. Medium or high-risk pruning requires reviewer or
user approval.

## Bloat prevention

- Consolidate packets with the same owner, dependencies, locks, scope, and validation plan.
- Review packets left in `Planned` for seven days without a claim and close obsolete packets with a reason.
- Deduplicate evidence before creating a new capture.
- Keep one canonical tracker and one canonical evidence reference per result.

## Cleanup checklist

```yaml
cleanup_id: PROJECT-T001-CL001
task_id: PROJECT-T001
packet_id: PROJECT-T001-P001
executed_by: "agent"
timestamp: ""
dead_code:
  identified: []
  decisions: []
  removed: []
  deferred: []
  retained: []
  false_positive: []
stale_artifacts:
  identified: []
  archived: []
  deleted: []
deprecations:
  identified: []
  migrated: []
  sunset_eligible: []
  removed: []
  retained_by_exception: []
temp_files:
  identified: []
  deleted: []
trackers:
  archived: []
  retained: []
user_approvals:
  high_risk_removals: []
  archive_confirmed: false
verification:
  imports_checked: false
  consumers_checked: false
  deprecation_windows_checked: false
  exceptions_checked: false
  lint_passed: false
  tests_passed: false
  no_orphaned_references: false
```

## Safeguards

- Never remove an unrecorded candidate.
- Never remove user-owned or untracked work without explicit permission.
- Never archive active work or release another owner's lock.
- Never delete evidence before retention and rollback requirements are satisfied.
- Never remove shared code, configuration, or dependencies without the required approval.
- If ownership or risk is unclear, stop and escalate to the reviewer or user.

## Cross-skill references

- Packet inventory: `phased-engineering-execution/SKILL.md`
- Closure orchestration: `project-lifecycle/SKILL.md`
- Coding principles: `coding-principles/SKILL.md`
