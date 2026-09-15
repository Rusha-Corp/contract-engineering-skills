# Design Contract and Factory Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved design-contract lifecycle, offline visual-review artifacts, deterministic admission enforcement, and clean-installable Factory Droid plugin.

**Architecture:** Keep project-specific contracts, approvals, artifacts, evidence, packets, and tracker state in each consuming repository. Package reusable skills, commands, droids, hooks, and runtime policy in a nested Factory plugin. Make repository validators and CI authoritative, use Factory hooks for local fail-fast behavior, and let the optional host supervisor enforce process, lease, resource, and session controls.

**Tech Stack:** YAML and JSON Schemas, Python 3 standard library, existing unittest suite, Markdown Factory commands/droids, Factory plugin hooks, Mermaid source with a pinned local runtime, static HTML/CSS/JavaScript, sanitized SVG, localhost HTTP serving, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-15-design-contract-factory-plugin-design.md`

## Global Constraints

- No implementation packet may enter `Ready` or be admitted until the user-approved design contract, required contract reviews, packet scope, and packet acceptance contract pass validation.
- Project records remain under `.contract-engineering/`; the plugin does not become a second source of truth.
- Visual artifacts are required for UI, UX, architecture, workflow, and data-flow work; text-only work remains supported.
- HTML previews and SVGs are local, offline-safe, read-only review artifacts with no credentials, external network, remote scripts, fonts, images, or telemetry.
- Mermaid source is canonical; generated SVGs are derived, sanitized, hashed, and never accepted when stale.
- Preview servers bind only to `127.0.0.1`, serve only the selected design directory, and do not install dependencies.
- Factory hooks fail closed for packet-scope and admission violations; CI and repository validators remain authoritative when hooks are unavailable.
- Existing legacy consumers remain compatible until an explicit migration packet enables mandatory design contracts.
- No task in this plan publishes a release or changes the six published protocol skill files.

---

## File and packet map

The implementation is split into six child packets under parent packet
`CENG-T014-P002`. Each child packet receives a non-overlapping scope,
structured acceptance contract, design reference
`CENG-T014-P001-DEC001`, and a dependency edge:

| Child packet | Responsibility | Depends on |
| --- | --- | --- |
| `CENG-T014-P003` | Design-contract schema, template, validator, fixtures | `CENG-T014-P001` |
| `CENG-T014-P004` | Visual artifact manifest, preview server, Mermaid/SVG/HTML safety | `CENG-T014-P003` |
| `CENG-T014-P005` | Factory planning, review, admission, and preview commands/droids | `CENG-T014-P003`, `CENG-T014-P004` |
| `CENG-T014-P006` | Factory hooks, runtime policy, and CI admission enforcement | `CENG-T014-P003`, `CENG-T014-P005` |
| `CENG-T014-P007` | Nested plugin packaging, marketplace manifest, clean-install checks | `CENG-T014-P004`, `CENG-T014-P005`, `CENG-T014-P006` |
| `CENG-T014-P008` | Consumer migration, documentation, rollout, and rollback | `CENG-T014-P003` through `CENG-T014-P007` |

The parent coordination packet creates and sequences these child packets. It
does not modify implementation files.

## Shared interfaces

The first child packet defines the record-level interfaces used by later
packets:

```python
def load_design(path: Path) -> dict[str, Any]:
    """Load one design-contract YAML document."""

def required_artifacts(design_type: str) -> set[str]:
    """Return required artifact kinds for a design type."""

def validate_design(root: Path, design_path: Path) -> None:
    """Raise a validation error for an invalid design contract."""

def validate_admission(project_root: Path, packet_path: Path) -> None:
    """Fail closed unless design, review, scope, and packet gates pass."""
```

The visual packet consumes the artifact manifest through:

```python
def validate_artifact_manifest(
    design_root: Path,
    manifest: list[dict[str, str | bool]],
) -> None:
    """Validate safe paths, required files, and SHA-256 bindings."""

def start_preview(
    design_root: Path,
    host: str = "127.0.0.1",
    port: int = 0,
) -> str:
    """Serve one design directory and return its local URL."""
```

The Factory hook runtime consumes the admission boundary through:

```python
def evaluate_tool_call(
    project_root: Path,
    tool_name: str,
    tool_input: dict[str, Any],
) -> tuple[str, str]:
    """Return (allow|deny|ask, reason) for one Droid tool call."""
