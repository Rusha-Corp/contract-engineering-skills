# Protocol Fleet and Compatibility

The project lock is authoritative for one repository, but a protocol release
can affect many repositories, harnesses, adapters, and CI environments. Use
`templates/protocol-consumer.yaml` to maintain a discoverable consumer record
where fleet management is needed.

## Consumer inventory

Record each consuming repository, owner, environment, lock path, pinned
release/ref, lock schema, tracker format, database-projection status,
harnesses, adapters, skill directory, compatibility window, migration status,
last verification, and evidence. Do not record credentials or private session
content.

The inventory is metadata about consumers; it does not replace the consumer's
project-local lock, tracker, packets, or evidence.

## Compatibility assessment

Before publishing a release:

1. Compare the release's schema, state-machine, safeguard, adapter, tracker
   format, database-projection, and migration changes with each supported
   consumer.
2. Identify consumers outside the supported compatibility window.
3. Create migration packets for breaking changes before changing locks.
4. Test representative harnesses and protocol preflight.
5. Publish an owner, target release, due date, rollback ref, and support
   decision for every affected consumer.

Lock schema, state-machine, and safeguard changes are breaking by default.
Skill additions and wording changes may be compatible only when the
compatibility assessment proves they do not alter required behavior.

## Drift and rollout

Detect stale refs, unsupported lock versions, missing skills, hash/version
mismatches, and unsynchronized harnesses. Drift blocks new packet claims in
that environment. Record the observed state before repairing it.

Roll out in stages where risk warrants:

1. verify the release and migration notes;
2. update a canary consumer;
3. run preflight and compatibility/evaluation suites;
4. expand to the remaining consumers;
5. retain the previous verified ref until rollout is complete;
6. record success, rollback, or end-of-support.

An unsupported consumer is not silently upgraded or deleted from the
inventory. It receives an owner and migration decision.

## End of support

Announce the support deadline and migration path before removing compatibility.
Security-driven emergency revocation may shorten the window only with an
incident record, explicit approval, affected-consumer analysis, and a
verified rollback or replacement.
