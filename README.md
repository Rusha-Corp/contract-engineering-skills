# Contract Engineering Skills

Shared Droid Skills and project templates for contract-driven, phased
engineering work.

## Contents

- `skills/` contains the governed shared Skill definitions.
- `docs/` contains deprecation, removal, and process guidance.
- `templates/` contains copyable work-packet, deprecation, feedback, and
  validation records.

The repository separates hard safety invariants from procedures. Procedures
may be tested and revised through a recorded practice experiment. No change to
an invariant is adopted without explicit review.

## Core loop

```text
Baseline
→ Design/Data Gates
→ Implement
→ Validate
→ Deprecation Review
→ Cleanup
→ Skill Review
→ User Verification
→ Closure
```

## Usage

Copy the applicable Skill into the local Droid Skill directory, then use the
templates in the project's execution ledger. Project-specific decisions,
owners, evidence, exceptions, and migration dates belong in the project
records, not only in this repository.

The deprecation policy covers API routes, configuration, dependencies, K8s
resources, feature flags, shared code, and process guidance. Deprecation is
separate from removal; removal requires evidence, migration, approval, and
rollback or retention planning.

## Validation

Use `templates/validation-guide.md` to perform non-destructive checks. This
repository intentionally does not ship an automatic deletion tool.