```

Later tasks must preserve these names and semantics or update every consumer
and its packet acceptance evidence in the same change.

---

### Task 1: Design-contract schema and validation (`CENG-T014-P003`)

**Files:**
- Create: `schemas/design-contract.schema.json`
- Create: `templates/design-contract.yaml`
- Create: `scripts/validate-design-contracts.py`
- Create: `scripts/validate-admission.py`
- Create: `tests/test_design_contracts.py`
- Create: `tests/fixtures/design-contracts/text-approved.yaml`
- Create: `tests/fixtures/design-contracts/ui-approved.yaml`
- Create: `tests/fixtures/design-contracts/invalid-missing-artifact.yaml`
- Create: `tests/fixtures/design-contracts/invalid-stale-approval.yaml`
- Create: `tests/fixtures/design-contracts/invalid-scope.yaml`
- Modify: `scripts/validate-contract-records.py`
- Modify: `.github/workflows/protocol-validation.yml`

**Interfaces:**
- Consumes: `.contract-engineering/designs/<TASK-ID>/design.yaml`, packet
  records, decision records, artifact manifests, and existing validator
  helpers.
- Produces: `load_design`, `required_artifacts`, `validate_design`, and
  `validate_admission` with nonzero exit status for missing or ambiguous
  records.

- [ ] **Step 1: Write failing schema and validator tests**

Add tests for:

```python
def test_text_design_does_not_require_visual_artifacts(): ...
def test_ui_design_requires_reviewable_visual_artifact(): ...
def test_architecture_design_requires_mermaid_and_svg(): ...
def test_approval_must_bind_to_artifact_manifest_revision(): ...
def test_packet_scope_must_be_covered_by_design_scope(): ...
def test_packet_criteria_must_reference_design_criteria(): ...
def test_rejected_review_blocks_admission(): ...
```

Run:

```bash
python3 -m unittest tests.test_design_contracts -v
```

Expected: FAIL because the schema, fixtures, and validators do not exist.

- [ ] **Step 2: Define the JSON Schema and reusable YAML template**

Implement the fields from the approved design:
`design_contract_version`, `design_id`, `task_id`, `status`, `design_type`,
problem, scope, architecture, alternatives, decisions, artifacts, reviews,
acceptance contract, and revision-bound approval.

Use identifier patterns matching the existing packet/decision conventions.
Require `artifact.sha256` for every artifact and require an authenticated
approval record for `status: approved`.

- [ ] **Step 3: Implement design validation**

Implement `load_design`, `required_artifacts`, and `validate_design` in
`scripts/validate-design-contracts.py`. Reuse the repository's safe YAML
loading and failure-reporting conventions. Validate:

```python
REQUIRED_BY_TYPE = {
    "ui": {"html"},
    "ux": {"html"},
    "architecture": {"architecture", "mermaid", "svg"},
    "workflow": {"mermaid"},
    "data-flow": {"data-flow", "mermaid", "svg"},
    "mixed": set(),
    "text": set(),
}
```

For `mixed`, require the union implied by the declared artifact kinds and
review records. Reject unsafe relative paths, duplicate artifact paths,
invalid SHA-256 values, stale approvals, and missing acceptance criteria.

- [ ] **Step 4: Implement cross-record admission validation**

Implement `validate_admission(project_root, packet_path)` in
`scripts/validate-admission.py`. Resolve `design_decision_ref` and the
design contract, then fail closed unless:

```python
design["status"] == "approved"
decision["status"] == "approved"
packet["design_decision_ref"] == decision["decision_id"]
packet_scope <= approved_design_scope
all_required_reviews_accepted(design)
all_packet_criteria_trace_to_design(packet, design)
```

Delegate packet state, dependency, authorization, lease, resource, and
handoff checks to existing validators rather than duplicating them.

- [ ] **Step 5: Add repository and CI integration**

Make `validate-contract-records.py` discover and validate design contracts
when the project contains `.contract-engineering/designs/`. Add a CI job step
that runs:

```bash
python3 scripts/validate-design-contracts.py --root .contract-engineering
python3 scripts/validate-admission.py --root .contract-engineering --all-ready
```

Keep the legacy path valid when no design contracts exist, unless a new packet
declares a design type that requires one.

- [ ] **Step 6: Run focused and full tests**

```bash
python3 -m unittest tests.test_design_contracts -v
python3 scripts/validate-contract-records.py
python3 scripts/validate-tracker.py --root .contract-engineering
python3 -m unittest discover -s tests -p 'test_*.py'
```

Expected: PASS, with invalid fixtures rejected and existing records unchanged.

- [ ] **Step 7: Commit the child packet**

```bash
git add schemas/design-contract.schema.json templates/design-contract.yaml \
  scripts/validate-design-contracts.py scripts/validate-admission.py \
  scripts/validate-contract-records.py tests .github/workflows/protocol-validation.yml
