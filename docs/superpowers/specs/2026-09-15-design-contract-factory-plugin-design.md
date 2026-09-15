# Design Contract and Factory Plugin Architecture

Status: approved for specification
Decision: `CENG-T014-P001-DEC001`
Packet: `CENG-T014-P001`
Date: 2026-09-15

## 1. Purpose

Contract-Driven Engineering currently has strong packet, handoff, and
admission primitives, but the design phase is not yet a first-class,
machine-checked contract. This design adds a user-led design contract before
implementation packet decomposition and packages the protocol as an
installable Factory Droid plugin.

The design also makes visual review a governed artifact flow. UI, UX,
architecture, workflow, and data-flow work can produce repository-local HTML,
Mermaid, SVG, and tradeoff artifacts that the user can inspect through a
localhost preview. Text-only work remains supported.

The central invariant is:

> No implementation packet may enter `Ready` or be admitted to a worker until
> the user-approved design contract, required contract reviews, packet scope,
> and packet acceptance contract all pass validation.

## 2. Goals and non-goals

### Goals

- Capture requirements, architecture, alternatives, constraints, risks, and
  acceptance criteria before implementation decomposition.
- Make design approval explicit, authenticated, revision-bound, and
  reviewable.
- Require visual artifacts for visual work without forcing diagrams onto
  text-only work.
- Keep design artifacts in the consuming repository under
  `.contract-engineering/designs/`.
- Provide offline-safe previews using a pinned local Mermaid runtime and a
  localhost-only static server.
- Generate SVG artifacts as derived, hashed review outputs.
- Enforce the lifecycle through repository validators, Factory hooks, CI, and
  an optional host supervisor.
- Make the repository installable as a nested Factory Droid plugin from a
  marketplace.
- Preserve the existing repository/host responsibility boundary and provide a
  migration path for existing consumers.

### Non-goals

- Building a general-purpose design editor.
- Replacing Figma, a production diagramming service, or a ticketing system.
- Allowing HTML prototypes to perform external writes, network calls, or
  authentication.
- Making the repository own a consuming project's runtime leases, processes,
  CPU, memory, or spend.
- Automatically deciding product priority without user-confirmed impact and
  urgency.
- Publishing a protocol release as part of this packet.

## 3. User-led lifecycle

The host plugin exposes a planning workflow, but the user remains the
authority for requirements, architecture, and priority.

```text
/contract-plan
  -> draft task contract
  -> requirements and open questions
  -> design/architecture proposal
  -> alternatives and risk review
  -> visual artifact review when required
  -> contract reviews
  -> explicit user approval
  -> bounded packet DAG
  -> packet review and admission
  -> worker execution
  -> validation and evidence
  -> independent handoff acceptance
```

A draft task may exist while questions are unresolved. It is not an
implementation packet and cannot be admitted. After design approval, the
supervisor creates a parent-coordination packet and bounded child packets.
Child packets reference the approved design decision and may not broaden its
scope.

If implementation discovers an unrepresented requirement, the worker records
the discovery and stops at the packet boundary. The supervisor creates a
design revision or a new design contract and obtains approval before creating
additional implementation scope.

## 4. Design contract record

The implementation will add a versioned design-contract schema and template.
The canonical record is stored at:

```text
.contract-engineering/designs/<TASK-ID>/design.yaml
```

The design record contains:

```yaml
design_contract_version: 1
design_id: PROJECT-T001-DC001
task_id: PROJECT-T001
status: proposed|in_review|approved|rejected|superseded
design_type: ui|ux|architecture|workflow|data-flow|mixed|text
title: ""
problem:
  statement: ""
  users: []
  impact: ""
  urgency: ""
  constraints: []
open_questions: []
scope:
  in: []
  out: []
architecture:
  proposal: ""
  components: []
  data_flows: []
  trust_boundaries: []
alternatives:
  - id: ALT001
    proposal: ""
    benefits: []
    costs: []
    rejected_reason: ""
decisions:
  security: []
  data: []
  compatibility: []
  observability: []
  rollback: []
artifacts:
  - path: ""
    kind: requirements|architecture|tradeoffs|html|mermaid|svg
    sha256: ""
    required: true
reviews:
  - review_id: ""
    kind: design|architecture|security|data|compatibility|operations|visual
    reviewer: ""
    status: pending|accepted|rejected
    notes: ""
acceptance_contract:
  version: 1
  criteria: []
approval:
  approver: ""
  authenticated: false
  approved_at: ""
  approved_revision: ""
```

