# Changelog

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
