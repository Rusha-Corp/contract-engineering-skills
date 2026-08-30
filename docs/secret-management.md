# Secret management

## Repository boundary

Credentials do not belong in source, packet records, evidence, logs, screenshots,
generated artifacts, or Git history. `.gitignore` reduces accidental staging of
common credential filenames, but it is not a security boundary. The Gitleaks
configuration and CI workflow are the enforcement boundary.

The scanner is pinned to Gitleaks 8.24.3. The Linux x86_64 release archive used
in CI has SHA-256
`9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c`. For local
macOS installation, verify the corresponding release checksum before placing
the binary on `PATH`:

- Darwin x86_64:
  `41c44ae8ad1d6eef57d4526ad0fd67d8129eee9a856f55c2b3b9395fd3d9ec0f`
- Darwin arm64:
  `b90f13bb8c90ab72083d9b0c842e39dafb82c0e5c3f872f407366b7a58909013`

Run both history and working-tree scans locally:

```sh
gitleaks detect --source . --redact --exit-code 1 --config .gitleaks.toml
gitleaks dir . --redact --exit-code 1 --config .gitleaks.toml
```

## Containment and rotation

If a scan detects a credential:

1. Stop distribution and do not paste the value into an issue, packet, log, or
   chat.
2. Record only the redacted finding identifier, path, commit, timestamp, and
   scanner version.
3. Revoke or rotate the credential at its issuing system, then verify the old
   value no longer works.
4. Assess Git history, CI logs, caches, artifacts, forks, and external stores.
5. Link the redacted evidence to an incident record and preserve chain of
   custody.
6. Remove the value from current files and rewrite history when required by the
   incident owner and repository policy.

False positives require reviewer-approved, narrowly scoped Gitleaks
allowlisting. Never allowlist a live credential or an entire directory to make
a scan green. Restricted evidence goes to an approved encrypted store with
role-based access and retention controls.
