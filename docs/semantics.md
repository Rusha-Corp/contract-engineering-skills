# Semantic Engineering

## Purpose

Semantics are the agreed meaning, rules, assumptions, and observable behavior
of a system element or boundary. Syntax describes form; structure describes
arrangement; semantics describe what the element means and does.

Semantic engineering makes meaning visible without pretending that a project
knows everything at the beginning. The protocol therefore treats uncertainty
as a recordable state that should become clearer through decisions, examples,
tests, observation, and controlled change.

## What is semantic work?

Semantic work includes changes to:

- domain terms, concepts, identities, units, or ownership;
- service responsibilities, bounded contexts, and dependency boundaries;
- API, event, command, or message meaning;
- data-model meaning, lineage, freshness, permissions, or nullability;
- workflow states, transitions, terminality, retries, and compensation;
- user-visible behavior and the interpretation of controls or statuses;
- agent authority, tool meaning, approval behavior, or prohibited outcomes.

Purely operational work may have `semantic_scope: none`. A packet that changes
or relies on meaning declares `semantic_scope: affected` or `defined` and
links a semantic contract.

## Semantic contract

`templates/semantic-contract.yaml` is a versioned record for the current
understanding of a semantic boundary. It is deliberately broader than an API
schema and more concrete than a prose design note. It records:

- purpose and scope, including explicit exclusions;
- vocabulary, synonyms, and prohibited interpretations;
- concepts and invariants;
- states and valid transitions when applicable;
- boundary inputs, outputs, preconditions, postconditions, and failure
  semantics;
- ordering, consistency, idempotency, and freshness assumptions;
- examples and counterexamples;
- compatibility, migration, and deprecation expectations;
- open questions, owners, review status, and change history.

The machine validator checks the contract's shape and references. Domain
experts and reviewers decide whether its meanings are correct. A structurally
valid contract is not proof that the domain model is correct.

## Progressive maturity

Semantic maturity is not a score and does not replace engineering judgment.
Use it to show what is known and what still needs discovery:

| Maturity | Meaning | Expected practice |
| --- | --- | --- |
| `fuzzy` | Important meanings are incomplete or contested. | Record the affected area, competing interpretations, owners, and next discovery action. |
| `emerging` | Core terms and boundaries exist, but material questions remain. | Review the vocabulary, scope, invariants, and representative examples. |
| `structured` | The current contract is coherent enough to guide implementation. | Trace implementation and validation to the contract, including failure behavior. |
| `stable` | Compatibility expectations and protective checks are established. | Monitor fitness functions, consumers, drift, and deprecation triggers. |
| `deprecated` | A replacement meaning or boundary is being adopted. | Follow the migration and removal rules; do not silently reinterpret consumers. |

An early packet may be `fuzzy` or `emerging` and still proceed when its
uncertainty is explicit, the current contract is approved for the bounded
change, and the packet's acceptance criteria do not depend on unanswered
questions. Unresolved questions become tracked semantic debt, not hidden
assumptions.

## Workflow

1. **Inventory meaning:** identify terms, actors, boundaries, states, data,
   assumptions, and consumers affected by the packet.
2. **Separate certainty levels:** distinguish observed facts, decisions,
   assumptions, hypotheses, and open questions.
3. **Create or revise the contract:** record the smallest useful current
   vocabulary, invariants, boundary behavior, examples, and failure meaning.
4. **Review the current interpretation:** domain owners and technical
   reviewers approve the contract for the packet's scope. Approval is not a
   claim that the contract is permanently complete.
5. **Implement and verify:** use tests, contract tests, examples, fixtures,
   observations, and review evidence to check the meaning, not just the
   syntax.
6. **Record change:** when implementation or discovery changes meaning, update
   the contract version and change log, assess consumers and compatibility,
   and record a decision or migration.
7. **Improve structure:** promote recurring open questions into explicit
   invariants, examples, profiles, or fitness functions. Retire stale
   concepts only through evidence-backed deprecation.

## Profiles

Profiles focus the universal contract without creating separate incompatible
protocols:

- **architecture:** responsibilities, ownership, dependency direction,
  boundaries, and architectural invariants;
- **api:** request and response meaning, preconditions, errors, ordering,
  idempotency, and compatibility;
- **event:** facts versus commands, producers, consumers, delivery, replay,
  ordering, and schema evolution;
- **data:** business meaning, units, ownership, lineage, freshness,
  nullability, permissions, and migration;
- **workflow:** states, triggers, guards, terminality, retries,
  compensation, and recovery;
- **ui:** user-visible meaning, interaction states, accessibility intent,
  validation, and loading, empty, and error behavior;
- **agent:** authority, interpretation boundaries, tool meaning, approvals,
  uncertainty, and prohibited outcomes.

Use only the profiles relevant to the packet. Add profile-specific fields
under `profile_data` when the universal core is insufficient, and document
the extension rather than silently inventing a competing format.

## Avoiding rigidity and spaghetti

The protocol uses these guardrails:

- Do not require a semantic contract for work that declares `none`.
- Do not reject discovery because every term is not yet settled.
- Do not let uncertainty disappear from the record; give it an owner and
  next action.
- Do not force one universal model across bounded contexts. Record local
  meanings and explicit translations.
- Do not treat a green schema check as proof of semantic compatibility.
- Do not change a shared meaning without consumer analysis, compatibility
  evidence, or an explicit migration and deprecation plan.
- Prefer small, reversible changes and measurable fitness functions over
  broad speculative abstractions.

## Semantic validation

At minimum, semantic validation should include the checks that fit the
profile:

- terminology and identity consistency;
- invariant and state-transition tests;
- API/event contract or compatibility tests;
- data mapping, units, permissions, and freshness checks;
- workflow failure, retry, and recovery cases;
- UI interaction and accessibility-state checks;
- agent authority, approval, and prohibited-outcome cases.

The handoff must state which meanings were verified, which remain uncertain,
what evidence supports them, and the exact next action for unresolved items.

## Prior art informing this guidance

This practice combines established ideas while keeping the protocol
tool-agnostic:

- [Ubiquitous Language](https://martinfowler.com/bliki/UbiquitousLanguage.html)
  and [Bounded Context](https://martinfowler.com/bliki/BoundedContext.html)
  keep domain language shared within explicit boundaries.
- [Architecture Decision Records](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html)
  preserve why a meaning or boundary changed.
- [Evolutionary Architecture](https://martinfowler.com/articles/evo-arch-forward.html)
  uses guided, incremental change and fitness functions instead of frozen
  up-front design.
- [Consumer-driven contract testing](https://pactflow.io/what-is-consumer-driven-contract-testing/)
  checks that a provider preserves consumer expectations.
- [AWS backward-compatible schema guidance](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.ads.5-ensure-backwards-compatibility-for-data-store-and-schema-changes.html)
  reinforces compatibility planning for evolving data meaning and structure.
