# Packet Leases and Distributed Coordination

Worktrees isolate files. They do not by themselves prevent two agents from
claiming the same logical packet, using the same external resource, or
continuing after a stale claim. Use `templates/packet-lease.yaml` when packet
coordination is concurrent or side-effecting.

## Lease contract

A lease identifies one holder, session, issue time, expiry, heartbeat, renewal
count, and fencing token. The coordination store must make claim, renewal,
release, and takeover atomic. A timestamp written by two agents without an
atomic compare-and-set is not a lease.

The holder renews before expiry. A missed heartbeat does not immediately prove
failure; use the configured grace period and coordination-store clock. The
old holder must stop when its lease expires or its fencing token is rejected.

## Fencing and shared resources

Every write to a protected shared resource carries the current fencing token.
The resource rejects tokens older than the latest accepted token. This
prevents a paused or partitioned agent from writing after another agent takes
over.

Packet locks, worktrees, external APIs, credentials, and generated artifacts
may each need separate ownership. Do not infer that a worktree lock protects
an external resource.

## Takeover

Takeover requires:

1. Verify the lease is expired, revoked, or explicitly released.
2. Record the prior holder, reason, last heartbeat, current revision, and
   recovery plan.
3. Issue a new fencing token and lease to the new holder.
4. Revalidate packet scope, approvals, budget, checkpoint, and external
   effects before resuming.
5. Preserve the prior session and evidence; do not silently overwrite it.

If the old holder may still be active and fencing cannot be enforced, block
the takeover and escalate to the reviewer or user.

## Failure states

- `expired`: lease passed its expiry without a verified renewal;
- `revoked`: reviewer or incident response stopped the holder;
- `takeover`: a new holder is being established;
- `split_brain`: multiple holders may have acted; block writes and open an
  incident;
- `released`: holder completed or intentionally surrendered the packet.

The tracker and packet state must agree with the lease record. A completed
packet has no active lease. A stale lock is not cleanup authorization.

## Native lifecycle conformance

The host must evaluate a requested transition against the packet's current
state before changing the tracker or packet. The transition record includes
the source state, destination state, reason, packet ID, and authenticated
actor. The following cases are mandatory:

| Requested transition | Native result |
| --- | --- |
| `Validation -> Handoff` with passing evidence | Permit |
| `Validation -> Complete` without a handoff | Block |
| `Handoff -> Complete` without authenticated receiver acceptance | Block |
| `Handoff -> Complete` with mismatched revision or scope | Block |
| `Complete -> Implementing` | Block |
| `Rework -> Implementing` with a current claim | Permit |
| `Cancelled -> Implementing` | Block |

The host must persist a redacted failure event for every blocked transition.
Updating a Markdown row or YAML state without a native transition decision is
not a valid lifecycle event.

## Packet state integrity

The coordination store or native harness must enforce the packet transition
table in `phased-engineering-execution/SKILL.md`. A packet cannot move to
`Complete` because a tracker row was edited: it needs a receiver-accepted
handoff whose revision, scope digest, changed-resource hashes, approval, and
validation evidence match the packet. `Interrupted` and `Cancelled` records
must carry a reason, disposition, and recovery or closure path. Invalid or
unverifiable transitions are blocked and retained as audit evidence.

## File-only fallback

Projects without a coordination service may use an atomic repository commit
or host-provided exclusive lock for low-risk file-only work. This fallback
must state its limitations, use short-lived claims, and block high-risk
external effects. It must not be described as split-brain-safe.
