# Contract Engineering and Superpowers Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Contract Engineering a root-level Factory plugin that composes with Superpowers without duplicating its general workflow skills, while enforcing design contracts and packet admission.

**Architecture:** Superpowers remains the general workflow plugin. Contract Engineering adds uniquely named governance skills, commands, droids, validators, hooks, and project records. The repository root is the Factory marketplace and plugin, so no nested copy of `skills/` is created.

**Tech Stack:** Factory plugin manifests, Markdown skills/commands/droids, Factory session hooks, Python 3 standard-library validators and localhost preview tools, YAML/JSON Schema, Mermaid source with a pinned local runtime, sanitized SVG, unittest, and GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-15-design-contract-factory-plugin-superpowers-design.md`, with the base requirements in `docs/superpowers/specs/2026-09-15-design-contract-factory-plugin-design.md`.

## Global Constraints

- Compose with Superpowers; do not fork it, copy its general skills, or modify its repository.
- Do not create Contract Engineering skills named `using-superpowers`, `brainstorming`, `writing-plans`, `subagent-driven-development`, `using-git-worktrees`, or `test-driven-development`.
- The root `.factory-plugin/marketplace.json` points to `"./"` and the root `.factory-plugin/plugin.json` describes the package.
- Repository records under `.contract-engineering/` remain the canonical project state.
- Design and packet admission remain hard gates before worker execution.
- Visual artifacts are offline-safe, localhost-only, hashed, and sanitized.
- No task publishes a release or updates a consumer lock to an unreleased revision.

---

## Child packet decomposition

Create these implementation packets after this plan is accepted:

| Packet | Deliverable | Dependencies |
| --- | --- | --- |
| `CENG-T014-P003` | Design-contract schema, artifact manifest, and admission validator | `CENG-T014-P001` |
| `CENG-T014-P004` | Offline HTML/Mermaid/SVG preview and safety runtime | `CENG-T014-P003` |
| `CENG-T014-P005` | Unique Contract Engineering commands, governance skills, and droids | `CENG-T014-P003`, `CENG-T014-P004` |
| `CENG-T014-P006` | Additive session bootstrap, PreToolUse policy hooks, and CI gates | `CENG-T014-P003`, `CENG-T014-P005` |
| `CENG-T014-P007` | Root-level Factory marketplace/plugin manifests and clean-install checks | `CENG-T014-P004`, `CENG-T014-P005`, `CENG-T014-P006` |
| `CENG-T014-P008` | Consumer migration, Superpowers compatibility docs, rollout, and rollback | `CENG-T014-P003` through `CENG-T014-P007` |

The child packet IDs remain unchanged from the original plan. Their scopes
change from nested plugin paths to root-level paths as specified below.

### Task 1: Design-contract schema and admission (`CENG-T014-P003`)

**Files:**
- Create: `schemas/design-contract.schema.json`
- Create: `templates/design-contract.yaml`
- Create: `scripts/validate-design-contracts.py`
- Create: `scripts/validate-admission.py`
- Create: `tests/test_design_contracts.py`
- Modify: `scripts/validate-contract-records.py`
- Modify: `.github/workflows/protocol-validation.yml`

**Interfaces:**
- Produces `load_design`, `required_artifacts`, `validate_design`, and
  `validate_admission` for later packets.
- Uses `.contract-engineering/designs/<TASK-ID>/design.yaml` and approved
  Superpowers design/plan artifacts as governed inputs.

- [ ] Write failing tests for text, UI, architecture, stale approval, scope,
  review, and design-criterion trace failures.
- [ ] Implement the schema/template and required artifact rules from the
  base design.
- [ ] Implement cross-record admission checks for approved design, decision,
  scope, reviews, packet criteria, dependencies, authorization, leases, and
  resources.
- [ ] Integrate validation with existing record validation and CI.
- [ ] Run focused tests, all repository tests, record validation, and tracker
  validation.
- [ ] Commit as `feat: enforce design contract admission` and submit the child
  packet for review.

### Task 2: Offline visual artifact runtime (`CENG-T014-P004`)

**Files:**
- Create: `scripts/preview-design.py`
- Create: `scripts/render-mermaid.py`
- Create: `scripts/sanitize-svg.py`
- Create: `tests/test_design_preview.py`
- Create: `tests/fixtures/designs/`
- Create: `runtime/mermaid.min.js`
- Modify: `schemas/design-contract.schema.json`

**Interfaces:**
- Produces `validate_artifact_manifest`, `start_preview`,
  `render_mermaid`, and `sanitize_svg`.
- Later plugin commands invoke the scripts from the repository root.

- [ ] Write failing tests for localhost binding, root confinement, hash
  mismatch, SVG safety, HTML safety, and missing-renderer behavior.
- [ ] Implement manifest validation, path confinement, and SHA-256 checks.
- [ ] Implement HTML/SVG safety filters and local Mermaid rendering.
- [ ] Implement a Python standard-library localhost server with runtime
  fallback detection.
- [ ] Run safe and unsafe fixtures plus focused/full tests.
- [ ] Commit as `feat: add offline design artifact preview` and submit the
  child packet for review.

### Task 3: Governance skills, commands, and droids (`CENG-T014-P005`)

**Files:**
- Create: `skills/contract-design/SKILL.md`
- Create: `skills/contract-review/SKILL.md`
- Create: `skills/contract-admission/SKILL.md`
- Create: `skills/contract-visual-review/SKILL.md`
- Create: `skills/contract-handoff-acceptance/SKILL.md`
- Create: `commands/contract-plan.md`
- Create: `commands/contract-review.md`
- Create: `commands/contract-admit.md`
- Create: `commands/design-preview.md`
- Create: `droids/contract-designer.md`
- Create: `droids/contract-reviewer.md`
- Create: `droids/contract-supervisor.md`
- Create: `tests/test_factory_interfaces.py`

**Interfaces:**
- Produces uniquely named Contract Engineering skills and Factory
  commands/droids; it does not provide Superpowers-owned workflow skills.
- Commands consume Task 1 validators and Task 2 preview tooling.

- [ ] Write metadata and routing tests proving no forbidden duplicate skill
  names exist.
- [ ] Implement `contract-design` to consume Superpowers brainstorming and
  create/update governed design records without approving them.
- [ ] Implement `contract-review` and the reviewer droid to record explicit
  design/architecture/security/data/visual review outcomes.
- [ ] Implement `contract-admit` and the supervisor droid to run validators,
  show blocked reasons, and create bounded packet proposals only after gates.
- [ ] Implement `design-preview` to validate manifests and launch local
  previews.
- [ ] Run metadata, routing, and validator tests.
- [ ] Commit as `feat: add Contract Engineering governance skills` and submit
  the child packet for review.

### Task 4: Additive bootstrap, hooks, and CI (`CENG-T014-P006`)

**Files:**
- Create: `hooks/hooks.json`
- Create: `hooks/session-start`
- Create: `hooks/enforce-packet-scope.py`
- Create: `hooks/enforce-admission.py`
- Create: `runtime/contract_policy.py`
- Create: `tests/test_factory_hooks.py`
- Modify: `.github/workflows/protocol-validation.yml`
- Modify: `.github/workflows/security.yml`

**Interfaces:**
- Produces `evaluate_tool_call(project_root, tool_name, tool_input)` and
  additive session context.
- Uses `${DROID_PLUGIN_ROOT}` for plugin-local hooks and falls back to
  project-local paths only when the host provides them.

- [ ] Write tests for no-packet denial, out-of-scope denial, external-effect
  approval, safe reads, canonical-record protection, and input sanitization.
- [ ] Implement session context that reminds the agent of Contract
  Engineering gates without copying or replacing Superpowers bootstrap text.
- [ ] Implement PreToolUse scope/admission enforcement with exit code `2` for
  blocking decisions.
- [ ] Add CI steps for design, admission, artifact, scope, plugin, and
  generated-projection checks.
- [ ] Run hook tests and all local validation.
- [ ] Commit as `feat: enforce Contract Engineering in Factory hooks` and
  submit the child packet for review.

### Task 5: Root-level Factory plugin packaging (`CENG-T014-P007`)

**Files:**
- Create: `.factory-plugin/marketplace.json`
- Modify: `.factory-plugin/plugin.json`
- Create: `scripts/build-factory-plugin.py`
- Create: `scripts/validate-factory-plugin.py`
- Create: `tests/test_factory_plugin_package.py`
- Modify: `README.md`
- Modify: `adapters/factory-droid/README.md`
- Modify: `.github/workflows/protocol-validation.yml`

**Interfaces:**
- Produces a root-level marketplace with one plugin whose source is `"./"`.
- Validates `skills/`, `commands/`, `droids/`, `hooks/`, `runtime/`, and
  existing `schemas/`, `templates/`, and `scripts/` without copying or
  overwriting them.

- [ ] Write tests for marketplace source, manifest identity, unique skill
  names, safe relative paths, and Superpowers coexistence.
- [ ] Add root marketplace metadata and update plugin metadata.
- [ ] Implement deterministic package validation and optional clean Factory
  CLI installation in an isolated temporary HOME.
- [ ] Document separate installation of both plugins and their ownership
  boundary.
- [ ] Run package checks and full repository validation.
- [ ] Commit as `feat: package Contract Engineering for Factory` and submit
  the child packet for review.

### Task 6: Compatibility migration and operations (`CENG-T014-P008`)

**Files:**
- Create: `templates/design-review.yaml`
- Create: `templates/design-artifact-manifest.yaml`
- Create: `templates/factory-consumer.yaml`
- Create: `tests/test_design_documentation.py`
- Modify: `docs/protocol-configuration.md`
- Modify: `docs/supervisor-workflow.md`
- Modify: `docs/repository-development.md`
- Modify: `templates/AGENTS.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Documents how consuming repositories install both plugins, pin the
  Contract Engineering release, and retain project records locally.
