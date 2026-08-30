# CI security

The protocol-validation workflow is intentionally safe to run for untrusted
pull requests. It uses the `pull_request` event, never checks out a merge-base
with elevated credentials, requests only `contents: read`, and does not receive
repository secrets. The job validates submitted repository records, so the
submitted files must be treated as untrusted input. No step publishes artifacts,
comments, deploys, or writes to the repository.

## Required workflow controls

- Every third-party action is pinned to a reviewed 40-character commit SHA.
  The inline invariant check rejects tags, branches, and abbreviated SHAs.
- `actions/checkout` uses `persist-credentials: false` and a shallow checkout.
- The job has an explicit ten-minute timeout.
- Concurrency cancels superseded runs for the same workflow and ref.
- The workflow uses a fixed `ubuntu-24.04` runner label rather than
  `ubuntu-latest`.
- `pull_request_target` and `workflow_run` are prohibited in this validation
  workflow because they can combine untrusted pull-request content with
  privileged repository context.

The static invariant check is deliberately local and fail-fast. It checks the
checked-out workflow before record validation and must remain in the workflow
when action or trigger changes are proposed.

The record validator also applies reviewed parser limits before constructing
objects: 1 MiB per YAML file, 256 KiB per scalar, 10,000 events, 64 nesting
levels, 50 aliases, ten CPU seconds, and 512 MiB address space. It uses
`yaml.SafeLoader` only. Oversized, malformed, deeply nested, and alias-heavy
inputs are rejected without echoing their contents. Parser failures remain
bounded by the workflow timeout and isolated to the read-only job. The
address-space limit is applied on supported runners; macOS may reject lowering
the process limit after interpreter startup, so local validation still relies
on all parser-level bounds and the workflow timeout.

## Dependency policy

`requirements-ci.txt` is the complete CI dependency manifest. Installations
must use `python -m pip install --require-hashes -r requirements-ci.txt`.
Hashes are obtained from the approved PyPI source and are updated in the same
review as a version change. The current workflow is intentionally constrained
to the Python 3.12 Linux x86_64 wheel, matching its runner. Dependabot
proposes action and pip updates weekly; updates require review of both the
version and immutable references or hashes.

## Review and incident handling

Changes to this workflow, its dependency manifest, or Dependabot policy
require review under the repository's security and ownership controls. If a
workflow credential, action reference, or dependency is suspected to be
compromised:

1. Disable or revert the affected workflow change and cancel active runs.
2. Rotate any credential that may have been exposed, even though this workflow
   is designed not to receive secrets.
3. Preserve run URLs and commit references as restricted incident evidence.
4. Record the incident under the agent incident-response process before
   restoring validation.

References:

- https://docs.github.com/en/actions/reference/security/secure-use
- https://docs.github.com/en/actions/concepts/security/script-injections
- https://github.com/actions/checkout
- https://scorecard.dev/
