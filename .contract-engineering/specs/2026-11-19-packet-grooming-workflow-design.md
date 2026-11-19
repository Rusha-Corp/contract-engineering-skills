# Spec: Packet grooming workflow and tm doctor reporting

**Date:** 2026-11-19
**Author:** droid
**Packet:** CENG-T037-P001
**Status:** Pending user approval

## Problem

CE workspaces accumulate three classes of data-quality issues over time:

1. **Broken YAML** in work-packets. The most common causes are unquoted
   colons in list items or mapping values (e.g. `- PR #647 merged: ci:
   path-filter` — the `:` after "merged" is parsed as a YAML mapping key)
   and duplicated mapping keys (e.g. `state: Planned` appearing twice
   because the write-back logic appended a second copy). Broken packets
   cannot be parsed by the ce-sync engine and are silently excluded from
   imports — the user may not realize a packet is missing from Task Master.

2. **Unresolved sidecar refs.** Packets reference governance records
   (decisions, data gates, threat models) via `design_decision_ref`,
   `data_gate_ref`, and `threat_model_ref`. Over time these refs break:
   absolute filesystem paths (`/home/dev/.factory/specs/...`), prose text
   (`Spec 2026-08-28-fix-dev-file-server-stalls (approved)`), wrong-kind
   ids (a data-gate id in `design_decision_ref`), or simply missing files.
   The packet still imports, but its governance links are incomplete.

3. **Unlinked governance records.** Decisions, data gates, and threat
   models that exist on disk but are not referenced by any packet. These
   may be orphaned artifacts from cancelled packets, renamed records, or
   simply forgotten. No data loss occurs, but the workspace accumulates
   clutter that makes it harder to understand governance state.

`tm doctor` currently reports these issues to the console (truncated at
5-10 items per category) but `--fix` only repairs directory structure,
missing lock files, and skill installation. It does nothing about the
packet and ref issues. The user has no actionable output — they see
"6 error(s), 82 unresolved ref(s), 164 unlinked record(s)" but cannot
see the full list without reading the source files themselves.

## Design

### 1. Where grooming fits in the CE lifecycle

Three options were considered:

**Option A — Pre-baseline step.** Before claiming new work, the agent
runs `tm doctor` and resolves all grooming findings. Pro: catches issues
before they block sync. Con: slows down starting work, especially in
workspaces with legacy issues that don't affect the current task. An
agent that just wants to claim a packet shouldn't be blocked by an
unlinked decision from a different task.

**Option B — Dedicated maintenance task.** Grooming is a separate packet
with `work_type: maintenance`. The user or agent claims it like any
other packet, with its own scope, acceptance criteria, and handoff.
Pro: explicit ownership, tracked in the tracker, governed by the state
machine. Con: adds overhead for small fixes; not every workspace needs
a formal grooming packet.

**Option C — Closure gate.** Before a task can be marked complete, all
grooming findings in its packets must be resolved. Pro: ensures clean
state at completion. Con: doesn't catch pre-existing issues from other
tasks; a task shouldn't be blocked by an unrelated broken packet.

**Recommendation: Hybrid (A-passive + B-on-demand).**

- **Passive detection:** `tm doctor` writes a grooming report on every
  run when issues are found — no flags needed. The report is a Markdown
  file at `<ceDir>/grooming-report.md` that lists every finding without
  truncation, with per-error fix hints. The user can feed this file to
  their LLM for manual repair.

- **On-demand maintenance:** When the user decides to groom
  systematically, they claim a maintenance packet (`work_type:
  maintenance`) with the grooming report as a baseline ref. The packet's
  scope.in lists the files to fix, and its acceptance criteria verify
  that `tm doctor` reports zero issues after the fixes.

This approach respects the existing state machine — no new states, gates,
or mandatory steps. The grooming report is always available as passive
detection, and the maintenance packet provides a governed path for
systematic cleanup when the user chooses it.

### 2. Severity taxonomy

| Severity | Category | Description | Impact |
|----------|----------|-------------|--------|
| **Blocker** | Broken YAML | Packet file cannot be parsed by js-yaml | Packet is silently excluded from ce:sync imports; its state, evidence, and governance are all missing from Task Master |
| **Warning** | Unresolved sidecar refs | Packet imports but one or more governance refs (design_decision_ref, data_gate_ref, threat_model_ref) cannot be resolved | Packet syncs with incomplete governance; decisions, data gates, or threat models are missing from the packet's governance tab |
| **Informational** | Unlinked records | Governance record exists on disk but is not referenced by any packet | No data loss; record may be orphaned from a cancelled packet or a rename; clutters the workspace |

The severity determines the recommended action:
- **Blocker:** Fix immediately — the packet is invisible to Task Master.
- **Warning:** Fix before the packet's handoff — governance must be complete at handoff.
- **Informational:** Review at task closure or during a maintenance packet — link or remove.

### 3. Grooming report format

