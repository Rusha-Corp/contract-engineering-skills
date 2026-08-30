# Validation Guide

These checks are intentionally non-destructive. They validate records and
references; they never delete a candidate automatically.

## Before implementation

- Confirm the baseline revision, environment, toolchain, and dependencies.
- Inventory consumers, routes, configuration, permissions, and generated
  references.
- Register the packet owner, reviewer, locks, dependencies, and gates.
- Record a deprecation entry for any public or shared surface being replaced.

## Before removal

- Search repository, generated, manifest, and test references.
- Check direct and transitive dependency consumers.
- Check runtime/access evidence for externally reachable surfaces.
- Confirm migration completion and replacement compatibility tests.
- Confirm the deprecation window or an unexpired approved exception.
- Record rollback, evidence retention, and approval.
- Run targeted validation, then full validation before closure.

## At closure

- Reconcile packet states, locks, handoffs, and the tracker.
- Review overdue deprecations and expired exceptions.
- Record cleanup decisions and retained candidates.
- Record Skill gaps and practice-experiment outcomes.
- Obtain user verification before archiving evidence.
