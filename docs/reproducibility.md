# Reproducible Agent Runs

Agent output depends on more than source code. Model/provider versions,
policies, prompts, tools, configuration, dependencies, external data, and
time can change the result. Use `templates/agent-run.yaml` for runs that
affect implementation, validation, decisions, or externally consumed output.

## Record without leaking content

Record stable identifiers and hashes for:

- actor, harness, session, and packet;
- model provider, model name/version, endpoint, and relevant settings;
- system policy and prompt-template references and hashes;
- tools, adapters, MCP servers, schemas, capabilities, and versions;
- repository revision, runtime, configuration, and dependency versions;
- external data or fixture snapshots;
- start/end time, outcome, evidence, and limitations.

Do not copy secrets, private prompts, customer records, or raw model
responses by default. Reference sanitized evidence by ID or hash and apply
the evidence security policy before storing any content.

## Reproduction levels

State which level is possible:

1. **Exact:** same model/provider build, prompt/policy, tools, inputs,
   configuration, seed, and environment.
2. **Replayable:** same recorded inputs and tool interactions can be replayed,
   but model nondeterminism or external state may differ.
3. **Auditable:** the run can be explained and independently assessed from
   recorded metadata, evidence, and limitations, but not replayed exactly.

Never claim exact reproduction when only an audit record exists.

## Change triggers

Create a new run record when the model, provider, prompt, policy, tool,
adapter, dependency, repository revision, configuration, fixture, or external
data snapshot changes. Link the new run to the prior record and explain
material differences.

Unknown or missing metadata is a limitation. It blocks high-risk claims and
must be dispositioned before handoff. A reproducibility record supports
evaluation and incident response; it does not replace either one.
