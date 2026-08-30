# Runtime Budgets and Emergency Stops

Packet scope limits what an agent may change. Runtime budgets limit how much
work it may perform while doing so. Autonomous and tool-using agents must
have both.

## Required budget

Use `templates/execution-budget.yaml` for any packet that can run tools,
network requests, subprocesses, long-running loops, or external effects.
Zero means the operation is not allowed, not unlimited. An explicitly
unbounded value is prohibited.

Specify:

- maximum duration, tool calls, retries, spend, file writes, and processes;
- allowed write paths and network targets;
- destructive-action policy;
- timeout and cancellation action;
- checkpoint used for resume;
- emergency-stop authority and recovery approval.

The host should enforce budgets before starting an operation and after every
tool call or side effect. A preflight-only host must record that enforcement
is unavailable and block operations that require the missing control.

## Approval and exhaustion

Budget approval is separate from action approval. Staying below a budget does
not authorize an unlisted action, and user approval for one operation does
not increase a budget silently.

On exhaustion:

1. Stop starting new work.
2. Preserve the last checkpoint and operation identifiers.
3. Record the exhausted limit and observed usage.
4. Leave the packet in `Validation`, `Rework`, `Interrupted`, or `Handoff`
   according to the actual state; never claim completion automatically.
5. Request an explicit budget change or continue with the remaining approved
   scope.

Retries count toward tool-call, duration, and cost limits. Backoff must be
bounded. A retry of a side-effecting operation requires idempotency or a
compensation plan.

## Cancellation and quarantine

Cancellation is a normal control, not an exception. The host must stop new
tool calls, attempt to terminate child processes, preserve evidence, and
record whether termination succeeded. If termination cannot be verified,
quarantine the worktree, credentials, and external connectors before recovery.

Quarantine prevents further writes and external effects while preserving the
state needed for investigation. Recovery requires a new session, revalidated
identity/capabilities, a current checkpoint, and approval for any pending
side effect.

## Emergency stop

An emergency stop may be triggered by the user, designated incident
commander, or an automated safety control named in the packet. It must:

1. Stop or isolate the agent and child agents.
2. Revoke or disable pending external effects and credentials when required.
3. Preserve redacted logs, operation IDs, and the last known state.
4. Open or link an incident for security, data, or production-impacting
   events.
5. Require explicit recovery approval before resuming.

The emergency stop procedure must be tested in a bounded environment. A
button or command that stops the model but leaves a child process or external
operation active is not a complete stop.

## Optional runtime controls

File-only documentation work may use the minimum budget needed for local
validation. Runtime-specific limits, quarantine, and emergency-stop controls
are mandatory when the packet uses autonomous loops, tools with side effects,
production-like data, network writes, or delegated agents.