git commit -m "feat: enforce design contract admission"
```

Record evidence and submit the child packet for independent review before
starting Task 2.

---

### Task 2: Offline visual artifact runtime (`CENG-T014-P004`)

**Files:**
- Create: `scripts/preview-design.py`
- Create: `scripts/render-mermaid.py`
- Create: `scripts/sanitize-svg.py`
- Create: `tests/test_design_preview.py`
- Create: `tests/fixtures/designs/ui-basic/design.yaml`
- Create: `tests/fixtures/designs/ui-basic/index.html`
- Create: `tests/fixtures/designs/architecture-basic/system.mmd`
- Create: `tests/fixtures/designs/architecture-basic/system.svg`
- Create: `tests/fixtures/designs/unsafe/scripted.svg`
- Create: `tests/fixtures/designs/unsafe/remote.html`
- Create: `plugins/contract-engineering-skills/runtime/mermaid.min.js`
- Modify: `schemas/design-contract.schema.json`

**Interfaces:**
- Consumes: approved design artifact manifests and Task 1 validators.
- Produces: `validate_artifact_manifest`, `start_preview`,
  `render_mermaid`, and `sanitize_svg`.

- [ ] **Step 1: Write failing safety and server tests**

Add tests for:

```python
def test_preview_binds_localhost_and_serves_only_design_root(): ...
def test_manifest_rejects_path_traversal_and_symlink_escape(): ...
def test_manifest_rejects_hash_mismatch(): ...
def test_svg_sanitizer_rejects_scripts_external_refs_and_handlers(): ...
def test_html_policy_rejects_remote_scripts_forms_and_network_urls(): ...
def test_missing_renderer_does_not_report_visual_review_passed(): ...
```

Run:

```bash
python3 -m unittest tests.test_design_preview -v
```

Expected: FAIL because the preview, renderer, and safety functions do not
exist.

- [ ] **Step 2: Implement artifact manifest validation**

Share the manifest validation boundary with Task 1. Resolve every path below
the selected design directory, reject symlinks that escape it, calculate
SHA-256 from bytes, and compare it with the manifest before serving or
rendering.

- [ ] **Step 3: Implement HTML and SVG safety checks**

Reject remote URL schemes and references, form submissions, credential access,
browser-storage access, external script/font/image loads, SVG scripts,
event-handler attributes, and external SVG references. Treat all artifact
content as untrusted data.

- [ ] **Step 4: Implement the localhost preview server**

Use `http.server.ThreadingHTTPServer` when `python3` or `python` is
available. Bind explicitly to `127.0.0.1`, select an ephemeral port when
`--port 0` is supplied, serve only the validated design directory, and print
the URL plus a foreground shutdown instruction. Do not spawn background
processes or install dependencies.

- [ ] **Step 5: Implement Mermaid rendering and fallback**

Store the pinned Mermaid runtime under the plugin runtime directory. The
browser preview uses the local runtime. `render-mermaid.py` invokes a
host-provided Mermaid CLI only when available, validates its SVG output with
`sanitize-svg.py`, and returns a nonzero status when required rendering is
unavailable. The fallback displays Mermaid source but never marks the visual
review passed.

- [ ] **Step 6: Run preview and safety tests**

```bash
python3 -m unittest tests.test_design_preview -v
python3 scripts/preview-design.py --root tests/fixtures/designs/ui-basic --port 0 --no-open
python3 scripts/sanitize-svg.py tests/fixtures/designs/architecture-basic/system.svg
python3 scripts/sanitize-svg.py tests/fixtures/designs/unsafe/scripted.svg
```

Expected: the preview starts on localhost, the safe SVG passes, and the
unsafe SVG exits nonzero.

- [ ] **Step 7: Commit the child packet**

```bash
git add scripts/preview-design.py scripts/render-mermaid.py scripts/sanitize-svg.py \
  tests/test_design_preview.py tests/fixtures/designs plugins/contract-engineering-skills/runtime
