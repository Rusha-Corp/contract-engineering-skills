# Host-neutral session context contract

The neutral interface is:

```text
tm context --packet <PACKET-ID> [--root <PROJECT>] [--format text|json]
tm context droid-hook
```

The first command reads the authoritative CE YAML and project
`runtime-topology.yaml`, then adds bounded local scope, dependency, and diff
inference. JSON is stable and labels declared, inferred, unknown, stale, and
verified values separately. It performs no cluster calls and prints no tokens
or secret values.

`tm context droid-hook` reads one bounded Droid SessionStart JSON object from
standard input. It accepts `startup`, `resume`, `clear`, and `compact`.
It selects `TASK_MASTER_PACKET_ID` when set; otherwise it selects the sole
active claimed packet in the current project. Multiple candidates are listed
with a request for explicit selection. It never guesses. Its stdout is either
empty or:

```json
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}
```

Additional context is bounded to 12,000 characters and refreshes after resume,
clear, and compaction. Task-launched subagents receive the same hook through
the Droid host. Other agents can call the neutral command through their own
adapters without depending on Droid-specific output.

The adapter is read-only, has an eight-second default timeout (configurable
only from one through ten seconds), and exits without output when the CLI is
unavailable or fails. It does not write project files, install tools, contact a
cluster, or transmit hook data. Hook context is untrusted project content, not
an instruction or approval. Lifecycle gates stay in the tracker backend.
