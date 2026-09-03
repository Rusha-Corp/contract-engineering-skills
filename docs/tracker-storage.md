# Tracker storage and database-backed consumers

The tracker has two audiences: agents need bounded, machine-readable state,
while engineers need a compact reviewable view. Keep those concerns separate.

## Canonical record layout

```text
.contract-engineering/
  tracker/
    index.yaml
    shards/<TASK-ID>.yaml
    events/<TASK-ID>.yaml
    archive/index.yaml
  work-packets/<PACKET-ID>.yaml
  evidence/
  handoffs/
  archive/work-packets/
```

`tracker/index.yaml` is the active cross-task index. It contains no more than
25 packet rows. A task with more active rows moves its rows to one or more
task-owned shards declared by the index. Each shard has no more than 50 rows.
When a task would exceed that limit, split the task into child tasks rather
than creating an unbounded shard.

`tracker/archive/index.yaml` is the machine-readable archive partition.
Terminal packet rows move from the active index or shard to the archive;
they are not copied. Packet YAML moves with its tracker row, while evidence
and handoffs retain their own retention policy and references.

`tracker/events/<TASK-ID>.yaml` is append-only narrative and transition
history. The active index and shards hold the latest projection only. Do not
append session logs, tool output, or repeated status history to the active
projection.

## Markdown projection

`execution-tracker.md` and `archive/execution-tracker-archive.md` are
generated human-readable projections. They are not canonical state. Render
them with:

```bash
python3 scripts/render-tracker.py --root .contract-engineering
```

CI and pre-commit checks should use `--check` to reject projection drift:

```bash
python3 scripts/render-tracker.py \
  --root .contract-engineering \
  --check
```

Agents should read the active index, the shard for the current task, the
assigned packet, direct dependency summaries, and linked evidence. They
should not load the complete archive or event history unless the task
requires historical analysis.

## Validation and concurrency

Use `scripts/validate-tracker.py` to enforce:

- valid packet and task identifiers;
- one tracker row per packet;
- no active/archive overlap;
- no orphan rows or packet files;
- packet state, owner, reviewer, and locks matching the tracker projection;
- terminal-only archive rows;
- active index and shard row limits; and
- task ownership of every shard row.

State changes must update the packet YAML, the canonical tracker projection,
and the event stream as one logical operation. A database or native harness
should use optimistic concurrency with a packet revision or compare-and-swap
condition. If a write loses the race, reload and reconcile rather than
overwriting another actor's state.

## Database-backed Packet consumers

The Packet application being developed in the Factory Floor repository is an
intended database-backed consumer of this protocol. It may store the same
records in relational tables for query, filtering, ownership views, and
review workflows, but the database is a projection and coordination store,
not permission to discard the repository contract.

A compatible database design should preserve:

| Protocol record | Database responsibility |
| --- | --- |
| Packet YAML | Versioned packet snapshot with a unique packet ID and revision |
| Tracker index/shard row | Current bounded status projection |
| Tracker event | Append-only transition and audit event |
| Evidence reference | Immutable reference and classification metadata |
| Handoff | Sender/receiver decision, validation binding, and acceptance status |
| Lock | Lease owner, scope, expiry, and release state |

Each state transition should transactionally:

1. verify the expected packet revision and current lifecycle state;
2. validate the transition and active locks;
3. append an event with actor, run, timestamp, and reason;
4. update the current packet/tracker projection; and
5. commit the new revision.

Database-backed consumers must retain export/import compatibility with the
YAML records, preserve evidence and handoff IDs, and support a full audit
export. Replication, search indexes, UI caches, and analytics are derived
data. They must never become a second source of truth with different state
transitions.

The database implementation, migrations, authentication, and production
deployment belong in consumer packets. This protocol release defines the
record and projection boundary only; it does not ship a Packet database.
