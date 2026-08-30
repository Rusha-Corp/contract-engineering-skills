# Factory Droid Adapter

The portable protocols in this repository can be installed as Factory Droid
Skills. The host-specific integration is:
- Project protocol configuration is committed to
  `.contract-engineering/protocol.lock.yaml`.
- Project trackers, packets, evidence, handoffs, and feedback are relative
  to the lock's `project.protocol_root`, not the global skill directory.

- Shared Skill files are discovered from `~/.factory/skills/<name>/SKILL.md`.
- Factory spec approval is the front gate for writes.
- Read `docs/protocol-configuration.md` for the shared preflight and update
  contract. This adapter only supplies the Factory global skill path and
  approval behavior.
- Project execution records remain in the consuming project's
  `.factory/execution-tracker.md` and `.factory/work-packets/`.

## Fresh installation

If the target directory does not exist or is empty:

```bash
mkdir -p ~/.factory
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  ~/.factory/skills || {
  echo "Failed to clone contract-engineering-skills" >&2
  exit 1
}
git -C ~/.factory/skills checkout --detach \
  bcc2adb73475af10c5aa92bd27471a5e31e0f514 || {
  echo "Failed to select the locked protocol revision" >&2
  exit 1
}
```

The commit above is the published v2.0.0 example. Replace it with the
immutable `protocol.ref` selected in the consuming project's lock file.

## Existing installation

Do not clone the repository directly over an existing directory containing
other Droid Skills. Instead:

```bash
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  ~/contract-engineering-skills || {
  echo "Failed to clone contract-engineering-skills" >&2
  exit 1
}
git -C "$HOME/contract-engineering-skills" checkout --detach \
  bcc2adb73475af10c5aa92bd27471a5e31e0f514 || {
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

Back up the current directories first and review the release tag. Do not
delete or overwrite unreviewed local modifications.

## Preflight and updates

Set `SKILLS_DIR="$HOME/.factory/skills"` and run the preflight from
`docs/protocol-configuration.md` before claiming work. On protocol updates,
update the project's lock first, install every governed skill from the same
immutable ref, and rerun preflight. If a hash or version mismatches, stop and
restore or reinstall the locked revision instead of editing a skill manually.
