# Handoff Schema

This reference is part of the `phased-engineering-execution` skill.
The skill's SKILL.md is the normative source; this file provides the
detailed handoff schema specification.

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

A handoff is complete only after the receiver records authenticated
acceptance or rejection with reasons. Acceptance must bind the receiver to
the exact packet revision, scope digest, changed-resource hashes, approval
reference, validation evidence, and receiver timestamp. The human owner
must sign the handoff acceptance; an agent may not transition a packet to
Complete on its own. A tracker state change without that handoff record is
invalid.
