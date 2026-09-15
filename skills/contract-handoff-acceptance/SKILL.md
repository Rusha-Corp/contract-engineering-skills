---
name: contract-handoff-acceptance
description: Independently accept or reject a Contract Engineering packet handoff.
---

# Contract Handoff Acceptance

The receiver independently checks the exact base and head revisions, scope
digest, changed-resource hashes, validation output, evidence, unresolved
items, and rollback notes.

Accept only when the packet's criteria and required gates pass. Record the
acceptance bound to the handoff revision and evidence. Reject with concrete
required fixes. The sender and receiver must be distinct authenticated
identities; a worker cannot self-accept.
