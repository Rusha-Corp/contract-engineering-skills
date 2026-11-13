# Extended Practices

This reference is part of the `phased-engineering-execution` skill.
The skill's SKILL.md is the normative source; this file provides the
detailed specifications for practices added in v2.8.0.

## Risk-tiered review

Review depth scales with risk. Authoring is cheap; verification is the
constraint. A flat "deep review everything" policy wastes reviewer capacity
on low-risk work and leaves less time for high-risk work. Adapted from
AIDLC's playbook rule.

### Risk tiers

| Tier | Trigger | Review depth |
| --- | --- | --- |
| **Low** | Documentation-only, single-file skill text, no code, no data, no external effects | Automated checks (validators, linters) + single reviewer approval |
| **Medium** | Code changes in a single domain, schema additions (non-breaking), new tests | Automated checks + single reviewer + targeted manual evidence review |
| **High** | Cross-cutting changes, security-domain, data migrations, external effects, breaking schema changes, production deployments | Automated checks + two independent reviewers + full manual evidence inspection |

### How to assign

The packet's `domain`, `packet_class`, and `scope` determine the tier. The
agent records the tier in the handoff:

```yaml
risk_tier: low|medium|high
```

If the agent and reviewer disagree on the tier, the higher tier wins.

### What changes by tier

- **Low:** the reviewer checks that automated validators pass and the change
  matches the packet scope. No line-by-line code review required.
- **Medium:** the reviewer additionally inspects the changed files and
  evidence to confirm the acceptance criteria are met.
- **High:** two reviewers independently check the change. At least one must
  be independent of the actor (not the same person who approved the design).
  The reviewer(s) inspect all evidence manually, including security and data
  correctness gates.

### Relationship to existing gates

Risk-tiered review does not replace gates. It adjusts the depth of human
review at handoff. All gates (Design, Data, Threat Model, Security
Verification) still run regardless of tier. The tier controls how much
manual inspection the reviewer performs on top of the gates.

## Mutation testing

Mutation testing measures test quality by injecting small defects (mutations)
into the code and checking whether the tests catch them. Tests that pass
despite mutations are asserting nothing meaningful. Adapted from AIDLC's
evals practice.

### When to run

Coding-domain packets SHOULD run mutation testing when tooling is available
for the language and framework (e.g., Stryker for JavaScript/TypeScript,
mutmut for Python, PIT for Java). It is not required when no mutation testing
tool supports the project's language or when the packet touches only
non-executable code (documentation, configuration schemas).

### How to record

Record the mutation score in the packet's evidence:

```yaml
validation_plan:
  - id: PROJECT-T001-P001-VAL001
    kind: test
    skill: phased-engineering-execution
    checks:
      - "mutation score >= 60% (or recorded limitation if tooling unavailable)"
    expected: "mutation score meets threshold or limitation is documented"
```

### Thresholds

- **60% or above:** acceptable. The test suite catches most injected defects.
- **Below 60%:** flagged for reviewer attention. The agent SHOULD document
  which survivors are expected (e.g., equivalent mutations) and which indicate
  a real gap. The reviewer decides whether to accept or send to Rework.
- **No score (tooling unavailable):** record the limitation in evidence. The
  packet is not blocked, but the reviewer is aware that mutation quality was
  not measured.

### Why not a hard gate

Mutation testing tooling is not universally available, and mutation scores
vary by domain (UI code typically scores lower than business logic). A hard
gate would block packets in environments without tooling. Instead, the score
is evidence for the reviewer to evaluate.
