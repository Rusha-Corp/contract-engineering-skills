# Durable Execution and Idempotency

An interrupted agent may have completed some work, lost its response, or
started an external effect whose result is unknown. A prose handoff is not
enough to distinguish those cases. Side-effecting or long-running packets use
the checkpoint contract in `templates/execution-checkpoint.yaml`.

## Operation identity

Every execution attempt has a stable `run_id`. Every meaningful operation has
an `operation_id` and sequence number. Retries reference the original
operation rather than creating an untraceable duplicate. The operation
identity is recorded before the effect starts.

Use an idempotency key whenever the target supports it. If the target does
not support idempotency, record a read-before-write check or a compensating
action. Never blindly retry an operation whose prior result is `unknown`.

## Checkpoint rules

Record a checkpoint:

1. Before starting a side effect.
2. After each completed step or durable file group.
3. Before waiting for approval or external input.
4. After success, failure, cancellation, timeout, or quarantine.

The checkpoint includes the packet base revision, scope digest, completed and
pending steps, side-effect statuses, retry attempt, and recovery action.
Sensitive payloads are referenced or redacted under the evidence policy.

## Retry and replay

Retries are permitted only when the failure class is retryable and the
operation budget allows another attempt. Backoff and total attempts are
bounded. A replay must verify:

- the same packet and approved scope;
- the current actor and capabilities;
- the base revision and checkpoint integrity;
- the prior side-effect status;
- the current approval and runtime budget.

If any check fails, pause for review. A successful operation must not be
replayed merely because its response was lost.

## Partial completion

When a run stops:

1. Mark unfinished work `pending` and uncertain effects `unknown`.
2. Stop new side effects and preserve the checkpoint.
3. Query or reconcile the target before retrying.
4. Compensate applied effects where safe, or request manual recovery.
5. Resume only from a verified checkpoint in a new or explicitly resumed
   session.

File changes use the same rule: verify the current tree and diff before
reapplying a step. Do not overwrite uncommitted work to make a replay pass.

## Completion

A packet is not complete until all operations are `completed`, `compensated`,
or explicitly accepted as a documented `unknown` with user approval. The
handoff links the final checkpoint and lists unresolved external effects.