git commit -m "feat: add offline design artifact preview"
```

---

### Task 3: Factory planning, review, admission, and preview interfaces (`CENG-T014-P005`)

**Files:**
- Create: `plugins/contract-engineering-skills/commands/contract-plan.md`
- Create: `plugins/contract-engineering-skills/commands/contract-review.md`
- Create: `plugins/contract-engineering-skills/commands/contract-admit.md`
- Create: `plugins/contract-engineering-skills/commands/design-preview.md`
- Create: `plugins/contract-engineering-skills/droids/contract-designer.md`
- Create: `plugins/contract-engineering-skills/droids/contract-reviewer.md`
- Create: `plugins/contract-engineering-skills/droids/contract-supervisor.md`
- Create: `tests/test_factory_interfaces.py`
- Modify: `docs/superpowers/specs/2026-09-15-design-contract-factory-plugin-design.md`

**Interfaces:**
- Consumes: Task 1 validators, Task 2 preview command, project-local
  `.contract-engineering` records, and Factory session identity.
- Produces: user-invoked commands and bounded subagent prompts that create
  records but do not silently approve or admit work.

- [ ] **Step 1: Write command metadata tests**

Test that each command has valid frontmatter, a clear description, safe
argument handling, and explicit stop points:

```python
def test_contract_plan_stops_for_user_approval(): ...
def test_contract_review_requires_named_design_revision(): ...
def test_contract_admit_runs_validators_before_plan_output(): ...
def test_design_preview_invokes_local_preview_only(): ...
def test_droids_cannot_self_approve_or_self_review(): ...
```

- [ ] **Step 2: Write the planning command**

`contract-plan.md` must guide the user through problem, users, priority,
constraints, open questions, architecture, alternatives, risks, visual
artifacts, reviews, and measurable acceptance criteria. It creates or updates
`design.yaml` with `status: proposed` or `in_review`; it never sets
`status: approved`.

- [ ] **Step 3: Write the review command and droid**

`contract-review.md` and `contract-reviewer.md` inspect named design
revisions, review each criterion individually, and record accepted or rejected
review records. They must be independent for high-risk or external-effect
work and must not change approval status.

- [ ] **Step 4: Write the admission command and supervisor droid**

`contract-admit.md` runs the design and admission validators, displays blocked
reasons, and only then proposes parent and child packet records. The
supervisor droid may categorize and order packets but cannot approve the
design, approve its own work, or skip a gate.

- [ ] **Step 5: Write the preview command**

`design-preview.md` validates the selected artifact manifest and invokes
`preview-design.py` with a localhost-only root. It must clearly label source,
derived output, renderer limitations, and design revision.

- [ ] **Step 6: Run interface checks**

```bash
python3 -m unittest tests.test_factory_interfaces -v
python3 scripts/validate-design-contracts.py --root .contract-engineering
```

Expected: all metadata and command-policy tests pass.

- [ ] **Step 7: Commit the child packet**

```bash
git add plugins/contract-engineering-skills/commands \
  plugins/contract-engineering-skills/droids tests/test_factory_interfaces.py
