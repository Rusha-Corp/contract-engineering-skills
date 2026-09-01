# Changelog

## Unreleased

### Protocol hardening

- Added packet-class ownership boundaries, metadata-driven security routing,
  structured external effects, lifecycle transition rules, evidence-policy
  schema validation, and CI unit/schema checks.
- Added batch-acceptance guidance that preserves per-packet evidence,
  handoffs, limitations, lock release, and tracker reconciliation.
- Clarified that pushed development revisions do not become consumer lock
  targets until an independently reviewed immutable release is published.
- Added agent identity, capabilities, risk tiers, approval policies, and
  external-effect records.
- Added trust-boundary and prompt-injection handling for repository, tool,
  web, and agent content.
- Added machine validation for packet records, dependencies, lifecycle
  invariants, tracker reconciliation, and changed-path scope.
- Added release provenance, evidence privacy, runtime budgets, durable
  checkpoints, packet leases, evaluation plans, reproducibility records,
  observability events, incident response, fleet compatibility, and adapter
  security templates.
- Added protocol release-preparation guidance; the stable lock remains pinned
  to the last published release until this hardening work is reviewed and
  published as an immutable release.
- Added immutable lock/source verification and a fail-closed stable-tag
  attestation gate; development tags remain explicitly non-stable.

## 2.2.1 - 2026-09-01

- Published as a replacement for the failed immutable 2.2.0 tag after the
  public release-key fingerprint was narrowly allowlisted in Gitleaks.
- Preserved v2.2.0 as immutable audit and rollback evidence; consumers must
  adopt only after independently verifying the v2.2.1 attestation and hosted
  security gates.

## 2.1.0 - 2026-08-30

- Added a portable `protocol.lock.yaml` template for pinning one immutable
  protocol source and all five governed skill files.
- Added cross-harness setup, preflight, update, rollback, and drift guidance.
- Documented the default `.contract-engineering` project record root and
  explicit legacy `.factory` migration behavior.
- Added adapter-specific global skill installation guidance without making
  host paths part of the project lock.
- Added protocol-lock preflight guidance to all governed skills.

## 2.0.0 - 2026-08-30

- Added `open_questions` to packet records for spec-to-packet traceability.
- Added `review_date` to deprecation records.
- Added an explicit `DeprecationReview` lifecycle state between validation
  and cleanup.
- Made installer examples fail on clone or copy errors instead of leaving a
  partial installation.
- Migration: packet and deprecation record consumers must accept the new
  fields, and lifecycle consumers must handle `DeprecationReview`.

## 1.1.0 - 2026-08-30

- Added deprecation and removal lifecycle guidance.
- Added evidence-driven dead-code and dependency cleanup.
- Added exception expiry and practice-experiment workflows.
- Added evolutionary architecture and compatibility guidance.
- Added generic and Factory Droid host adapters.
- Added portable work-packet, deprecation, Skill-gap, and validation
  templates.
