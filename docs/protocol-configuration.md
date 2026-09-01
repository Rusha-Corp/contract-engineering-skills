# Protocol Configuration

This guide keeps the Contract-Driven Engineering protocols consistent across
Factory Droid, IDE agents, CLI agents, CI, and other AI-assisted development
environments.

## Three layers

Use three separate layers:

1. **Canonical source:** this repository, selected by an immutable commit.
2. **Global skill installation:** the host's skill directory, such as
   `~/.factory/skills` for Factory Droid.
3. **Project configuration and records:** the consuming repository's committed
   `.contract-engineering/` directory.

Global installations provide instructions. They do not own project decisions,
packet state, evidence, or version selection.

## Project files

Create these files in every consuming project:

```text
.contract-engineering/
  protocol.lock.yaml
  execution-tracker.md
  work-packets/
  archive/
    execution-tracker-archive.md
    work-packets/
  evidence/
  handoffs/
  skill-feedback.md
```

The protocol root is project-relative and defaults to `.contract-engineering`.
If an existing project already stores records under `.factory`, set
`project.protocol_root: .factory` in its lock file while migrating. Do not
move or delete existing records automatically.

The active tracker is intentionally bounded: it contains live and
not-yet-closed packets. During cleanup or iteration closure, move terminal
packet YAML files from `work-packets/` to `archive/work-packets/`, and move
their rows from `execution-tracker.md` to the append-only
`archive/execution-tracker-archive.md`. Rows must be moved, not copied. The
archive ledger preserves history while keeping the active tracker small.

The rollover is a harness-native procedure. The harness should use its native
file and YAML tooling to identify terminal packets, move the packet files and
rows, and verify that each packet exists in exactly one partition, each
partition has the correct tracker row, and archived packets are terminal.
No Python runtime or repository archive command is required.

### Bounded tracker and packet maintenance

The active tracker is an index, not a permanent history log:

- Keep at most 25 packet rows in `execution-tracker.md`.
- When the index reaches 26 rows, move complete task rows into
  `tracker-shards/<TASK-ID>.md` and keep one task's rows in one shard.
- Keep at most 50 packet rows in a task shard. Split a large task into child
  tasks and shards instead of growing the shard indefinitely.
- Shards are active-only views. They use the same table schema and remain
  subject to the one-row/one-packet invariant. A packet row must appear in
  exactly one of the active index, one active shard, or the archive ledger.
- At user confirmation or iteration closure, move terminal packet YAML and
  its row from the active index or shard into `archive/work-packets/` and
  `archive/execution-tracker-archive.md`. Move, do not copy, and retain the
  handoff and evidence references.

To prevent stale active work, review every `Claimed`, `Implementing`,
`Validation`, and `Handoff` packet at least every 14 days. The owner must
resume it, record an `Interrupted` recovery path, cancel it, or complete the
handoff. Do not invent a `Stale` state and do not archive active work. A
failed rollover restores the source files and leaves the packet active.
Validation enforces shard ownership, row uniqueness, archive partitioning, and
the row limits; the review cadence remains an owner/reviewer responsibility.

### Repository-level agent instructions

The project lock and records are the source of truth; a repository-level
instruction file is only the host integration entry point. If the harness
loads `AGENTS.md`, copy [`templates/AGENTS.md`](../templates/AGENTS.md) to the
consumer repository root and adapt only host-specific paths or commands. If
the harness uses another project-instruction mechanism, adapt the same
template to that mechanism, such as `CLAUDE.md` or `.cursorrules`.

The adapted file SHOULD require agents to read the lock, run preflight with
the harness's actual global skill directory, read the tracker and applicable
skills, claim a packet before editing, honor packet scope and locks, and
complete validation and handoff. Keep the file concise and link to this
guide and the configured `project.protocol_root`; do not copy the full
protocol skills into the repository instruction file. The file belongs in
the consuming repository, not in the global skill directory.

Create the lock from the repository template:

```bash
mkdir -p .contract-engineering
cp templates/protocol-lock.yaml \
  .contract-engineering/protocol.lock.yaml
```

Review every value before committing it. The lock file is the project's
authority for protocol selection.

## Lock file contract

`protocol.lock.yaml` contains:

- `lock_version`: lock schema version;
- `protocol.repository`: canonical repository URL;
- `protocol.ref`: immutable commit SHA, not a floating branch;
- `protocol.release`: human-readable release associated with the commit;
- `skills.<name>.version`: front-matter version for each governed skill;
- `skills.<name>.sha256`: hash of the installed `SKILL.md`;
- `project.protocol_root`: project-relative directory for shared records.

The lock must list all six governed skills. The release field is descriptive;
the immutable `ref` and per-file hashes are the integrity controls. When
using a tag, resolve it to a commit and record that commit in `ref`.

## Initial installation

