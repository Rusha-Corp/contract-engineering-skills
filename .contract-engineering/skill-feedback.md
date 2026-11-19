# Skill Feedback Log

## Active Gaps

| ID | Skill | Type | Severity | Status | Owner |
| --- | --- | --- | --- | --- | --- |
| CE-SG001 | phased-engineering-execution | missing | medium | open | user |
| CE-SG002 | phased-engineering-execution | missing | low | open | user |

### CE-SG001: Sync-before-review is not explicit in the protocol

- **gap_type:** missing
- **severity:** medium
- **description:** The phased-engineering-execution skill says "on spec approval, create the packet and claim it" but does not require syncing the packet to Task Master in `Planned` state for user review. The packet exists as a YAML file but may never reach the board if the sync fails silently. This happened during CENG-T037-P001: the packet YAML was created but had a YAML error (owner: null), the sync excluded it, and the user never saw the packet on the board. The agent proceeded to implementation without the user's design review.
- **impact:** The user cannot review the design on the board. The agent may proceed to implementation without approval, violating the P1 gate ("implement only approved, claimed packet scope"). The grooming phase (Scrum equivalent: backlog refinement) is effectively skipped.
- **proposed_change:** Add a step in the Planned state: "Sync the packet to Task Master via ce:sync. The user reviews the design on the board. Do not claim or implement until the user approves." Consider a tm doctor check that verifies the packet is on the board before the agent claims it.

### CE-SG002: Full sidecar ceremony required before design review

- **gap_type:** missing
- **severity:** low
- **description:** A design packet in Planned state currently needs spec + DEC001 + TM001 + DG001 + tracker entry + event stream just to get a design reviewed. This is heavy ceremony for the grooming phase (Scrum equivalent: backlog grooming should be lightweight — refine the story and bring it to the team). The full sidecars could be created after approval, when the packet is claimed and enters P0/P1.
- **impact:** Friction in the grooming flow. Agents may skip the protocol to avoid the ceremony, as happened during CENG-T037-P001 where the agent created all sidecars but then jumped to implementation without waiting for review.
- **proposed_change:** Allow a lightweight Planned state (spec + packet YAML + tracker entry only). Full sidecars (DEC, TM, DG) are created after approval, when the packet is claimed and enters P0/P1. The spec is the design artifact under review; the sidecars are the gate artifacts created at claim time.

## Resolved Gaps

| ID | Skill | Resolution | Version | Date | Closed by |
| --- | --- | --- | --- | --- | --- |

## Patterns

- Recurring gap themes:
- Skills needing major revision:
- New skill requests:
- Review date:
