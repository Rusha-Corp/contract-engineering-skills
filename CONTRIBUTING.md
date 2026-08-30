# Contributing

## Change expectations

1. Explain the problem and the affected engineering boundary.
2. Update the relevant Skill, policy, or template.
3. Preserve safety, authorization, data-correctness, and traceability
   invariants.
4. Add a migration note for changed guidance.
5. Provide a validation plan and evidence.
6. Keep changes small, reviewable, and reversible.

## Skill changes

Use semantic versioning:

- Patch: wording, examples, or link corrections.
- Minor: new capability or materially expanded procedure.
- Major: state-machine, schema, scope, or safeguard changes.

Classify each rule as an invariant, default procedure, or experiment. New
procedures should be trialled on bounded work with an owner, hypothesis,
success metric, expiry, and rollback plan before becoming defaults.

## Protocol configuration changes

Changes to the lock template or cross-harness setup guidance must document
the source commit, release, five skill versions, SHA-256 values, project
protocol-root behavior, adapter impact, migration steps, rollback, and
preflight validation. Do not introduce host-specific paths into the portable
lock contract.

## Deprecation changes

Every deprecated public or shared surface needs a replacement, affected
consumers, migration steps, sunset target, removal criteria, evidence, and
rollback or retention plan. Do not remove externally consumed behavior based
only on static repository search.

## Review checklist

- Is the change backward compatible or explicitly deprecated?
- Are consumer and migration impacts documented?
- Are validation and rollback steps reproducible?
- Are stale references and compatibility shims addressed?
- Are the Skill version and revision history updated?
- Does the change improve code health without adding speculative machinery?