git commit -m "feat: add design contract Factory commands"
```

---

### Task 4: Factory hooks, runtime policy, and CI enforcement (`CENG-T014-P006`)

**Files:**
- Create: `plugins/contract-engineering-skills/hooks/hooks.json`
- Create: `plugins/contract-engineering-skills/hooks/enforce-packet-scope.py`
- Create: `plugins/contract-engineering-skills/hooks/enforce-admission.py`
- Create: `plugins/contract-engineering-skills/runtime/contract_policy.py`
- Create: `tests/test_factory_hooks.py`
- Modify: `.github/workflows/protocol-validation.yml`
- Modify: `.github/workflows/security.yml`

**Interfaces:**
- Consumes: Task 1 admission validator, Task 3 command boundaries, Factory
  hook JSON stdin, current project directory, and packet scope.
- Produces: `evaluate_tool_call(project_root, tool_name, tool_input)` and
  hook scripts that exit `2` with a clear blocking reason.

- [ ] **Step 1: Write hook-policy tests**

```python
def test_edit_without_claimed_packet_is_denied(): ...
def test_edit_outside_scope_is_denied(): ...
def test_execute_publish_requires_approval(): ...
def test_read_only_design_review_is_allowed(): ...
def test_direct_tracker_state_edit_is_denied(): ...
def test_hook_input_paths_are_sanitized(): ...
```

- [ ] **Step 2: Implement the shared policy evaluator**

Parse hook JSON from stdin, resolve the project root from `cwd`, load the
active packet, and return:

```python
("allow", "read-only inspection")
("deny", "no claimed packet covers this write")
("ask", "external effect requires user approval")
```

Never trust tool-provided paths, packet IDs, or command strings without
normalizing and validating them against the project root and packet scope.

- [ ] **Step 3: Implement Factory hook declarations**

Match `Create|Edit|ApplyPatch` for packet-scope checks and `Execute` for
admission/external-effect checks. Use `${DROID_PLUGIN_ROOT}` for plugin
scripts and keep timeouts bounded. Hooks must not log prompts, credentials,
cookies, or raw tool payloads.

- [ ] **Step 4: Add CI enforcement**

Add per-job steps for design validation, admission validation, scope checks,
artifact safety, and plugin policy tests. Keep checkout credentials, job
permissions, timeouts, and concurrency explicit for every job.

- [ ] **Step 5: Run hook and workflow checks**

```bash
python3 -m unittest tests.test_factory_hooks -v
python3 scripts/validate-design-contracts.py --root .contract-engineering
python3 scripts/validate-admission.py --root .contract-engineering --all-ready
python3 scripts/validate-contract-records.py
```

Expected: unsafe fixtures are denied and current repository records pass.

- [ ] **Step 6: Commit the child packet**

```bash
git add plugins/contract-engineering-skills/hooks \
  plugins/contract-engineering-skills/runtime/contract_policy.py \
  tests/test_factory_hooks.py .github/workflows
git commit -m "feat: enforce packet admission in Factory hooks"
```

---

### Task 5: Nested Factory plugin packaging and clean installation (`CENG-T014-P007`)

**Files:**
- Create: `.factory-plugin/marketplace.json`
- Create: `plugins/contract-engineering-skills/.factory-plugin/plugin.json`
- Create: `plugins/contract-engineering-skills/README.md`
- Create: `scripts/build-factory-plugin.py`
- Create: `scripts/validate-factory-plugin.py`
- Create: `tests/test_factory_plugin_package.py`
- Modify: `README.md`
- Modify: `adapters/factory-droid/README.md`
- Modify: `.github/workflows/protocol-validation.yml`

**Interfaces:**
- Consumes: root skills, Task 2 runtime, Task 3 commands/droids, Task 4
  hooks/runtime, and the plugin manifest.
- Produces: a deterministic nested plugin tree and validation command:

```bash
python3 scripts/build-factory-plugin.py --check
python3 scripts/validate-factory-plugin.py --root plugins/contract-engineering-skills
```

- [ ] **Step 1: Write packaging tests**

```python
def test_marketplace_points_to_nested_plugin(): ...
def test_plugin_contains_all_six_governed_skills(): ...
def test_plugin_relative_paths_stay_inside_package(): ...
def test_generated_plugin_matches_canonical_sources(): ...
def test_clean_install_command_is_documented(): ...
```

- [ ] **Step 2: Add marketplace and plugin manifests**

The root `.factory-plugin/marketplace.json` points to
`./plugins/contract-engineering-skills`. The nested `plugin.json` declares
the plugin name, version, repository, license, and description. The package
must contain the six governed skills and all command, droid, hook, and runtime
files.

- [ ] **Step 3: Implement deterministic packaging**

`build-factory-plugin.py` copies or verifies canonical files without
overwriting user directories. It must fail if a source is missing, a
generated file differs, or a destination escapes the plugin root.

- [ ] **Step 4: Implement clean-checkout validation**

`validate-factory-plugin.py` checks manifests, skill frontmatter and hashes,
command/droid metadata, hook paths, runtime assets, and forbidden external
references. If the Factory CLI is installed, the test may run a local
marketplace install in an isolated temporary HOME. If the CLI is unavailable,
the structural check remains mandatory and records that limitation.

- [ ] **Step 5: Update installation documentation**

Document:

```bash
droid plugin marketplace add https://github.com/Rusha-Corp/contract-engineering-skills
droid plugin install contract-engineering-skills@contract-engineering-skills --scope user
```

Also document project-scope installation, protocol-lock preflight, update,
rollback, and the rule not to overwrite existing skill directories.

- [ ] **Step 6: Run packaging checks**

```bash
python3 scripts/build-factory-plugin.py --check
python3 scripts/validate-factory-plugin.py --root plugins/contract-engineering-skills
python3 -m unittest tests.test_factory_plugin_package -v
```

Expected: the package is reproducible and all plugin paths resolve safely.

- [ ] **Step 7: Commit the child packet**

```bash
git add .factory-plugin plugins scripts/build-factory-plugin.py \
  scripts/validate-factory-plugin.py tests/test_factory_plugin_package.py \
  README.md adapters/factory-droid/README.md .github/workflows/protocol-validation.yml
