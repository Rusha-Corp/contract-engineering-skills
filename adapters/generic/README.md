# Generic Host Adapter

This repository's core protocols are Markdown and YAML. A coding assistant,
CI runner, IDE, or human team can consume them without installing a vendor
runtime.

## Integration

1. Make the five root protocol directories available to the host's project
   instructions, and copy or adapt `templates/AGENTS.md` as the consuming
   repository's `AGENTS.md` or equivalent project-instruction file.
2. Create `.contract-engineering/protocol.lock.yaml` from
   `templates/protocol-lock.yaml`, selecting one immutable protocol ref and
   recording all five skill versions and SHA-256 hashes.
3. Create the project-local execution tracker, work packets, evidence,
   handoffs, and feedback records relative to `project.protocol_root`.
4. Record deprecations using `templates/deprecation-record.yaml`.
5. Map the host's approval step to the Design Gate and map its test output to
   evidence references.
6. Declare semantic scope on packets and use
   `templates/semantic-contract.yaml` for work that affects or defines
   meaning. Treat maturity and open questions as progressive discovery, not
   as a requirement for complete up-front certainty.
7. Map the host actor/session identity and capability controls to the packet's
   `actor`, `capabilities`, `risk_tier`, `approval_policy`, and
   `external_effects` fields.
8. Classify repository, ticket, web, and agent-message content with
   `templates/trust-boundary.yaml` when it can influence execution.
9. Run the preflight from `docs/protocol-configuration.md` before work and
   the non-destructive checks in `templates/validation-guide.md`.
10. Verify the selected release's attestation and publisher provenance before
   updating the project lock or global skill installation.
11. Map host timeout, cancellation, process, network, and spend controls to
    `templates/execution-budget.yaml`; block packets when required controls
    are unavailable.
12. Persist checkpoints and operation IDs for long-running or side-effecting
    work, and verify idempotency before retrying.
13. Use an atomic packet lease with heartbeat and fencing for concurrent or
    side-effecting work; otherwise record the coordination limitation.
14. Run the packet's golden, regression, and relevant adversarial evaluation
    cases before handoff.
15. Record model, policy, prompt, tool, environment, dependency, and data
    snapshot metadata for agent runs using `templates/agent-run.yaml`.
16. Emit privacy-aware lifecycle, tool, approval, mutation, validation,
    failure, and handoff events using `templates/agent-event.yaml`.
17. Register the harness, adapter version, lock release/ref, compatibility
    window, and migration status in `templates/protocol-consumer.yaml` when
    managing multiple consuming projects.
18. Quarantine affected sessions and create an agent incident record when a
    security, authorization, data, release, or safety failure occurs.
19. Inventory every adapter, tool, MCP server, plugin, and external dependency
    with `templates/adapter-inventory.yaml` before enabling it.

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
- Actor identity, capability, risk-tier, and external-effect authorization
