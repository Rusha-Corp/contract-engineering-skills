# Adapter and Dependency Security

An adapter is part of the agent's trust and capability boundary. This includes
host integrations, CLIs, plugins, MCP servers, tool definitions, runtimes,
packages, actions, and external endpoints. Inventory each supported adapter
with `templates/adapter-inventory.yaml` before allowing it to execute a
packet.

## Inventory requirements

Record:

- owner, version, source ref, provenance, signature, and compatibility;
- capabilities and permissions;
- every network endpoint and whether each operation is allowlisted;
- direct and transitive dependencies, lockfile refs, licenses, and
  vulnerability status;
- validation/evaluation references, approval, status, and rollback.

Do not accept an adapter whose source, version, permissions, or endpoint set
cannot be identified.

## Capability and endpoint controls

Use least privilege. An adapter receives only the capabilities required by the
packet and cannot grant new capabilities to an agent. Network access is
deny-by-default and limited to named hosts and operations. Redirects,
user-controlled URLs, tool-provided URLs, and dynamically discovered servers
must be validated against the allowlist.

Tool and MCP descriptions are untrusted input. Validate schemas, authentication
boundaries, authorization, output types, and side effects. Do not pass
ambient credentials or unrestricted repository context to an adapter.

## Dependency checks

Before approval and on every version change:

1. Resolve the exact dependency and adapter refs from lockfiles or manifests.
2. Verify publisher provenance and artifact integrity.
3. Run vulnerability and license checks for direct and transitive
   dependencies.
4. Review permissions, endpoints, migration impact, and compatibility.
5. Run representative and adversarial evaluation cases.
6. Record the result and reviewer in the inventory.

Unknown vulnerability, provenance, or compatibility status blocks high-risk
and external-effect use. A temporary exception requires owner, mitigation,
expiry, and rollback.

## Revocation and rollback

Set an adapter to `revoked` when it is compromised, incompatible, vulnerable
above the accepted threshold, or violates its declared capability boundary.
Stop new use, quarantine active sessions, preserve evidence, and disable
credentials or endpoints as required. Roll back to the last verified ref or
use a manually approved replacement. Do not delete the inventory or incident
record.