git commit -m "feat: package Contract Engineering for Factory"
```

---

### Task 6: Consumer migration and operational documentation (`CENG-T014-P008`)

**Files:**
- Create: `templates/design-review.yaml`
- Create: `templates/design-artifact-manifest.yaml`
- Create: `templates/factory-consumer.yaml`
- Modify: `docs/protocol-configuration.md`
- Modify: `docs/supervisor-workflow.md`
- Modify: `docs/repository-development.md`
- Modify: `templates/AGENTS.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Create: `tests/test_design_documentation.py`

**Interfaces:**
- Consumes: all prior child-packet records, validators, plugin layout, and
  approved design contract.
- Produces: consumer setup guidance, migration mode, rollout gates,
  rollback instructions, and documentation cross-reference checks.

- [ ] **Step 1: Write documentation tests**

```python
def test_docs_define_design_contract_setup(): ...
def test_docs_define_legacy_migration_mode(): ...
def test_docs_define_visual_artifact_policy(): ...
def test_docs_define_factory_install_and_rollback(): ...
def test_templates_reference_canonical_project_records(): ...
```

- [ ] **Step 2: Add consumer templates**

Create a design-review template, artifact-manifest template, and Factory
consumer inventory template. Keep project-specific approvals, actor identity,
and records in the consuming repository.

- [ ] **Step 3: Document migration and rollout**

Document report-only admission, blocking hooks for low-risk work, mandatory
design contracts for new visual/architecture work, CI enforcement, supervisor
enablement, legacy packet handling, rollback, and limitations.

- [ ] **Step 4: Run documentation and full validation**

```bash
python3 -m unittest tests.test_design_documentation -v
python3 scripts/check-markdown-links.py
python3 scripts/validate-design-contracts.py --root .contract-engineering
python3 scripts/validate-admission.py --root .contract-engineering --all-ready
python3 scripts/validate-contract-records.py
python3 scripts/validate-tracker.py --root .contract-engineering
python3 scripts/render-tracker.py --root .contract-engineering --check
python3 -m unittest discover -s tests -p 'test_*.py'
```

- [ ] **Step 5: Commit the child packet**

```bash
git add templates/design-review.yaml templates/design-artifact-manifest.yaml \
  templates/factory-consumer.yaml docs templates/AGENTS.md README.md \
  CHANGELOG.md tests/test_design_documentation.py
git commit -m "docs: document design contract migration"
```

---

## Final integration gate

After all child packets are independently accepted, the parent coordinator
creates one integration worktree and runs:

```bash
python3 scripts/build-factory-plugin.py --check
python3 scripts/validate-factory-plugin.py --root plugins/contract-engineering-skills
python3 scripts/validate-design-contracts.py --root .contract-engineering
python3 scripts/validate-admission.py --root .contract-engineering --all-ready
python3 scripts/validate-contract-records.py
python3 scripts/validate-tracker.py --root .contract-engineering
python3 scripts/render-tracker.py --root .contract-engineering --check
python3 -m unittest discover -s tests -p 'test_*.py'
```

The integration packet records clean-install results when the Factory CLI is
available and records the structural validation limitation when it is not.
No release or consumer lock update occurs until the replacement protocol
release has passed its independent review, attestation, and stable CI gate.
