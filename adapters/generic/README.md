# Generic Host Adapter

This repository's core protocols are Markdown and YAML. A coding assistant,
CI runner, IDE, or human team can consume them without installing a vendor
runtime.

## Integration

1. Make the five root protocol directories available to the host's project
   instructions.
2. Create a project-local execution tracker and work packets from
   `templates/work-packet.yaml`.
3. Record deprecations using `templates/deprecation-record.yaml`.
4. Store evidence and handoffs in the consuming project.
5. Map the host's approval step to the Design Gate and map its test output to
   evidence references.
6. Run the non-destructive checks in `templates/validation-guide.md`.

The host should provide a way to claim ownership, lock shared resources,
record decisions, run validation, accept handoffs, and retain evidence. If a
host lacks one of these capabilities, record the limitation as a Skill Gap
instead of silently skipping the control.

## Conformance

An adapter conforms when it demonstrates:

- Baseline and packet creation
- Design and data gates
- Implementation and validation
- Deprecation and sunset review
- Evidence-backed cleanup
- Handoff acceptance
- Practice review and closure