The design contract's acceptance criteria are task-level criteria. When the
supervisor decomposes the task, each child packet criterion must reference
one or more design criteria. A child criterion may make a criterion more
specific, but may not weaken or contradict it.

Approval binds to the design revision and the artifact manifest. Changing an
approved artifact changes the design revision and returns the design to
`in_review`.

## 5. Visual artifact contract

Artifact requirements depend on `design_type`:

| Design type | Required artifacts |
| --- | --- |
| `ui`, `ux` | At least one HTML prototype or approved visual artifact, interaction states, responsive/accessibility notes |
| `architecture` | Architecture narrative, Mermaid source, and rendered SVG |
| `workflow` | State/sequence representation, Mermaid source or equivalent SVG, failure and recovery states |
| `data-flow` | Data-flow narrative, trust-boundary representation, Mermaid source and rendered SVG |
| `mixed` | The union of each applicable type's requirements |
| `text` | Written design contract and acceptance contract only |

The canonical artifact is the editable source, not the generated SVG. The
manifest stores SHA-256 hashes for both source and derived outputs. A visual
review may not pass when a required renderer failed or when the derived SVG
does not match the source revision.

### HTML prototypes

HTML prototypes are static, local, and read-only. They may contain local CSS
and local JavaScript needed to demonstrate interaction states, but may not:

- submit forms to remote services;
- read credentials, cookies, or browser storage;
- call remote URLs;
- load external fonts, scripts, images, or telemetry;
- claim production data or production behavior without fixture evidence.

Each prototype includes a visible review header with the design ID, revision,
artifact status, known limitations, and a link to the acceptance criteria.

### Mermaid and SVG

Mermaid source is stored as `.mmd`. A pinned Mermaid runtime is shipped in the
plugin package. SVG output is generated locally, sanitized, and stored as a
derived artifact. SVG files must not contain scripts, external references,
event handlers, or embedded secrets.

If a Mermaid runtime or SVG renderer is unavailable, the preview command
shows the source and reports the renderer limitation. It must not report a
visual review as passed.

### Tradeoffs

Tradeoffs are represented in `tradeoffs.md` or a generated static HTML page.
Every rejected alternative must identify its cost, risk, and reason for
rejection. A tradeoff page is evidence for the design review, not a substitute
for approval.

## 6. Local preview runtime

The plugin supplies a preview command that resolves available host runtimes
in this order:

1. `python3` with the standard-library HTTP server;
2. `python` with the standard-library HTTP server;
3. a bundled Node static-server implementation when `node` is available;
4. a file/source fallback that does not claim a rendered preview.

The server:

- serves only the selected design directory;
- binds to `127.0.0.1`;
- selects an available local port;
- prints the URL, design revision, and shutdown command;
- never starts a background process without an explicit host command;
- does not install dependencies;
- does not require network access.

The preview launcher validates the artifact manifest before serving. It
rejects path traversal, symlinks escaping the design directory, malformed
artifact hashes, and missing required artifacts.

## 7. Review and admission enforcement

### Repository validator

`validate-design-contracts.py` validates:

- identifiers and version;
- design type and required artifacts;
- artifact paths and hashes;
- approval status and approved revision;
- review status and reviewer independence where required;
- acceptance contract structure;
- Mermaid/SVG and HTML safety constraints;
- packet scope coverage;
- design revision consistency.

`validate-admission.py` validates the cross-record boundary:

```text
design.status == approved
design approval binds to current artifact manifest
required design reviews == accepted
packet.design_decision_ref == approved design
packet scope is covered by design scope
packet criteria trace to design criteria
packet gates, dependencies, authorization, lease, and resources pass
```

The validator returns a nonzero status for any missing or ambiguous
condition. It does not infer approval from a tracker edit.

### Factory hooks

The plugin's `PreToolUse` hooks protect the local session:

- `Create`, `Edit`, and `ApplyPatch` are blocked when no claimed packet is
  active.
- Writes outside `scope.in` are blocked.
- Implementation writes are blocked before `Ready` admission.
- Direct edits to canonical state are blocked unless they are made through
  the transition command or an explicitly allowed record operation.
- `Execute` calls that publish, push, deploy, or perform declared external
  effects require the packet's approval policy.

Hooks are advisory only when the host is not running the plugin. CI and the
repository validator remain authoritative for merge and release gates.

### CI

CI runs design validation, admission validation, packet scope validation,
artifact safety checks, tests, clean-plugin packaging checks, and generated
projection checks. A pull request that changes an approved design artifact
without updating its manifest or approval is rejected.

### Host supervisor

