# Approval integrity

An approval is a signed statement about a precise subject. A display name,
chat message, issue comment, or unverified URL is not authentication evidence.
Instantiate `templates/approval.yaml` for an approval and
`templates/handoff.yaml` for a transfer of work.

## Required binding

The verifier must canonicalize and compare all of these fields:

- packet ID;
- the 40-character lowercase base and head revisions;
- `scope_digest`, a SHA-256 over canonical JSON containing the packet ID and
  sorted changed resource paths and hashes;
- approval decision, policy, constraints, and expiration;
- RFC 3339 UTC creation, approval, verification, and revocation-check times.

An approval is valid only when its signature verifies to the recorded
approver identity through the configured `sigstore`, `gpg`, or other approved
verification system, and the identity is authorized for the packet. The
verifier must check revocation and record the result. Missing, malformed,
expired, revoked, or mismatched values fail closed.

The requester and approver must be different authenticated identities for
`reviewer`, `user`, and `two_person` policies. High-risk and critical packets
require an independent approver; the packet owner may not approve their own
work. Two-person approval requires two distinct approver identities and two
verifiable signatures.

## Handoff acceptance

An accepted handoff must contain authenticated sender and receiver identities,
the exact base and head revisions, scope digest, changed-resource hashes,
approval reference, verification result, and receiver timestamp. A receiver
may accept only after independently checking the diff and validation evidence.
The handoff expires when its recorded expiry passes or when its subject revision
or scope changes.

## Verification test matrix

Implementations must pass a positive signed approval and reject each of these
negative cases without disclosing signed payloads or secret material:

1. missing signature or unauthenticated approver;
2. requester equal to approver for a high-risk packet;
3. altered revision, scope digest, changed-resource hash, or policy;
4. approval outside its validity window;
5. revoked signer, approval, or release;
6. expired handoff or receiver mismatch.

Record only redacted identifiers, hashes, rule names, and outcomes in evidence.
Never copy signature payloads, private keys, access tokens, or raw provider
responses into repository records.

## Key compromise and rollback drill

On key compromise, stop accepting the affected identity, mark all dependent
approvals and attestations revoked, preserve redacted verification evidence,
and create an incident. Rotate the key in the configured provider, publish a
verified replacement approval or release, and rerun the full verification
matrix. Roll back to the last independently verified revision if replacement
verification cannot complete. A revoked release remains in the audit trail.
