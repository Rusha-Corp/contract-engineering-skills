# Protocol Release Integrity

A lock file proves that a consumer has the expected bytes. It does not, by
itself, prove who published those bytes or whether the release process was
authorized. Protocol releases therefore require both content hashing and
publisher/provenance verification.

## Release controls

Before publishing a protocol release:

1. Work from a clean, reviewed commit on a protected release path.
2. Run the complete protocol validation suite, including unit tests,
   cross-reference, JSON schema, adapter, security, and compatibility checks.
3. Have an independent reviewer approve the release contents, migration
   notes, affected consumers, and rollback plan.
4. Generate an attestation from `templates/protocol-attestation.yaml`.
5. Sign the commit or release artifact with the repository's approved signing
   system and publish the verification reference.
6. Record the source commit, artifact hashes, builder/workflow, dependencies,
   reviewers, and approval reference.
7. Publish immutable release metadata and announce any breaking changes.

The release actor must not be the sole author and approver. A tag or release
name is a convenience label; consuming locks must still contain the resolved
40-character commit.

The attestation is valid only when it includes an authenticated publisher,
immutable source commit, artifact hashes, builder/workflow identity,
dependencies, independent approval, signature/transparency references,
verification time, and revocation status. The independent approver must not
be the release author or publisher. Attestations are bound to the exact
repository, commit, release, and artifact bytes; changing any subject field
requires a new signature and approval.

## Verification

A consumer verifies, in order:

- the canonical repository identity;
- the immutable commit and release association;
- the publisher signature and transparency or verification reference;
- the attestation subject and artifact hashes;
- the independent approval;
- the protocol and skill versions;
- the migration and compatibility requirements.

Verification must check the signature against the publisher identity, confirm
the source and artifact hashes, validate the independent approval and its
validity window, and perform a current revocation check. Missing, unsigned,
expired, revoked, or mismatched metadata fails closed. Do not update the
project lock. Preserve only redacted failure identifiers and hashes for
investigation, record an incident when appropriate, and continue using the last
verified release.

SLSA provenance and in-toto attestations are compatible implementation choices.
The protocol does not require one vendor, but the chosen system must let a
consumer verify origin, authorization, and the steps used to produce the
release.

## Key lifecycle and compromise

The release owner maintains signing identity metadata and a tested process
for rotation, expiration, revocation, and recovery. A compromised key or
release requires:

1. Marking the attestation and release revoked.
2. Stopping new lock updates and affected installations.
3. Identifying consumers from the protocol fleet inventory when available.
4. Publishing a verified replacement or rollback reference.
5. Preserving evidence and recording an incident and postmortem.

Do not erase a revoked release from the audit trail.

The release owner must exercise both a positive verification and negative
verification for altered commit, artifact hash, approval identity, expiry, and
revocation status before publication. A key-compromise drill must demonstrate
revocation propagation and rollback to the last verified release without
publishing a new lock.

## Consumer lock update

After a verified release is published, a consuming project updates `ref`,
`release`, every governed skill version, and every SHA-256 value in one
reviewed change. The project records the attestation reference and migration
evidence. The old lock and verified installation remain available until the
new preflight and compatibility checks pass.