The optional host supervisor remains responsible for process-level controls:
worker sessions, worktrees, leases, fencing, CPU/memory/process/token/spend
limits, reviewer capacity, cancellation, and integration sequencing. It
consumes the repository admission result; it does not replace the design
contract or user approval.

## 8. Factory plugin packaging

The repository will expose a marketplace at its root and a nested plugin:

```text
.factory-plugin/
  marketplace.json
plugins/
  contract-engineering-skills/
    .factory-plugin/
      plugin.json
    skills/
    commands/
    droids/
    hooks/
    runtime/
    README.md
```

The root marketplace points to
`./plugins/contract-engineering-skills`. The nested package contains the six
governed skills plus the planning, review, admission, preview, and enforcement
components. The root remains the protocol source, schema source, test suite,
and documentation source.

The clean-install check will:

1. Build or copy the nested plugin into a temporary directory.
2. Verify the manifest, six skill files, commands, droids, hooks, runtime,
   and pinned Mermaid asset.
3. Validate that every plugin-relative path resolves inside the plugin.
4. Install the local marketplace with the Factory CLI when available.
5. Verify plugin discovery and command metadata.
6. Run the plugin's offline validation command.

No test may overwrite a user's existing `~/.factory/skills` or plugin cache.

## 9. Child packet decomposition

The parent packet will be followed by bounded child packets:

1. **Design contract schema and validation**
   - design record schema, template, validator, artifact manifest, and tests.
2. **Visual artifact runtime**
   - preview launcher, static server selection, Mermaid runtime pin,
     SVG sanitization/export, HTML safety checks, and fixtures.
3. **Factory commands and droids**
   - planning, review, admission, preview, and specialized reviewer
     interfaces.
4. **Factory hooks and CI enforcement**
   - pre-tool blocking, packet-scope enforcement, admission checks, and
     workflow integration.
5. **Nested plugin packaging**
   - marketplace manifest, nested plugin contents, clean-install checks, and
     versioning documentation.
6. **Consumer migration and operational documentation**
   - project setup, lock/preflight updates, examples, rollout, rollback,
     and limitations.

Each child packet must identify its parent design contract, have non-overlap
scope, define dependencies, and carry its own structured acceptance contract.
The parent packet coordinates but does not implement child scope.

## 10. Security and failure handling

Design artifacts and issue text are untrusted data. The system must treat
embedded instructions, links, scripts, and generated content as data rather
than authority.

The system quarantines or blocks when:

- a required design review is rejected or missing;
- the artifact manifest does not match the files;
- the renderer is unavailable for a required visual review;
- an SVG contains scripts or external references;
- an HTML artifact requests network or credential access;
- the user approval is missing, stale, or bound to another revision;
- packet scope exceeds the approved design;
- a hook, validator, or cancellation step fails closed;
- a host supervisor reports unknown side effects or stale leases.

Failure evidence records the exact design revision, artifact path, validator
result, and requested recovery action. It must not include credentials,
cookies, raw session tokens, or unnecessary prompt content.

## 11. Validation and rollout

The first implementation phase is dry-run and local-only:

- validate existing records;
- validate a text-only design fixture;
- validate UI/UX HTML fixtures;
- validate architecture Mermaid/SVG fixtures;
- exercise missing-renderer and unsafe-artifact failures;
- run the preview server on localhost;
- validate the nested plugin from a clean checkout.

Rollout proceeds in stages:

1. Install the plugin in project scope with admission in report-only mode.
2. Enable blocking hooks for low-risk file-only packets.
3. Require design contracts for new UI, UX, architecture, workflow, and
   data-flow tasks.
4. Enable CI admission enforcement for all new implementation packets.
5. Enable host-supervisor resource and lease enforcement.
6. Migrate existing consumers through explicit child packets.

Existing legacy packets remain valid under the current protocol until a
consumer migration packet adopts design-contract enforcement. New packets
created after the protocol release must use the design contract when their
design type requires it.

## 12. Success criteria

The implementation is successful when:

- a user can collaboratively produce and approve a design contract;
- the contract captures architecture, alternatives, risks, tradeoffs, and
  measurable acceptance criteria;
- required UI and architecture artifacts can be reviewed offline;
- the preview server is localhost-only and does not install or fetch runtime
  dependencies;
- packet decomposition is blocked until design approval and required reviews;
- packet criteria trace to design criteria and evidence;
- out-of-scope Factory edits are blocked by hooks and rejected by CI;
- the nested plugin installs from a clean marketplace checkout;
- a consuming repository retains ownership of its own records and approvals;
- failure paths are explicit, auditable, and fail closed.
