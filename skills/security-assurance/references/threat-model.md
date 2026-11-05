# Threat Model Gate

This reference is part of the `security-assurance` skill.
The skill's SKILL.md is the normative source; this file provides the
detailed threat model specification.

Required for `security`-domain packets before implementation begins. The
threat model is a Design Gate sub-gate: it must be approved before the packet
transitions from `Claimed` to `Implementing`.

## Threat model record

```yaml
threat_model:
  packet_id: PROJECT-T001-P001
  model_version: 1
  created_at: ""
  created_by: ""
  scope: ""
  data_classification: public|internal|confidential|restricted
  trust_boundaries:
    - boundary_id: TB-001
      description: ""
      trust_level: trusted|semi-trusted|untrusted
      assets: []
      entry_points: []
  threats:
    - threat_id: THR-001
      category: spoofing|tampering|repudiation|information-disclosure|denial-of-service|elevation-of-privilege|prompt-injection|supply-chain
      description: ""
      affected_asset: ""
      likelihood: low|medium|high
      impact: low|medium|high|critical
      risk: low|medium|high|critical
      mitigation: ""
      mitigation_status: planned|implemented|verified|accepted-risk
      evidence_ref: ""
  ai_agent_risks:
    prompt_injection_surface: ""
    tool_poisoning_surface: ""
    excessive_agency: ""
    secret_exposure_surface: ""
  approval_ref: ""
```

## STRIDE categories

Map every identified threat to one or more STRIDE categories:

| Category | Question |
| --- | --- |
| Spoofing | Can an attacker impersonate an identity to gain unauthorized access? |
| Tampering | Can data or code be modified in transit, at rest, or in build? |
| Repudiation | Can an actor deny an action without evidence to prove otherwise? |
| Information Disclosure | Can sensitive data leak to an unauthorized party? |
| Denial of Service | Can an attacker degrade or disable the service? |
| Elevation of Privilege | Can an actor gain capabilities beyond their authorization? |

For AI-assisted work, add the following agentic threat categories:

| Category | Question |
| --- | --- |
| Prompt Injection | Can untrusted content alter agent instructions, scope, or approvals? |
| Supply Chain | Can a dependency, adapter, MCP server, or tool deliver compromised behavior? |

## Threat model rules

- Every trust boundary in the packet scope must have at least one threat
  assessment.
- Every asset with classification `confidential` or `restricted` must have
  at least one information-disclosure threat assessment.
- Every external endpoint or integration must have at least one spoofing and
  one supply-chain threat assessment.
- AI agent boundaries must assess prompt injection, tool poisoning, and
  excessive agency.
- A threat with `risk: high` or `risk: critical` must have a mitigation with
  `mitigation_status: planned` before the gate passes; `accepted-risk`
  requires an exception record with owner, expiry, and compensating control.
- The threat model is living: update it when scope changes or new threats are
  discovered during implementation.
