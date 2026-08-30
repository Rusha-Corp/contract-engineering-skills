# Contract-Driven Engineering

Tool-agnostic protocols and templates for AI-assisted software development:
phased delivery, deprecation, dead-code removal, evidence, and continuous
process improvement.

This repository is usable by human engineers, coding assistants, CI
automation, and agentic development environments. The core protocols do not
depend on a particular vendor, editor, CLI, or model.

## Contents

- Root protocol directories contain the five governed `SKILL.md` files.
- `docs/` contains deprecation, removal, and process guidance.
- `templates/` contains portable work-packet, deprecation, feedback,
  validation, semantic-contract, and consumer repository-instruction
  templates.
- `adapters/` explains host-specific installation and execution integration.

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

They also treat semantics as a first-class concern. Work packets declare
whether system meaning is unaffected, affected, or being defined. Semantic
work links a versioned contract covering vocabulary, invariants, boundaries,
failure behavior, compatibility, examples, and open questions. Contracts may
begin fuzzy and become more structured through evidence and review; the
protocol records that evolution instead of forcing false precision.

Read [Semantic Engineering](docs/semantics.md) for the workflow and profiles.

## Droid installation

For a new or empty Droid Skill directory, first create a project lock using
the [protocol configuration guide](docs/protocol-configuration.md), then use
its immutable `protocol.ref`:

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
`protocol.lock.yaml`. This works because each protocol directory is at the
repository root and contains its own `SKILL.md`.

If `~/.factory/skills` already contains other Droid Skills, do not clone over
it. Clone separately, review the release, back up the target directory, and
copy only the five protocol directories:

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
for skill in phased-engineering-execution cleanup-protocol project-lifecycle skill-evolution coding-principles; do
  test ! -e "$HOME/.factory/skills/$skill" || {
    echo "Refusing to overwrite existing $skill" >&2
    exit 1
  }
  cp -R "$HOME/contract-engineering-skills/$skill" "$HOME/.factory/skills/" || {
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

The project-specific execution ledger belongs to the consuming project. This
repository supplies the general protocol; it does not own project decisions,
runtime evidence, or consumer migration records.

## Updating and rollback

Prefer tagged releases. Review the release notes, copy the five protocol
directories into the host's configured instruction location, and retain the
previous version until validation succeeds. Roll back by restoring the prior
version from the backup or checked-out tag.

## Validation

Use `templates/validation-guide.md` for non-destructive checks and
`docs/protocol-configuration.md` for cross-harness preflight. This repository
intentionally does not ship an automatic deletion or mutation tool.