Choose a checkout directory outside the host's skill directory:

```bash
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  "$HOME/contract-engineering-skills"
git -C "$HOME/contract-engineering-skills" checkout --detach \
  575f473a9349c5dfb61df7758b52a5592b2e2915
```

Use the `protocol.ref` from the project's lock file instead of the example
commit above. Then follow the host adapter's instructions to copy the five
`SKILL.md` files into its global skill directory. Never overwrite an existing
skill until its local differences have been reviewed or backed up.

## Preflight before work

Every harness should perform this preflight before claiming a packet:

1. Read the project's lock file.
2. Confirm the local protocol checkout is at `protocol.ref`, when a checkout
   is used.
3. Confirm each installed governed skill exists.
4. Compare each installed file's SHA-256 hash with the lock.
5. Compare each installed front-matter `version` with the lock.
6. Stop and synchronize if any check fails.

Projects SHOULD also run `scripts/validate-contract-records.py` when this
repository is available as a checkout. That validator checks packet schemas,
identifiers, dependencies, references, tracker reconciliation, active-lock
collisions, and optional changed-path scope. A packet with invalid records or
an out-of-scope change must not advance to validation or handoff.

The following check uses Python and PyYAML. A harness may implement the same
checks with its native YAML parser:

```bash
SKILLS_DIR="$HOME/.factory/skills" \
  python3 - ".contract-engineering/protocol.lock.yaml" <<'PY'
import hashlib
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required for this preflight")

lock_path = Path(sys.argv[1])
lock = yaml.safe_load(lock_path.read_text())
skills_dir = Path(os.environ["SKILLS_DIR"]).expanduser()
skills = lock["skills"]
required = {
    "phased-engineering-execution",
    "cleanup-protocol",
    "project-lifecycle",
    "skill-evolution",
    "coding-principles",
    "security-assurance",
}
if set(skills) != required:
    raise SystemExit(f"lock must contain exactly six governed skills: {sorted(skills)}")

for name, pin in skills.items():
    skill_file = skills_dir / name / "SKILL.md"
    if not skill_file.is_file():
        raise SystemExit(f"missing installed skill: {skill_file}")
    actual_hash = hashlib.sha256(skill_file.read_bytes()).hexdigest()
    if actual_hash != pin["sha256"]:
        raise SystemExit(f"hash mismatch: {name}")
    match = re.search(r"^version:\s*(\S+)\s*$", skill_file.read_text(), re.MULTILINE)
    if not match or match.group(1) != str(pin["version"]):
        raise SystemExit(f"version mismatch: {name}")

print("protocol preflight passed")
PY
```

For another harness, change only `SKILLS_DIR`. Do not change the lock to
match a stale installation. Update the installation from the locked source,
then rerun preflight.

Security controls are selected from packet metadata, not task identifiers.
Packets in the security domain, high or critical packets, packets with
external effects or sensitive capabilities, and classified packets touching
sensitive scope must include actor identity, capabilities, risk and approval
policy, declared effects, and applicable trust, budget, checkpoint, evaluation,
run, observability, and incident references. Completed legacy packets may be
migrated under a separately scoped packet; they are not a precedent for new
work.

## Updating protocols

Protocol updates are coordinated, not discovered independently by each tool:

1. Review the protocol repository release notes.
2. Update the project's `protocol.lock.yaml` to the new immutable ref,
   release, skill versions, and SHA-256 values.
3. Review migration notes and any changed schemas or lifecycle states.
4. Update each harness's global skill installation from that same ref.
5. Run preflight in every harness.
6. Record the lock path and ref in each packet's `baseline_refs`.

Do not update one harness to a newer protocol while another continues work
against an older contract under the same project lock.

For organizations with multiple consuming projects, maintain a consumer
record from `templates/protocol-consumer.yaml` and follow
`docs/protocol-fleet.md`. Breaking lock-schema, state-machine, or safeguard
changes require an impact assessment and migration packet before rollout.

## Rollback and drift recovery

To roll back, restore the previous lock file and reinstall the exact previous
ref into each harness. Keep the previous skill installation or a verified
backup until the new installation passes preflight.

If a hash, version, or source ref differs:

1. Stop new packet work in that environment.
2. Preserve the current installation for comparison.
3. Reinstall from the lock's immutable ref, or restore the verified backup.
4. Rerun preflight.
5. Record the drift and recovery in the project evidence or handoff.

Never solve drift by editing an installed `SKILL.md` manually.

## Multi-harness coordination

All harnesses use the same project-local:

- `protocol.lock.yaml`;
- execution tracker;
- work packets and ownership locks;
- evidence and handoffs;
- skill feedback log.

The host adapter supplies only the global skill path and approval mechanics.
It must not create a second project lock or private tracker. Chat history and
private AI sessions are not sources of truth.
