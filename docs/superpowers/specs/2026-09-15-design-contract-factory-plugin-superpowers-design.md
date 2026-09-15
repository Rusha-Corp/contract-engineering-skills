# Contract Engineering and Superpowers Composition

Status: approved compatibility amendment
Supersedes: `CENG-T014-P001-DEC001`
Decision: `CENG-T014-P009-DEC001`
Base design: `docs/superpowers/specs/2026-09-15-design-contract-factory-plugin-design.md`
Date: 2026-09-15

## 1. Decision

Contract Engineering will compose with `obra/superpowers` as a separate
companion plugin. It will not fork Superpowers and will not copy its general
workflow skills.

The base design remains normative for design contracts, visual artifacts,
admission, security, evidence, handoffs, and rollout. This amendment changes
the plugin composition, skill ownership, bootstrap behavior, and packaging
layout.

## 2. Skill ownership

Superpowers owns general agent-workflow behavior:

- brainstorming;
- using-git-worktrees;
- writing-plans;
- test-driven-development;
- systematic-debugging;
- verification-before-completion;
- subagent-driven-development;
- executing-plans;
- requesting and receiving code review;
- finishing a development branch.

Contract Engineering owns governance and project contracts:

- contract-design;
- contract-review;
- contract-admission;
- contract-visual-review;
- contract-handoff-acceptance;
- phased execution, security assurance, cleanup, lifecycle, and skill
  governance where those skills do not duplicate Superpowers behavior;
- design records, packet records, dependencies, scope, gates, leases,
  resources, evidence, handoffs, and audit history.

Contract Engineering must not create skills named `using-superpowers`,
`brainstorming`, `writing-plans`, `subagent-driven-development`,
`using-git-worktrees`, or `test-driven-development`. Existing skills in this
repository that cover a distinct protocol concern retain their names and
must document any interaction with the corresponding Superpowers workflow.

## 3. Combined lifecycle

The compatible lifecycle is:

```text
Superpowers brainstorming
  -> Contract Engineering design contract
  -> Contract Engineering visual and contract reviews
  -> user architecture approval
  -> Superpowers writing-plans
  -> Contract Engineering packet creation and admission
  -> Superpowers worktrees and subagent-driven implementation
  -> Contract Engineering validation, evidence, and handoff
  -> Superpowers branch finishing
```

Superpowers may produce a human-readable design or implementation plan. The
Contract Engineering adapter consumes those artifacts and binds them to
`.contract-engineering/designs/<TASK-ID>/design.yaml`. A Superpowers approval
or plan is not, by itself, packet admission.

The Contract Engineering planning command must:

1. read the Superpowers design/plan artifact when present;
2. create or update the design contract and artifact manifest;
3. request the required security, data, compatibility, operations, and
   visual reviews;
4. record authenticated user approval;
5. create bounded packet records only after the approval is valid.

The Contract Engineering admission command must run before
subagent-driven implementation. It returns blocked reasons rather than
asking a Superpowers worker to infer missing governance.

## 4. Bootstrap and invocation compatibility

The two plugins may both provide session-start context. The Contract
Engineering bootstrap must be additive:

- it must not replace or re-emit the full Superpowers `using-superpowers`
  skill;
- it must not define a competing global skill-discovery rule;
- it must remind the agent to check the project lock, tracker, design
  contract, and packet admission before writes;
- it must identify the Contract Engineering commands and their stop points;
- it must state that repository validators and CI are authoritative.

Routing descriptions must make the ordering explicit:

```text
brainstorming -> contract-design -> writing-plans -> contract-admission
-> subagent-driven-development -> contract-validation -> handoff acceptance
```

If a host invokes skills in an unexpected order, `contract-admission` and CI
still block implementation. Automatic skill invocation is convenience, not
the security boundary.

## 5. Root-level Factory packaging

The repository itself is both marketplace and plugin:

```text
.factory-plugin/
  marketplace.json
  plugin.json
skills/
  contract-design/
  contract-review/
  contract-admission/
  contract-visual-review/
  contract-handoff-acceptance/
commands/
droids/
hooks/
scripts/
runtime/
schemas/
templates/
tests/
```

`.factory-plugin/marketplace.json` declares one plugin whose source is `"./"`.
`.factory-plugin/plugin.json` describes the same root package. This matches
the Superpowers installation shape and avoids a duplicated nested copy of
skills or runtime files.

The Factory installation is:

```bash
droid plugin marketplace add https://github.com/Rusha-Corp/contract-engineering-skills
droid plugin install contract-engineering-skills@contract-engineering-skills --scope user
```

Superpowers remains separately installable:

```bash
droid plugin marketplace add https://github.com/obra/superpowers
droid plugin install superpowers@superpowers --scope user
```

Clean-install validation must verify both plugin manifests, root-relative
paths, unique skill names, command metadata, hook loading, and coexistence
with a Superpowers installation. It must not overwrite or modify the
Superpowers plugin.

## 6. Compatibility failure handling

The system blocks or reports a compatibility failure when:

- a Contract Engineering skill claims a Superpowers-owned skill name;
- a command attempts to approve a design or packet without user approval;
- a Superpowers plan has no corresponding design contract when one is
  required;
- packet admission is attempted before the Contract Engineering gate;
- a hook assumes a harness-specific environment variable without a fallback;
- a plugin-relative path escapes the root package;
- a local runtime loads remote assets or starts a non-local listener.

The failure record points to the plugin, skill, command, packet, and design
revision involved. No fork synchronization or upstream mutation is attempted.

## 7. Acceptance criteria

- A clean Factory installation can install both plugins without duplicate
  skill names or overwritten files.
- Superpowers brainstorming and planning remain available and are not copied.
- Contract Engineering receives the approved design/plan as governed input.
- Contract Engineering admission blocks worker execution until design and
  packet gates pass.
- Root-level marketplace and plugin manifests validate from a clean checkout.
- Session bootstrap behavior is additive and does not replace Superpowers
  bootstrap content.
- Existing Contract Engineering project records remain the canonical source
  of state and evidence.
