# Contract-Driven Engineering

<img src="assets/contract-spark/contract-spark-lockup.svg" alt="Contract Spark, the Contract-Driven Engineering protocol identity" width="280">

**Contract-Driven Engineering** is a tool-agnostic protocol for making
AI-assisted software development safe, accountable, and auditable. It turns
every piece of work into a bounded *packet* with an owner, a scope, explicit
gates, reproducible evidence, and an independent handoff that a reviewer must
accept before the work is considered done.

This repository supplies everything you need to adopt the protocol:

| What | Where | Purpose |
| --- | --- | --- |
| Governed skills | `skills/` | Six `SKILL.md` files covering phased execution, coding principles, security assurance, cleanup, skill evolution, and project lifecycle. |
| Templates | `templates/` | Work-packet, deprecation, feedback, validation, and consumer `AGENTS.md` templates. |
| Host adapters | `adapters/` | Installation and integration guides for Factory Droid, Hermes Agent, and generic harnesses. |
| Reference docs | `docs/` | Release integrity, protocol configuration, secret management, incident response, and more. |
| Tracker storage | `.contract-engineering/tracker/`, `scripts/` | Canonical YAML tracker partitions, bounded task shards, event history, and generated Markdown projections. |
| Visual identity | `assets/contract-spark/` | Contract Spark SVG mark, lockup, and badge for documentation and branding. |
| CI workflows | `.github/workflows/` | Protocol validation, secret scanning, and security checks with pinned actions. |

It is designed for **human engineers, coding assistants, CI automation, and
agentic development environments**. The core protocols do not depend on a
particular vendor, editor, CLI, or model — any team or agent harness can
adopt them by pinning an immutable release in a project-local lock file.

## Contents

- `skills/` contains the six governed `SKILL.md` files.
- `docs/` contains deprecation, removal, and process guidance.
- `templates/` contains portable work-packet, deprecation, feedback,
  validation, and consumer repository-instruction templates.
- `adapters/` explains host-specific installation and execution integration
  for Factory Droid, Hermes Agent, and generic harnesses.
- `assets/contract-spark/` contains the Contract Spark visual identity (SVG
  mark, lockup, and badge). See the [visual identity guide](docs/visual-identity.md).
- `.contract-engineering/tracker/` contains the canonical YAML tracker index,
  task shards, event history, and archive projection. Read
  [`docs/tracker-storage.md`](docs/tracker-storage.md) for the bounded storage
  contract and database-backed consumer model.
- `.factory-plugin/plugin.json` is the Factory Droid plugin manifest.
- `LICENSE` is the MIT license.

## Protocol configuration

Global skill installations are host-specific. For example, Factory Droid
discovers shared skills from `~/.factory/skills`, while another harness may
use a different user-level directory. Project configuration is portable and
belongs in the consuming repository:

```text
.contract-engineering/protocol.lock.yaml
```

The lock selects one immutable protocol release and records every governed
skill's version and SHA-256 hash. Project trackers, packets, evidence,
handoffs, and feedback are stored relative to the configured protocol root.
Read [the protocol configuration guide](docs/protocol-configuration.md) for
setup, preflight, updates, rollback, and multi-harness coordination.
For the repository-level bootstrap that connects those records to an agent
harness, copy or adapt [`templates/AGENTS.md`](templates/AGENTS.md) as the
consumer's `AGENTS.md` or equivalent project-instruction file.

## Core loop

```text
Baseline
→ Design/Data Gates
→ Implement
→ Validate
→ Deprecation Review
→ Cleanup
→ Practice Review
→ User Verification
→ Closure
```

The protocols separate hard safety, authorization, data-correctness, and
traceability invariants from procedures. Procedures may be tested and revised
through bounded practice experiments.

## Droid installation

This repository includes a `.factory-plugin/plugin.json` manifest and can be
installed as a Factory Droid plugin:

```bash
droid plugin marketplace add https://github.com/Rusha-Corp/contract-engineering-skills
droid plugin install contract-engineering-skills@contract-engineering-skills --scope user
```

Alternatively, for a new or empty Droid Skill directory, first create a
project lock using the
[protocol configuration guide](docs/protocol-configuration.md), then use its
immutable `protocol.ref`:

```bash
mkdir -p ~/.factory
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  ~/.factory/skills || {
  echo "Failed to clone contract-engineering-skills" >&2
  exit 1
}
git -C ~/.factory/skills checkout --detach \
  575f473a9349c5dfb61df7758b52a5592b2e2915 || {
  echo "Failed to select the locked protocol revision" >&2
  exit 1
}
```

Replace the example commit with the value from the consuming project's
`protocol.lock.yaml`. This works because each protocol skill directory is
under `skills/` and contains its own `SKILL.md`.

If `~/.factory/skills` already contains other Droid Skills, do not clone over
it. Clone separately, review the release, back up the target directory, and
copy only the six protocol skill directories:

```bash
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  ~/contract-engineering-skills || {
  echo "Failed to clone contract-engineering-skills" >&2
  exit 1
}
git -C "$HOME/contract-engineering-skills" checkout --detach \
  575f473a9349c5dfb61df7758b52a5592b2e2915 || {
  echo "Failed to select the locked protocol revision" >&2
  exit 1
}
for skill in phased-engineering-execution cleanup-protocol project-lifecycle skill-evolution coding-principles security-assurance; do
  test ! -e "$HOME/.factory/skills/$skill" || {
    echo "Refusing to overwrite existing $skill" >&2
    exit 1
  }
  cp -R "$HOME/contract-engineering-skills/skills/$skill" "$HOME/.factory/skills/" || {
    echo "Failed to install $skill" >&2
    exit 1
  }
done
```

Back up and compare existing directories before deliberately replacing them.
Do not use recursive deletion or overwrite unreviewed local files. Use a
versioned release when updating an existing installation.
Factory-specific approval behavior is documented in
`adapters/factory-droid/README.md`.

## Other agentic development environments

Read the root `SKILL.md` files through the host's instruction or project
guidance mechanism. Use the templates to create project-local packets,
deprecation records, evidence, exceptions, and closure records. See
`adapters/generic/README.md`.

For Hermes Agent (Nous Research), skills are compatible with the
[agentskills.io](https://agentskills.io/specification) open standard and can
be installed via `hermes skills install` or external skill directories. See
`adapters/hermes/README.md`.

The project-specific execution ledger belongs to the consuming project. This
repository supplies the general protocol; it does not own project decisions,
runtime evidence, or consumer migration records.

## Updating and rollback

Prefer tagged releases. Review the release notes, copy the six protocol
skill directories into the host's configured instruction location, and retain
the previous version until validation succeeds. Roll back by restoring the
prior version from the backup or checked-out tag.

## Visual identity

The protocol's visual identity is **Contract Spark**: four interlinked
contract loops forming a spark with a check mark at its center. The loops
represent the iterative contract cycle; the spark represents the energy of
agreement; the check mark represents verified acceptance.

Three self-contained SVG assets are available in `assets/contract-spark/`:

- `contract-spark-mark.svg` — compact mark for favicons and small surfaces.
- `contract-spark-lockup.svg` — mark plus wordmark for documentation headers.
- `contract-spark-badge.svg` — rounded badge for repository and release surfaces.

All assets are script-free, font-free, and accessible. Read the
[visual identity guide](docs/visual-identity.md) for the palette, accessibility,
reuse rules, and size guidance.

## Validation

Use `templates/validation-guide.md` for non-destructive checks and
`docs/protocol-configuration.md` for cross-harness preflight. This repository
intentionally does not ship an automatic deletion or mutation tool.
