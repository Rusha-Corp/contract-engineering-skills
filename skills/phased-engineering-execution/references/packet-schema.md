# Packet Schema and Acceptance Contract

This reference is part of the `phased-engineering-execution` skill.
The skill's SKILL.md is the normative source; this file provides the
detailed schema and contract specification.

## Packet schema

```yaml
packet_id: PROJECT-T001-P001
task_id: PROJECT-T001
phase: P0_FOUNDATIONS
domain: coding|browser|design|data|documentation|security
title: "Short measurable title"
objective: "Verifiable outcome"
open_questions: []
scope:
  in: []
  out: []
implementor:
  agent_id: ""
  harness: ""
  model: ""
  session_id: ""
capabilities: []
risk_tier: low|medium|high|critical
approval_policy: automatic|reviewer|user|two_person
external_effects: []
owner:
  identity: ""
  identity_type: human
  authentication_ref: ""
  signed_at: ""
reviewer: "agent-or-user"
cleanup_owner: "agent-or-user"
dependencies: []
locks: []
claim_timestamp: ""
baseline_refs: []
design_decision_ref: null
data_gate_ref: null
acceptance_criteria: []
acceptance_contract:
  version: 1
  criteria:
    - id: ""
      statement: ""
      expected_result: ""
      verification_method: ""
      verification_command: ""
      evidence_refs: []
      failure_result: ""
      validation_ref: ""
validation_plan: []
cleanup_scope:
  size_reviews: []
  dead_code_review: []
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
packet_class: single-domain|cross-cutting|parent-coordination|child-implementation
state: Planned
evidence_refs: []
handoff_ref: null
```

`cleanup_scope` and `skill_gaps` are inventories and references only. Cleanup execution belongs to `cleanup-protocol`; gap review belongs to `skill-evolution`.

## Structured acceptance contract

New packets SHOULD provide `acceptance_contract` with structured criteria.
Each criterion SHALL have:

- a stable `id` matching `<PACKET-ID>-AC<NNN>`;
- a measurable `statement` describing what must be true;
- an `expected_result` that is observable or testable;
- a `verification_method` (inspect, execute, or review);
- an optional `verification_command` for executable checks;
- at least one `evidence_refs` entry linking to concrete evidence;
- an optional `failure_result` describing the prohibited outcome;
- an optional `validation_ref` linking to a `validation_plan` entry.

The record validator enforces these fields when `acceptance_contract` is
present. Legacy packets may use only the `acceptance_criteria` string list,
but new packets should migrate to the structured contract. Reviewers must
evaluate each criterion individually and reject aspirational, non-measurable,
or evidence-deficient criteria.

## Deprecation and removal planning

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
