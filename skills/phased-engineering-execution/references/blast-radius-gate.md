# Runtime blast-radius gate

Every newly governed nonterminal packet carries `blast_radius` version 1.
Packets claimed before the 2026-11-23 protocol adoption remain readable during
migration, and terminal historical packets are never rewritten. A missing
assessment on a newly claimed packet is invalid. Use `status: unknown` with
`risk: high` and named `unknowns` while investigating; unknown cannot enter
Ready. Use `status: no_runtime_impact` only with low risk, an explicit reason,
and no runtime components or couplings.

## Declared and inferred context

The packet YAML is authoritative for the declaration. A project-owned
`runtime-topology.yaml` maps path globs to services, identities, consumers,
shared resources, environments, and coupling. Hosts may add working-diff and
local dependency inference. Every component and coupling is labelled
`declared`, `inferred`, or `verified`. Inference is advisory and never
becomes verified live state merely because it matches a path.

An assessment is bound to `packet_revision`. Material packet changes require
a new assessment. Live observations expire after 24 hours and must identify
source revision, live revision, environment, observation time, and evidence.
Missing shared infrastructure, RBAC, deployment, public interface, or data
migration impact is high risk, not low risk by default.

## Risk gates

- **Low:** provide a reasoned assessment. Context remains advisory.
- **Medium:** complete inference review with evidence before Handoff.
- **High:** before Ready, provide complete components, verified coupling,
  affected environments, current live evidence, and an evidenced rollout.
  Before Complete, verify the real user or service entry point after deploy
  and bind that evidence to the same source and live revisions.

An incompatible permission or interface reduction requires exactly
**expand → migrate → contract**. Retain the old capability while deploying and
verifying its replacement. Contract only after accepted migration evidence.
This prevents policy or interface changes from outpacing their running
consumers.

The Droid SessionStart hook is an early-warning adapter, not an enforcement
boundary. Task Master or the consuming tracker remains authoritative for
lifecycle gates.