The report is a Markdown file written to `<ceDir>/grooming-report.md`
on every `tm doctor` run that finds issues. Structure:

```markdown
# CE Packet Grooming Report
Generated: 2026-11-19T12:00:00Z
Workspace: /home/dev/hermes

## Summary
- 6 broken packet(s) (YAML parse errors)
- 82 unresolved sidecar ref(s)
- 164 unlinked record(s)

## Broken packets (6)

### HERMES-CI-T016-P013.yaml
**Error:** bad indentation of a mapping entry (124:31)
**Fix:** Unquoted colon in a list item. The ":" in the value is parsed
as a YAML mapping key.
Quote the list item value:
  - "Direct push to main: fix(ci): remove dangling quality job d ..."

### HERMES-MCP-T001-P001.yaml
**Error:** duplicated mapping key (147:1)
**Fix:** Key "risk_tier" appears 2 times in the document (error at line
147). Remove the earlier occurrence(s) — keep the last one, which is
the authoritative write-back value.

... (one section per broken packet, no truncation)

## Unresolved sidecar refs (82)

### [absolute-path] (6)
These refs point at absolute filesystem paths outside
.contract-engineering/. Move the file under
.contract-engineering/decisions/ and update the ref, or remove it.

- **HERMES-CI-T016-P013** → design_decision_ref: `/home/dev/.factory/specs/2026-10-12-...`
- ...

### [missing-file] (7)
...

### [prose] (10)
...

### [wrong-kind-id] (58)
...

### [unreadable] (1)
...

## Unlinked records (164)

These governance records are not referenced by any packet. Link them
via the appropriate ref field, or remove if obsolete.

### decisions (89)
- `.contract-engineering/decisions/CALI-T001-P005-service-contract.md`
- ...

### data-gates (42)
- ...

### threat-models (33)
- ...
```

Key properties:
- **No truncation.** Every finding is listed, unlike the console output
  which caps at 5-10 items.
- **Per-error fix hints.** For YAML errors, the report extracts the line
  number from the error message, reads the offending line, and generates
  a specific fix (quote the value, remove the duplicate key).
- **Grouped by category.** Broken packets first (most severe), then
  unresolved refs by category, then unlinked records by subdirectory.
- **Advisory only.** The report does not modify any files. The user
  reviews and applies fixes manually or via their LLM.

### 4. Trigger model

| Trigger | What happens | When |
|---------|-------------|------|
| `tm doctor` (no flags) | Writes grooming report if issues found | Every run |
| `tm doctor --fix` | Repairs dirs/lock/skills AND writes grooming report | When user runs --fix |
| `tm doctor --update` | Updates lock/skills AND writes grooming report | When user runs --update |
| `ce:sync --dry-run` | Reports unresolved refs and unlinked records (existing) | Pre-sync preview |

The grooming report is always written when issues are found — it is not
gated behind `--fix`. The console output remains as-is (truncated for
quick glance), and the report file provides the complete picture.

`--fix` does NOT auto-fix YAML or refs. The previous design considered
auto-fixing YAML (quoting values, removing duplicates) but this was
superseded by the report-only approach: the user feeds the report to
their LLM, which can handle nuanced fixes (e.g. distinguishing a
prose ref that should be a DEC id from one that should be removed)
better than a mechanical auto-fixer.

### 5. Integration with ce:sync

`ce:sync --dry-run` already reports unresolved refs and unlinked records
as part of its pre-sync preview. The grooming report is complementary:

- `ce:sync --dry-run` is a pre-sync check: "what will import, what
  won't, and why." It's run before syncing to preview the import.
- `tm doctor` is a health check: "what's broken in this workspace,
  regardless of whether you're about to sync." The grooming report is
  the complete untruncated view of all findings.

Both use the same underlying engine (`buildTaskPayloads` in ce-sync.mjs),
so their findings are consistent. The grooming report adds per-error fix
hints that ce:sync --dry-run does not provide.

### 6. Maintenance packet pattern

When the user decides to groom systematically, they create a maintenance
packet:

```yaml
packet_id: PROJECT-TXXX-P001
task_id: PROJECT-TXXX
work_type: maintenance
title: "Groom CE workspace — fix broken packets and unresolved refs"
scope:
  in:
  - .contract-engineering/work-packets/BROKEN-PACKET.yaml
  - .contract-engineering/decisions/ORPHAN-DEC001.yaml
  out:
  - Any files not listed in the grooming report
acceptance_criteria:
  - "tm doctor reports zero broken packets"
  - "tm doctor reports zero unresolved refs"
  - "All unlinked records are linked or removed"
evidence_refs:
  - PROJECT-TXXX-P001-EV001  # tm doctor output showing zero issues
```

The grooming report serves as the baseline ref for the maintenance
packet. The packet is claimed, executed, and handed off like any other,
with the user accepting the handoff after verifying `tm doctor` is clean.
