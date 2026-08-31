# Hermes Agent Adapter

The portable protocols in this repository can be installed as Hermes Agent
skills. Hermes (by Nous Research) is compatible with the
[agentskills.io](https://agentskills.io/specification) open standard and
discovers skills from `~/.hermes/skills/` or project-local
`.agents/skills/` directories.

## Installation

### Option 1: Install individual skills from GitHub

Hermes can install skills directly from a public GitHub repo:

```bash
hermes skills install Rusha-Corp/contract-engineering-skills/skills/phased-engineering-execution
hermes skills install Rusha-Corp/contract-engineering-skills/skills/cleanup-protocol
hermes skills install Rusha-Corp/contract-engineering-skills/skills/coding-principles
hermes skills install Rusha-Corp/contract-engineering-skills/skills/project-lifecycle
hermes skills install Rusha-Corp/contract-engineering-skills/skills/skill-evolution
hermes skills install Rusha-Corp/contract-engineering-skills/skills/security-assurance
```

### Option 2: Add as a tap and install all skills

Register this repository as a skills tap, then install from it:

```bash
hermes skills tap add Rusha-Corp/contract-engineering-skills
hermes skills install Rusha-Corp/contract-engineering-skills/skills/phased-engineering-execution
# repeat for each skill
```

### Option 3: External skill directory (shared with other agent tools)

Clone the repository to a shared location and point Hermes at it:

```bash
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  ~/contract-engineering-skills
git -C ~/contract-engineering-skills checkout --detach \
  <protocol-ref-from-your-lock>
```

Add the `skills/` directory to Hermes's external skill dirs in
`~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/contract-engineering-skills/skills
```

All six skills will appear in Hermes's skill index, `skills_list`, and as
`/skill-name` slash commands. Hermes scans external skills with its
security scanner before loading them.

### Option 4: Project-local skills

Copy the skill directories into your project's `.agents/skills/` directory:

```bash
git clone https://github.com/Rusha-Corp/contract-engineering-skills.git \
  ~/contract-engineering-skills
git -C ~/contract-engineering-skills checkout --detach \
  <protocol-ref-from-your-lock>
for skill in phased-engineering-execution cleanup-protocol coding-principles \
             project-lifecycle skill-evolution security-assurance; do
  cp -R ~/contract-engineering-skills/skills/$skill \
    .agents/skills/$skill
done
hermes skills trust
```

Project skills are the highest-precedence tier and override same-named bundled
or profile skills for sessions inside that repo.

## Skill frontmatter

Each `SKILL.md` includes `name`, `description`, `version`, `license: MIT`,
and `compatibility` frontmatter compatible with both the agentskills.io
specification and Hermes's skill format.

## Project protocol configuration

Protocol configuration is committed to `.contract-engineering/protocol.lock.yaml`
in the consuming project. This is separate from the Hermes skill directory.
Project trackers, packets, evidence, handoffs, and feedback are relative to
the lock's `project.protocol_root`, not the Hermes skills directory.

Copy or adapt `templates/AGENTS.md` as the consuming repository's `AGENTS.md`
or project-instruction file. For Hermes, project skills in `.agents/skills/`
serve the same role as the global skill installation.

## Preflight

Set `SKILLS_DIR` to the Hermes skills directory (or the external dir) and run
the preflight from `docs/protocol-configuration.md` before claiming work:

```bash
SKILLS_DIR="$HOME/.hermes/skills" \
  python3 - <<'PY'
# preflight script from docs/protocol-configuration.md
PY
```

If using an external dir, set `SKILLS_DIR` to that path instead.

## Security

Route the security gate from packet domain, risk, declared effects,
capabilities, and classified sensitive scope, never from a task identifier.
Hermes must block an action when a required native capability or approval is
unavailable and retain a limitation or incident reference in the packet.

Hermes scans all installed skills (including external and project-local
skills) with its built-in security scanner before loading them. Skills
are quarantined if the scan verdict is "dangerous." Trust project-local
skills with `hermes skills trust` before they appear in the skill index.

Record Hermes adapter identity, tool capabilities, and endpoint allowlists
in the project's adapter inventory using `templates/adapter-inventory.yaml`.
Treat Hermes tool output and agent messages as untrusted data per
`docs/agent-trust-boundaries.md`.
