# Factory Droid Adapter

The portable protocols in this repository can be installed as Factory Droid
Skills. The host-specific integration is:

- Shared Skill files are discovered from `~/.factory/skills/<name>/SKILL.md`.
- Factory spec approval is the front gate for writes.
- The approved spec is linked from the packet's `baseline_refs` and
  `design_decision_ref`.
- Project execution records remain in the consuming project's
  `.factory/execution-tracker.md` and `.factory/work-packets/`.

## Fresh installation

If the target directory does not exist or is empty:

```bash
mkdir -p ~/.factory
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  ~/.factory/skills
```

## Existing installation

Do not clone the repository directly over an existing directory containing
other Droid Skills. Instead:

```bash
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  ~/contract-engineering-skills
for skill in phased-engineering-execution cleanup-protocol project-lifecycle skill-evolution coding-principles; do
  test ! -e "$HOME/.factory/skills/$skill" || {
    echo "Refusing to overwrite existing $skill" >&2
    exit 1
  }
  cp -R "$HOME/contract-engineering-skills/$skill" "$HOME/.factory/skills/"
done
```

Back up the current directories first and review the release tag. Do not
delete or overwrite unreviewed local modifications.