- Documents migration from legacy packets and report-only admission.

- [ ] Write tests for compatibility docs, migration mode, visual artifact
  rules, installation, rollback, and canonical record ownership.
- [ ] Add templates and consumer setup/preflight guidance.
- [ ] Document the ordering:
  `brainstorming -> contract-design -> writing-plans -> contract-admission
  -> subagent-driven-development -> handoff acceptance`.
- [ ] Document failure, rollback, and limitation handling.
- [ ] Run documentation, link, plugin, design, admission, tracker, and full
  test validation.
- [ ] Commit as `docs: document Superpowers compatibility` and submit the
  child packet for review.

## Final integration gate

After child packets are independently accepted, run:

```bash
python3 scripts/validate-factory-plugin.py --root .
python3 scripts/validate-design-contracts.py --root .contract-engineering
python3 scripts/validate-admission.py --root .contract-engineering --all-ready
python3 scripts/validate-contract-records.py
python3 scripts/validate-tracker.py --root .contract-engineering
python3 scripts/render-tracker.py --root .contract-engineering --check
python3 -m unittest discover -s tests -p 'test_*.py'
```

If the Factory CLI is available, install both plugins into an isolated
temporary home and verify that each plugin's skills, commands, droids, and
hooks load without collisions. If it is unavailable, record the structural
validation result and limitation; do not claim a live-install test passed.
