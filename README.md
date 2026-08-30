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
- `templates/` contains portable work-packet, deprecation, feedback, and
  validation records.
- `adapters/` explains host-specific installation and execution integration.

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

For a new or empty Droid Skill directory:

```bash
mkdir -p ~/.factory
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  ~/.factory/skills
```

This works because each protocol directory is at the repository root and
contains its own `SKILL.md`.

If `~/.factory/skills` already contains other Droid Skills, do not clone over
it. Clone separately, review the release, back up the target directory, and
copy only the five protocol directories:

```bash
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  ~/contract-engineering-skills || {
  echo "Failed to clone contract-engineering-skills" >&2
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

Use `templates/validation-guide.md` for non-destructive checks. This
repository intentionally does not ship an automatic deletion or mutation
tool.
