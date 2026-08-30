# Deprecation and Removal Policy

This policy governs Humming Mind public interfaces, internal shared
interfaces, configuration, K8s resources, dependencies, feature flags, and
project-process records.

## Stability levels

Every public or shared surface has one stability level:

| Level | Meaning | Compatibility expectation |
|---|---|---|
| `experimental` | Subject to active design change | No removal window is promised; consumers must opt in |
| `beta` | Usable, but still being validated | Breaking change requires a migration note and review window |
| `stable` | Supported interface | Preserve compatibility or deprecate before removal |
| `deprecated` | Replaced or scheduled for removal | Replacement and sunset criteria are mandatory |

The level belongs in the relevant contract, packet, or interface description.
An implementation must not silently present an experimental or deprecated
surface as stable.

## Deprecation lifecycle

```text
Active
  -> Deprecated       decision, owner, replacement, and notice
  -> Migration        consumers and migration work are tracked
  -> SunsetEligible   criteria and review window are satisfied
  -> RemovalReview    evidence and approval are checked
  -> Removed
  -> Verified         regression and runtime checks pass
```

An item may move to `RetainedByException` from `Migration` or
`RemovalReview`. Exceptions require a reason, owner, success measure, review
date, expiry date, and rollback plan. An expired exception is a blocker, not a
permanent retention decision.

## Choosing a migration window

There is no universal duration. Select a window using consumer impact, release
cadence, data or security risk, and whether consumers are controlled by this
project.

Defaults for planning are:

- Private implementation detail: remove in the same change when evidence is
  complete.
- Internal shared interface or configuration: at least 14 days or one
  consumer release.
- Project API or K8s interface: at least 30 days or one compatible release.
- External or public API: at least 90 days or one major release, whichever is
  longer.
- Security or incident-driven removal: expedited removal is allowed only with
  explicit reviewer/user approval, a migration or mitigation note, and
  preserved evidence.

These are defaults, not gates that override risk judgment. A shorter window
must be justified in the deprecation record.

## API and interface signaling

For HTTP resources, use the RFC 9745 `Deprecation` response header and RFC
8594 `Sunset` response header when the resource is scheduled to become
unresponsive. Link the response to migration documentation where practical.

OpenAPI descriptions must mark deprecated operations, parameters, and schemas
with `deprecated: true`, document the replacement, and include the planned
sunset behavior. API compatibility tests must cover the replacement and any
temporary compatibility path.

For package APIs, use the language/package manager's native deprecation
mechanism. Deprecate versions rather than destructively unpublishing versions
that consumers may still need to install.

## K8s and deployment resources

K8s API versions and resources follow the upstream version-aware migration
practice: identify the target cluster versions, migrate manifests and live
consumers, render and apply the replacement, and remove the old resource only
after rollback and ownership checks pass.

Deployment changes must preserve the exact tested image and configuration
inputs. A deprecation record does not authorize direct mutation of the live
cluster.

## Feature flags

Every feature flag has an owner, category, creation date, expected expiry, and
removal packet:

- Release flags are removed after rollout validation.
- Experiment flags are removed or renewed after the experiment decision.
- Operational kill switches remain available only while their risk justifies
  them and require periodic review.

Flag cleanup is separate from disabling a flag. A disabled flag is not dead
code until its consumers and fallback path have been removed and validated.

## Dead-code and dependency removal

Static search is evidence, not proof, for externally consumed surfaces.
Removal requires evidence appropriate to the target:

- References, imports, exports, generated files, and tests for code.
- Direct and transitive consumers, lockfile impact, security/license status,
  and replacement availability for dependencies.
- Repository consumers, interface documentation, access data, and migration
  status for routes and APIs.
- Manifests, templates, runtime use, and deployment consumers for
  configuration.

Each candidate receives one decision: `remove`, `deprecate`, `retain`,
`archive`, `false_positive`, or `needs_evidence`. Removal is a separate,
reviewable change from deprecation. Broad or externally visible removal
requires the applicable reviewer or user approval.

## Practice evolution

Safety, authorization, data-correctness, and traceability rules are invariants.
Tools, thresholds, evidence sources, and workflow defaults are procedures and
may evolve.

When a procedure is uncertain:

1. Record the gap and proposed change.
2. Obtain user approval for a bounded experiment.
3. Define a hypothesis, owner, scope, metric, expiry, and rollback.
4. Run it on small, reversible work.
5. Measure the result.
6. Retain, revise, or reject the practice and version the governing Skill.

No process rule may be weakened silently. A workaround remains open until the
gap has a recorded decision.
