# Generic Host Adapter

This repository's core protocols are Markdown and YAML. A coding assistant,
CI runner, IDE, or human team can consume them without installing a vendor
runtime.

## Integration

1. Make the five root protocol directories available to the host's project
   instructions.
2. Create `.contract-engineering/protocol.lock.yaml` from
   `templates/protocol-lock.yaml`, selecting one immutable protocol ref and
   recording all five skill versions and SHA-256 hashes.
3. Create the project-local execution tracker, work packets, evidence,
   handoffs, and feedback records relative to `project.protocol_root`.
4. Record deprecations using `templates/deprecation-record.yaml`.
5. Map the host's approval step to the Design Gate and map its test output to
   evidence references.
6. Run the preflight from `docs/protocol-configuration.md` before work and
   the non-destructive checks in `templates/validation-guide.md`.

The global skill directory is host-specific. It may be a user-level
directory, a container mount, or a CI-provided instruction path. It must
contain the exact skill files selected by the project lock. The project lock
and records remain portable and must not be duplicated per host.

The host should provide a way to claim ownership, lock shared resources,
record decisions, run validation, accept handoffs, and retain evidence. If a
host lacks one of these capabilities, record the limitation as a Skill Gap
instead of silently skipping the control.

## Updates and drift

When the protocol changes, update the lock and every host installation from
the same immutable ref. A missing skill, version mismatch, or hash mismatch
blocks new work until the installation is synchronized. Preserve the prior
installation or a verified backup for rollback.

## Conformance

An adapter conforms when it demonstrates:

- Baseline and packet creation
- Design and data gates
- Implementation and validation
- Deprecation and sunset review
- Evidence-backed cleanup
- Handoff acceptance
- Practice review and closure
