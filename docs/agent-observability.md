# Agent Observability

Agent work is a distributed execution trace across sessions, models, tools,
worktrees, approvals, and external systems. Use
`templates/agent-event.yaml` for a stable, privacy-aware event vocabulary.

## Required events

Emit or record events for:

- agent or run start and stop;
- model calls and delegated-agent boundaries;
- tool calls and returned outcomes;
- approval requested, granted, denied, or expired;
- file or configuration changes;
- validation, retry, failure, cancellation, and quarantine;
- external effects;
- handoff and packet state transitions.

Every event has an ID, timestamp, packet, run, operation, actor, outcome, and
correlation parent where applicable. Include resource identifiers and digests,
not raw sensitive payloads.

## Privacy and integrity

Raw prompts, model responses, tool arguments, and tool results are disabled by
default. Events carry classification, redaction state, and a reference to
sanitized evidence when content is necessary. Apply the evidence security
policy before export.

Events should be append-only and tamper-evident. The collector records
sequence gaps, clock limitations, dropped events, export failures, and
sampling decisions. A telemetry failure must not be reported as successful
completion or silently disable an approval or safety control.

OpenTelemetry GenAI semantic conventions are a compatible mapping for spans
and metrics. The protocol remains vendor-neutral and requires the local
event fields even when a host uses another telemetry system.

## Correlation and metrics

Correlate `packet_id`, `run_id`, `operation_id`, `event_id`, actor, session,
approval, checkpoint, evaluation, incident, and evidence references. At
minimum, derive:

- success, failure, cancellation, and unknown-effect counts;
- scope and approval violations;
- tool-call, retry, duration, token, and cost usage;
- validation and evaluation outcomes;
- stale lease, quarantine, and recovery time;
- dropped or redaction-failed event counts.

Metrics are indicators, not permission. A low error rate cannot override a
critical safety or authorization failure.

## Retention and access

Apply the evidence classification and retention policy to events. Restrict
access to sensitive traces, encrypt them in transit and at rest, and retain
only the metadata needed for audit, debugging, evaluation, and incident
response. Record who queried restricted telemetry when the host supports it.
