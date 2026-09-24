#!/usr/bin/env python3
"""Validate Contract Engineering records and optionally enforce packet scope."""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from collections import namedtuple
from pathlib import Path

IDENTIFIERS = Path(__file__).with_name("identifiers.py")
IDENTIFIER_SPEC = importlib.util.spec_from_file_location("identifiers", IDENTIFIERS)
assert IDENTIFIER_SPEC and IDENTIFIER_SPEC.loader
identifiers = importlib.util.module_from_spec(IDENTIFIER_SPEC)
IDENTIFIER_SPEC.loader.exec_module(identifiers)
from typing import Any

import yaml
import jsonschema
from referencing import Registry, Resource
from yaml.events import (
    AliasEvent,
    MappingEndEvent,
    MappingStartEvent,
    SequenceEndEvent,
    SequenceStartEvent,
)
try:
    import resource
except ImportError:  # pragma: no cover - Windows has no resource module
    resource = None

STATES = {
    "Planned",
    "Claimed",
    "DesignReview",
    "DesignBlocked",
    "DataReview",
    "DataBlocked",
    "Ready",
    "Implementing",
    "Validation",
    "Rework",
    "Handoff",
    "Complete",
    "Interrupted",
    "Cancelled",
}
DOMAINS = {"coding", "browser", "design", "data", "documentation", "security"}
TASK_ID = identifiers.TASK_ID
PACKET_ID = identifiers.PACKET_ID
BASE_REVISION = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_YAML_BYTES = 1 * 1024 * 1024
MAX_SCALAR_BYTES = 256 * 1024
MAX_YAML_NODES = 10_000
MAX_YAML_DEPTH = 64
MAX_YAML_ALIASES = 50
MAX_CPU_SECONDS = 10
MAX_ADDRESS_SPACE = 512 * 1024 * 1024
SECURITY_SCOPE_PATTERNS = (
    ".github/workflows/",
    "adapters/",
    "docs/agent-security.md",
    "docs/adapter-security.md",
    "docs/approval-integrity.md",
    "docs/incident-response.md",
    "docs/release-integrity.md",
    "schemas/",
    "templates/adapter-",
    "templates/agent-",
)
PACKET_CLASSES = {
    "single-domain",
    "cross-cutting",
    "parent-coordination",
    "child-implementation",
}
ACCEPTANCE_CRITERION_ID = re.compile(r"^[A-Z0-9-]+-AC\d{3}$")
VALIDATION_PLAN_ID = re.compile(r"^[A-Z0-9-]+-VAL\d{3}$")
OPEN_QUESTION_ID = re.compile(r"^[A-Z0-9-]+-OQ\d{3}$")
EPIC_ID = re.compile(r"^(?:[A-Z][A-Z0-9]*-)+E\d{3}$")
WORK_TYPES = {"discovery", "delivery", "bugfix", "enabler"}
PRIORITIES = {"critical", "high", "normal", "deferred"}
QUESTION_DISPOSITIONS = {"blocking", "bounded", "resolved", "follow_up", "deferred"}
EXECUTION_CONTROL_REFS = (
    "trust_boundary_ref",
    "execution_budget_ref",
    "checkpoint_ref",
    "evaluation_ref",
    "agent_run_ref",
    "observability_refs",
    "incident_refs",
)
FORBIDDEN_CAPABILITIES = {
    "admin:repository",
    "write:outside-scope",
    "execute:untrusted",
}


def fail(message: str) -> None:
    raise ValueError(message)


ValidationResult = namedtuple(
    "ValidationResult", ("mode", "valid", "skipped", "messages"),
    defaults=(False, ()),
)


def _configured_root(project_dir: Path) -> str | None:
    lock_path = project_dir / ".contract-engineering" / "protocol.lock.yaml"
    if not lock_path.is_file():
        return None
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8")) or {}
    configured = lock.get("project", {}).get("protocol_root")
    return configured if isinstance(configured, str) and configured else None


def resolve_protocol_root(
    project_dir: Path | str = ".",
    *,
    explicit_root: Path | str | None = None,
    environment: dict[str, str] | None = None,
) -> Path:
    """Resolve records as explicit path, environment, lock, then default.

    Relative roots are always relative to ``project_dir``; absolute roots are
    retained.  This keeps adapter callers deterministic regardless of cwd.
    """

    project = Path(project_dir).expanduser().resolve()
    values = environment if environment is not None else os.environ
    configured = (
        explicit_root
        if explicit_root is not None
        else values.get("CE_PROTOCOL_ROOT")
        or _configured_root(project)
        or ".contract-engineering"
    )
    root = Path(configured).expanduser()
    return root if root.is_absolute() else project / root


def _validate_records(root: Path, packet_path: Path | None, changed_paths: list[str]) -> None:
    if not root.is_dir():
        fail(f"protocol root does not exist: {root}")
    configure_resource_limits()
    def load_partition(directory: Path) -> dict[str, dict[str, Any]]:
        partition: dict[str, dict[str, Any]] = {}
        if not directory.is_dir():
            return partition
        for path in sorted(directory.glob("*.yaml")):
            packet = load_yaml(path)
            if not isinstance(packet, dict) or "packet_id" not in packet:
                fail(f"{path}: packet must be a YAML mapping with packet_id")
            packet_id = packet["packet_id"]
            if packet_id in partition:
                fail(f"duplicate packet ID in {directory}: {packet_id}")
            partition[packet_id] = packet
        return partition
    live_packets = load_partition(root / "work-packets")
    archive_packets = load_partition(root / ARCHIVE_PACKET_DIR)
    cross_dup = set(live_packets) & set(archive_packets)
    if cross_dup:
        fail(f"duplicate packet IDs across partitions {sorted(cross_dup)}")
    packets = {**live_packets, **archive_packets}
    validate_json_schemas(root, packets)
    for directory, partition in (
        (root / "work-packets", live_packets),
        (root / ARCHIVE_PACKET_DIR, archive_packets),
    ):
        if directory.is_dir():
            for path in sorted(directory.glob("*.yaml")):
                validate_packet(path, packets[path.stem], packets)
    validate_project_lock(root)
    validate_canonical_tracker(root)
    validate_tracker(root, live_packets, archive_packets)
    validate_dependency_graph(packets)
    validate_locks(packets)
    validate_references(root, packets)
    validate_planning_records(root, packets)
    if packet_path:
        packet = packets.get(packet_path.stem)
        if packet is None:
            fail(f"unknown packet {packet_path}")
        enforce_scope(packet, changed_paths)


def validate_json_schemas(root: Path, packets: dict[str, dict[str, Any]]) -> None:
    """Validate canonical records with the pinned JSON Schema implementation."""
    schema_dir = root.parent / "schemas"
    documents = {
        path.name: load_json_schema(path)
        for path in schema_dir.glob("*.json")
    }
    store: dict[str, dict[str, Any]] = {}
    for name, document in documents.items():
        store[name] = document
        if document.get("$id"):
            store[document["$id"]] = document
    registry = Registry().with_resources(
        [
            (document["$id"], Resource.from_contents(document))
            for document in documents.values()
            if document.get("$id")
        ]
    )
    schemas = {}
    for schema_name in (
        "work-packet.schema.json",
        "tracker.schema.json",
        "tracker-event.schema.json",
    ):
        document = documents.get(schema_name)
        if document is None:
            fail(f"{schema_dir / schema_name}: schema is missing")
        validator_class = jsonschema.validators.validator_for(document)
        validator_class.check_schema(document)
        schemas[schema_name] = validator_class(document, registry=registry)
    packet_validator = schemas["work-packet.schema.json"]
    for packet_id, packet in packets.items():
        errors = sorted(
            packet_validator.iter_errors(packet),
            key=lambda error: list(error.path),
        )
        if errors:
            location = ".".join(str(part) for part in errors[0].path) or "<root>"
            fail(
                f"{packet_id}: schema validation failed at {location}: "
                f"{errors[0].message}"
            )
    for directory, schema_name, identifier_key in (
        (root / "epics", "epic.schema.json", "epic_id"),
        (root / "tasks", "task.schema.json", "task_id"),
    ):
        if not directory.is_dir():
            continue
        document = documents.get(schema_name)
        if document is None:
            fail(f"{schema_dir / schema_name}: schema is missing")
        validator_class = jsonschema.validators.validator_for(document)
        instance_validator = validator_class(document, registry=registry)
        for path in sorted(directory.glob("*.yaml")):
            validate_instance(
                instance_validator,
                load_yaml(path),
                f"{path} ({identifier_key})",
            )
    tracker_validator = schemas["tracker.schema.json"]
    for path in _tracker_instance_paths(root):
        validate_instance(tracker_validator, load_yaml(path), str(path))
    event_validator = schemas["tracker-event.schema.json"]
    for path in sorted((root / "tracker/events").glob("*.yaml")):
        validate_instance(event_validator, load_yaml(path), str(path))
    identifier_schema = load_json_schema(schema_dir / "identifiers.schema.json")
    task_validator = jsonschema.Draft202012Validator(
        identifier_schema["$defs"]["taskId"]
    )
    packet_validator = jsonschema.Draft202012Validator(
        identifier_schema["$defs"]["packetId"]
    )
    for packet_id, packet in packets.items():
        validate_identifier(task_validator, packet.get("task_id"), f"{packet_id}.task_id")
        validate_identifier(packet_validator, packet_id, f"{packet_id}.packet_id")
        for dependency in packet.get("dependencies", []):
            validate_identifier(packet_validator, dependency, f"{packet_id}.dependency")


def load_json_schema(path: Path) -> dict[str, Any]:
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(f"{path}: cannot load JSON Schema: {exc}")


def validate_instance(validator: Any, instance: Any, label: str) -> None:
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        fail(f"{label}: schema validation failed at {location}: {errors[0].message}")


def _tracker_instance_paths(root: Path) -> list[Path]:
    paths = []
    index = root / "tracker/index.yaml"
    archive = root / "tracker/archive/index.yaml"
    if index.is_file():
        paths.append(index)
        document = load_yaml(index)
        for relative in document.get("shards", []):
            path = root / relative
            if path.is_file():
                paths.append(path)
    if archive.is_file():
        paths.append(archive)
        document = load_yaml(archive)
        for relative in document.get("shards", []):
            path = root / relative
            if path.is_file():
                paths.append(path)
    return paths


def validate_identifier(validator: Any, value: object, label: str) -> None:
    try:
        validator.validate(value)
    except jsonschema.ValidationError as exc:
        fail(f"{label}: JSON Schema validation failed: {exc.message}")


def run_validation(
    project_dir: Path | str = ".",
    *,
    explicit_root: Path | str | None = None,
    mode: str | None = None,
    environment: dict[str, str] | None = None,
    packet_path: Path | None = None,
    changed_paths: list[str] | None = None,
) -> ValidationResult:
    """Run local validation in explicit off, advisory, or enforced mode."""

    values = environment if environment is not None else os.environ
    selected = mode or values.get("CE_VALIDATION_MODE", "enforced")
    if selected not in {"off", "advisory", "enforced"}:
        raise ValueError(f"invalid validation mode: {selected}")
    if selected == "off":
        return ValidationResult(selected, valid=True, skipped=True)
    root = resolve_protocol_root(
        project_dir, explicit_root=explicit_root, environment=environment
    )
    try:
        _validate_records(root, packet_path, changed_paths or [])
    except ValueError as exc:
        if selected == "enforced":
            raise
        return ValidationResult(selected, valid=False, messages=(str(exc),))
    return ValidationResult(selected, valid=True)


def load_yaml(path: Path) -> Any:
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_YAML_BYTES:
            fail(f"{path}: YAML exceeds the {MAX_YAML_BYTES}-byte limit")
        text = raw.decode("utf-8")
        depth = 0
        nodes = 0
        aliases = 0
        for event in yaml.parse(text, Loader=yaml.SafeLoader):
            nodes += 1
            if nodes > MAX_YAML_NODES:
                fail(f"{path}: YAML exceeds the {MAX_YAML_NODES}-node limit")
            if isinstance(event, (MappingStartEvent, SequenceStartEvent)):
                depth += 1
                if depth > MAX_YAML_DEPTH:
                    fail(f"{path}: YAML exceeds the {MAX_YAML_DEPTH}-level depth limit")
            elif isinstance(event, (MappingEndEvent, SequenceEndEvent)):
                depth -= 1
            elif isinstance(event, AliasEvent):
                aliases += 1
                if aliases > MAX_YAML_ALIASES:
                    fail(f"{path}: YAML exceeds the {MAX_YAML_ALIASES}-alias limit")
            elif getattr(event, "value", None) is not None:
                if len(event.value.encode("utf-8")) > MAX_SCALAR_BYTES:
                    fail(f"{path}: YAML scalar exceeds the {MAX_SCALAR_BYTES}-byte limit")
        return yaml.safe_load(text)
    except ValueError:
        raise
    except Exception as exc:  # pragma: no cover - error message is the contract
        fail(f"{path}: invalid or resource-limited YAML ({type(exc).__name__})")


def configure_resource_limits() -> None:
    """Bound parser CPU and address space in the validator process."""
    if resource is None:
        return
    resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS + 5))
    try:
        resource.setrlimit(
            resource.RLIMIT_AS, (MAX_ADDRESS_SPACE, MAX_ADDRESS_SPACE)
        )
    except (ValueError, OSError):
        if sys.platform != "darwin":
            raise


def validate_evidence_policy(policy: dict[str, Any], source: str = "evidence policy") -> None:
    required = {
        "evidence_policy_version",
        "classification",
        "contains_sensitive_data",
        "redaction",
        "secret_scan",
        "access",
        "retention",
        "telemetry",
    }
    missing = required - policy.keys()
    if missing:
        fail(f"{source}: missing evidence policy fields: {sorted(missing)}")
    if policy["classification"] not in {
        "public",
        "internal",
        "confidential",
        "restricted",
    }:
        fail(f"{source}: invalid classification")
    redaction = policy["redaction"]
    scan = policy["secret_scan"]
    access = policy["access"]
    retention = policy["retention"]
    telemetry = policy["telemetry"]
    if not isinstance(redaction, dict) or not isinstance(scan, dict):
        fail(f"{source}: redaction and secret_scan must be mappings")
    if not isinstance(access, dict) or not isinstance(retention, dict):
        fail(f"{source}: access and retention must be mappings")
    if not isinstance(telemetry, dict):
        fail(f"{source}: telemetry must be a mapping")
    if redaction.get("required") is not True or redaction.get("performed") is not True:
        fail(f"{source}: evidence redaction is incomplete")
    if not redaction.get("reviewer") or not redaction.get("method"):
        fail(f"{source}: evidence redaction reviewer and method are required")
    if scan.get("required") is not True or scan.get("result") != "pass":
        fail(f"{source}: evidence secret scan did not pass")
    if not scan.get("tool"):
        fail(f"{source}: evidence secret scan tool is required")
    if not isinstance(access.get("allowed_roles"), list):
        fail(f"{source}: evidence access roles must be a list")
    if access.get("storage") not in {
        "repository",
        "encrypted_archive",
        "restricted_store",
    }:
        fail(f"{source}: invalid evidence storage")
    if not isinstance(access.get("encryption_at_rest"), bool) or not isinstance(
        access.get("encryption_in_transit"), bool
    ):
        fail(f"{source}: evidence encryption flags must be boolean")
    if retention.get("class") not in {"standard", "extended", "archive"}:
        fail(f"{source}: invalid evidence retention class")
    if policy["classification"] in {"confidential", "restricted"}:
        if access.get("storage") not in {"encrypted_archive", "restricted_store"}:
            fail(f"{source}: sensitive evidence requires encrypted storage")
        if access.get("encryption_at_rest") is not True:
            fail(f"{source}: sensitive evidence requires encryption at rest")
    if telemetry.get("raw_content_allowed") is not False:
        fail(f"{source}: raw telemetry content must be denied")


def validate_security_semantics(packet: dict[str, Any]) -> None:
    """Enforce security controls from packet metadata, not task identifiers."""
    scope = packet.get("scope", {}).get("in", [])
    security_surface = any(
        path_matches(str(candidate), pattern)
        for candidate in scope
        for pattern in SECURITY_SCOPE_PATTERNS
    )
    trigger = (
        packet.get("domain") == "security"
        or packet.get("risk_tier") in {"high", "critical"}
        or bool(packet.get("external_effects"))
        or any(
            str(capability).startswith(
                ("network:", "external:", "secrets:", "destructive:")
            )
            for capability in packet.get("capabilities", [])
        )
        or ("packet_class" in packet and security_surface)
    )
    if not trigger:
        return
    required = {"actor", "capabilities", "risk_tier", "approval_policy", "external_effects"}
    missing = required - packet.keys()
    if missing:
        fail(f"{packet['packet_id']}: missing security fields: {sorted(missing)}")
    if packet["risk_tier"] not in {"low", "medium", "high", "critical"}:
        fail(f"{packet['packet_id']}: invalid risk tier")
    if packet["approval_policy"] not in {"automatic", "reviewer", "user", "two_person"}:
        fail(f"{packet['packet_id']}: invalid approval policy")
    if not isinstance(packet["actor"], dict) or not {
        "agent_id",
        "harness",
        "model",
        "session_id",
    } <= packet["actor"].keys():
        fail(f"{packet['packet_id']}: actor identity is incomplete")
    if not isinstance(packet["capabilities"], list):
        fail(f"{packet['packet_id']}: capabilities must be a list")
    excessive = FORBIDDEN_CAPABILITIES.intersection(packet["capabilities"])
    if excessive:
        fail(f"{packet['packet_id']}: forbidden capabilities: {sorted(excessive)}")
    if packet["risk_tier"] in {"high", "critical"} and packet["approval_policy"] == "automatic":
        fail(f"{packet['packet_id']}: high-risk work cannot use automatic approval")
    for effect in packet["external_effects"]:
        # Completed records from before structured external effects were
        # introduced remain readable until an explicit migration packet
        # updates them. New classified packets must use structured effects.
        if packet["state"] == "Complete" and "packet_class" not in packet:
            continue
        if not isinstance(effect, dict):
            fail(f"{packet['packet_id']}: external effects must be structured")
        required_effect = {
            "effect_id",
            "target",
            "operation",
            "data_classification",
            "approval_ref",
            "rollback",
        }
        missing_effect = required_effect - effect.keys()
        if missing_effect:
            fail(
                f"{packet['packet_id']}: external effect missing fields: "
                f"{sorted(missing_effect)}"
            )
        if not effect.get("declared") or not effect.get("approval_ref"):
            fail(f"{packet['packet_id']}: external effect is missing declaration or approval")
        if effect.get("reversible") is not True:
            fail(f"{packet['packet_id']}: external effect must be reversible or separately approved")
    if packet["state"] != "Complete" and packet["risk_tier"] in {"high", "critical"}:
        for name in EXECUTION_CONTROL_REFS:
            value = packet.get(name)
            if not value:
                fail(f"{packet['packet_id']}: missing applicable control reference {name}")
    if "evidence_policy" in packet:
        policy = packet["evidence_policy"]
        if not isinstance(policy, dict):
            fail(f"{packet['packet_id']}: evidence_policy must be a mapping")
        validate_evidence_policy(policy, packet["packet_id"])


def path_matches(candidate: str, rule: str) -> bool:
    candidate = candidate.rstrip("/")
    rule = rule.rstrip("/")
    return candidate == rule or candidate.startswith(rule + "/")


def validate_acceptance_contract(path: Path, packet: dict[str, Any]) -> None:
    """Enforce structured acceptance contracts when present.

    Historical packets may use only the legacy ``acceptance_criteria`` list.
    New packets SHOULD provide ``acceptance_contract`` with structured
    criteria. When present, the contract is validated for completeness.
    """
    contract = packet.get("acceptance_contract")
    if contract is None:
        return
    if not isinstance(contract, dict):
        fail(f"{path}: acceptance_contract must be a mapping")
    if contract.get("version") != 1:
        fail(f"{path}: acceptance_contract.version must be 1")
    criteria = contract.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        fail(f"{path}: acceptance_contract.criteria must be a non-empty list")
    seen_ids: set[str] = set()
    for item in criteria:
        if not isinstance(item, dict):
            fail(f"{path}: acceptance_contract criterion must be a mapping")
        criterion_id = item.get("id", "")
        if not ACCEPTANCE_CRITERION_ID.fullmatch(str(criterion_id)):
            fail(f"{path}: invalid acceptance criterion id: {criterion_id}")
        if criterion_id in seen_ids:
            fail(f"{path}: duplicate acceptance criterion id: {criterion_id}")
        seen_ids.add(criterion_id)
        for field in ("statement", "expected_result", "verification_method"):
            val = item.get(field, "")
            if not isinstance(val, str) or not val.strip():
                fail(f"{path}: acceptance criterion {criterion_id} missing {field}")
        evidence_refs = item.get("evidence_refs", [])
        if not isinstance(evidence_refs, list):
            fail(f"{path}: acceptance criterion {criterion_id} evidence_refs must be a list")
        if packet.get("state") == "Complete" and not evidence_refs:
            fail(f"{path}: acceptance criterion {criterion_id} must have evidence_refs before Complete")
        for ref in evidence_refs:
            if not isinstance(ref, str) or not ref.strip():
                fail(f"{path}: acceptance criterion {criterion_id} has empty evidence ref")
    # If validation_ref is present, it must match a validation_plan id.
    validation_ids = {
        vp.get("id", "")
        for vp in packet.get("validation_plan", [])
        if isinstance(vp, dict) and VALIDATION_PLAN_ID.fullmatch(str(vp.get("id", "")))
    }
    for item in criteria:
        vref = item.get("validation_ref")
        if vref and vref not in validation_ids:
            fail(f"{path}: acceptance criterion {item['id']} references unknown validation {vref}")


def validate_work_metadata(path: Path, packet: dict[str, Any]) -> None:
    """Validate optional metadata used by new acceptance-first packets."""
    work_type = packet.get("work_type")
    if work_type is not None and work_type not in WORK_TYPES:
        fail(f"{path}: invalid work_type {work_type!r}")
    priority = packet.get("priority")
    if priority is not None and priority not in PRIORITIES:
        fail(f"{path}: invalid priority {priority!r}")
    parent_task_id = packet.get("parent_task_id")
    if parent_task_id is not None and (
        not isinstance(parent_task_id, str) or not TASK_ID.fullmatch(parent_task_id)
    ):
        fail(f"{path}: parent_task_id must be a valid task identifier")
    iteration = packet.get("iteration")
    if iteration is not None and (not isinstance(iteration, str) or not iteration.strip()):
        fail(f"{path}: iteration must be a non-empty string when provided")


def validate_open_questions(path: Path, packet: dict[str, Any]) -> None:
    """Validate criterion-linked unknowns and block only unresolved blockers."""
    questions = packet.get("open_questions", [])
    if not isinstance(questions, list):
        fail(f"{path}: open_questions must be a list")
    criteria = {
        item.get("id")
        for item in packet.get("acceptance_contract", {}).get("criteria", [])
        if isinstance(item, dict)
    }
    for question in questions:
        if isinstance(question, str):
            # Legacy packets use free-form questions and are migrated separately.
            continue
        if not isinstance(question, dict):
            fail(f"{path}: each open question must be a mapping")
        question_id = question.get("id", "")
        if not OPEN_QUESTION_ID.fullmatch(str(question_id)):
            fail(f"{path}: invalid open question id: {question_id}")
        if not isinstance(question.get("question"), str) or not question["question"].strip():
            fail(f"{path}: open question {question_id} is missing question")
        affects = question.get("affects_criteria", [])
        if not isinstance(affects, list) or not affects:
            fail(f"{path}: open question {question_id} must affect at least one criterion")
        unknown_criteria = set(affects) - criteria
        if unknown_criteria:
            fail(
                f"{path}: open question {question_id} references unknown criteria "
                f"{sorted(unknown_criteria)}"
            )
        if not isinstance(question.get("owner"), str) or not question["owner"].strip():
            fail(f"{path}: open question {question_id} is missing owner")
        disposition = question.get("disposition")
        if disposition not in QUESTION_DISPOSITIONS:
            fail(f"{path}: open question {question_id} has invalid disposition")
        if disposition in {"resolved", "bounded"} and not question.get("resolution_ref"):
            fail(f"{path}: open question {question_id} needs resolution_ref")
        if packet.get("state") == "Ready" and disposition == "blocking":
            fail(f"{path}: blocking open question {question_id} prevents Ready")


def validate_planning_records(
    root: Path, packets: dict[str, dict[str, Any]]
) -> None:
    """Validate optional epic/task planning records and their references."""
    epics_dir = root / "epics"
    tasks_dir = root / "tasks"
    epics: dict[str, dict[str, Any]] = {}
    tasks: dict[str, dict[str, Any]] = {}
    for path in sorted(epics_dir.glob("*.yaml")) if epics_dir.is_dir() else []:
        value = load_yaml(path)
        if not isinstance(value, dict):
            fail(f"{path}: epic must be a mapping")
        epic_id = value.get("epic_id")
        if not isinstance(epic_id, str) or not EPIC_ID.fullmatch(epic_id):
            fail(f"{path}: invalid epic_id")
        if path.stem != epic_id or epic_id in epics:
            fail(f"{path}: epic_id does not match filename or is duplicated")
        if value.get("priority") not in PRIORITIES:
            fail(f"{path}: invalid priority")
        if value.get("status") not in {"proposed", "active", "paused", "closed"}:
            fail(f"{path}: invalid status")
        if not isinstance(value.get("task_refs", []), list):
            fail(f"{path}: task_refs must be a list")
        epics[epic_id] = value
    for path in sorted(tasks_dir.glob("*.yaml")) if tasks_dir.is_dir() else []:
        value = load_yaml(path)
        if not isinstance(value, dict):
            fail(f"{path}: task must be a mapping")
        task_id = value.get("task_id")
        if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
            fail(f"{path}: invalid task_id")
        if path.stem != task_id or task_id in tasks:
            fail(f"{path}: task_id does not match filename or is duplicated")
        if value.get("priority") not in PRIORITIES:
            fail(f"{path}: invalid priority")
        if value.get("status") not in {"proposed", "in_progress", "blocked", "done", "deferred"}:
            fail(f"{path}: invalid status")
        epic_id = value.get("epic_id")
        if epic_id is not None and epic_id not in epics:
            fail(f"{path}: unknown epic_id {epic_id}")
        for packet_id in value.get("packet_refs", []):
            if packet_id not in packets:
                fail(f"{path}: unknown packet reference {packet_id}")
        tasks[task_id] = value
    for epic_id, epic in epics.items():
        for task_id in epic.get("task_refs", []):
            if task_id not in tasks:
                fail(f"{epic_id}: unknown task reference {task_id}")


def validate_packet(path: Path, packet: dict[str, Any], packets: dict[str, dict[str, Any]]) -> None:
    required = {
        "packet_id",
        "task_id",
        "phase",
        "domain",
        "title",
        "objective",
        "scope",
        "owner",
        "reviewer",
        "cleanup_owner",
        "dependencies",
        "locks",
        "baseline_refs",
        "acceptance_criteria",
        "validation_plan",
        "state",
    }
    missing = required - packet.keys()
    if missing:
        fail(f"{path}: missing required fields: {sorted(missing)}")
    packet_id = packet["packet_id"]
    if path.stem != packet_id or not PACKET_ID.fullmatch(packet_id):
        fail(f"{path}: packet_id does not match filename or identifier contract")
    if packet["domain"] not in DOMAINS:
        fail(f"{path}: invalid domain")
    if "packet_class" in packet and packet["packet_class"] not in PACKET_CLASSES:
        fail(f"{path}: invalid packet class")
    if packet["state"] not in STATES:
        fail(f"{path}: invalid state {packet['state']}")
    if packet["state"] in {"Claimed", "Implementing", "Validation", "Handoff"}:
        if packet["owner"] in {"", "unassigned"} or not packet["claim_timestamp"]:
            fail(f"{path}: active packet must have an owner and claim timestamp")
    if packet["state"] == "Complete":
        if packet["locks"]:
            fail(f"{path}: complete packet must release all locks")
        if not packet.get("handoff_ref"):
            fail(f"{path}: complete packet must reference a handoff")
    if not packet["scope"].get("in") or "out" not in packet["scope"]:
        fail(f"{path}: scope.in and scope.out are required and scope.in cannot be empty")
    if not packet["acceptance_criteria"] or not packet["validation_plan"]:
        fail(f"{path}: acceptance_criteria and validation_plan cannot be empty")
    if ".contract-engineering/protocol.lock.yaml" not in packet["baseline_refs"]:
        fail(f"{path}: missing protocol lock baseline")
    revisions = [ref for ref in packet["baseline_refs"] if BASE_REVISION.fullmatch(str(ref))]
    if not revisions:
        fail(f"{path}: missing 40-character base revision")
    for dependency in packet["dependencies"]:
        if dependency not in packets:
            fail(f"{path}: missing dependency {dependency}")
    if len(packet["locks"]) != len(set(packet["locks"])):
        fail(f"{path}: duplicate lock")
    validate_security_semantics(packet)
    validate_work_metadata(path, packet)
    validate_acceptance_contract(path, packet)
    validate_open_questions(path, packet)


ARCHIVE_PACKET_DIR = "archive/work-packets"
ARCHIVE_TRACKER = "archive/execution-tracker-archive.md"
TRACKER_SHARD_DIR = "tracker-shards"
MAX_INDEX_PACKET_ROWS = 25
MAX_SHARD_PACKET_ROWS = 50
TERMINAL_STATES = {"Complete", "Cancelled"}
TRACKER_ROW_RE = re.compile(
    rf"^\| ([^|]+) \| ({identifiers.PACKET_PATTERN[1:-1]}) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$",
    re.MULTILINE,
)


def is_task_or_packet_identifier(value: object) -> bool:
    return identifiers.is_task_or_packet_identifier(value)


def _parse_tracker_rows(text: str) -> list[tuple[str, str, str, str, str, str]]:
    return TRACKER_ROW_RE.findall(text)


def _check_row_consistency(
    label: str, rows: list[tuple[str, str, str, str, str, str]], packets: dict[str, dict[str, Any]]
) -> set[str]:
    """Return the set of packet IDs seen in the given tracker rows.

    Enforces no duplicate rows and that rows for known packets match state,
    owner, and reviewer. Orphan rows (no matching packet file) are reported by
    the caller, not here, because a row is only an orphan relative to its
    expected partition.
    """
    seen: set[str] = set()
    for _, packet_id, state, owner, reviewer, _ in rows:
        if packet_id in seen:
            fail(f"{label}: duplicate packet row {packet_id}")
        seen.add(packet_id)
        if packet_id in packets:
            packet = packets[packet_id]
            if state.strip() != packet["state"]:
                fail(f"{label}: state mismatch for {packet_id}")
            if owner.strip() != str(packet["owner"]):
                fail(f"{label}: owner mismatch for {packet_id}")
            if reviewer.strip() != str(packet["reviewer"]):
                fail(f"{label}: reviewer mismatch for {packet_id}")
    return seen


def validate_tracker(
    root: Path,
    live_packets: dict[str, dict[str, Any]],
    archive_packets: dict[str, dict[str, Any]],
) -> None:
    if (root / "tracker/index.yaml").is_file():
        return
    all_packets = {**live_packets, **archive_packets}
    live_tracker_path = root / "execution-tracker.md"
    if not live_tracker_path.is_file():
        fail("tracker: execution-tracker.md is missing")
    live_rows = _parse_tracker_rows(live_tracker_path.read_text())
    if len(live_rows) > MAX_INDEX_PACKET_ROWS:
        fail(
            f"tracker: active index has {len(live_rows)} packet rows; "
            f"move task rows into {TRACKER_SHARD_DIR}/"
        )
    live_seen = _check_row_consistency("tracker", live_rows, all_packets)
    shard_dir = root / TRACKER_SHARD_DIR
    if shard_dir.exists() and not shard_dir.is_dir():
        fail(f"tracker: {TRACKER_SHARD_DIR} is not a directory")
    shard_paths = sorted(shard_dir.glob("*.md")) if shard_dir.is_dir() else []
    for shard_path in shard_paths:
        shard_rows = _parse_tracker_rows(shard_path.read_text())
        if len(shard_rows) > MAX_SHARD_PACKET_ROWS:
            fail(
                f"tracker shard {shard_path.name}: has {len(shard_rows)} packet rows; "
                f"split the task shard before adding more work"
            )
        for task, packet_id, *_ in shard_rows:
            if not task.strip() or not shard_path.stem.startswith(task.strip()):
                fail(
                    f"tracker shard {shard_path.name}: row {packet_id} "
                    f"does not belong to task {task.strip()}"
                )
        shard_seen = _check_row_consistency(
            f"tracker shard {shard_path.name}", shard_rows, all_packets
        )
        duplicate = live_seen & shard_seen
        if duplicate:
            fail(f"tracker: packets in index and shard {sorted(duplicate)}")
        live_seen |= shard_seen

    archive_seen: set[str] = set()
    archive_tracker_path = root / ARCHIVE_TRACKER
    if archive_tracker_path.is_file():
        archive_rows = _parse_tracker_rows(archive_tracker_path.read_text())
        archive_seen = _check_row_consistency(
            "archive-tracker", archive_rows, all_packets
        )
    elif (root / ARCHIVE_PACKET_DIR).is_dir():
        fail(f"tracker: {ARCHIVE_PACKET_DIR} exists but {ARCHIVE_TRACKER} is missing")

    # Every packet must appear in exactly one tracker, in the right partition.
    live_missing = set(live_packets) - live_seen
    if live_missing:
        fail(f"tracker: missing live packet rows {sorted(live_missing)}")
    archive_missing = set(archive_packets) - archive_seen
    if archive_missing:
        fail(f"tracker: missing archive packet rows {sorted(archive_missing)}")

    cross_partition = live_seen & archive_seen
    if cross_partition:
        fail(f"tracker: packets in both trackers {sorted(cross_partition)}")

    # Rows must resolve to a packet file in the matching partition.
    live_orphans = live_seen - set(live_packets)
    if live_orphans:
        fail(f"tracker: orphan rows with no live packet file {sorted(live_orphans)}")
    archive_orphans = archive_seen - set(archive_packets)
    if archive_orphans:
        fail(f"tracker: orphan rows with no archive packet file {sorted(archive_orphans)}")

    # Archived packets must be terminal state.
    for packet_id, packet in archive_packets.items():
        if packet["state"] not in TERMINAL_STATES:
            fail(f"archive-tracker: {packet_id} is not terminal ({packet['state']})")
        if packet["state"] == "Complete" and not packet.get("handoff_ref"):
            fail(f"archive-tracker: {packet_id} Complete without handoff_ref")


def validate_project_lock(root: Path) -> None:
    lock_path = root / "protocol.lock.yaml"
    lock = load_yaml(lock_path)
    if not isinstance(lock, dict) or lock.get("lock_version") != 1:
        fail(f"{lock_path}: unsupported lock schema")
    protocol = lock.get("protocol", {})
    if not BASE_REVISION.fullmatch(str(protocol.get("ref", ""))):
        fail(f"{lock_path}: protocol.ref must be an immutable commit SHA")
    if not protocol.get("repository") or not protocol.get("release"):
        fail(f"{lock_path}: protocol repository and release are required")
    skills = lock.get("skills", {})
    required = {
        "phased-engineering-execution",
        "cleanup-protocol",
        "project-lifecycle",
        "skill-evolution",
        "coding-principles",
        "security-assurance",
    }
    if set(skills) != required:
        fail(f"{lock_path}: lock must contain exactly the governed skills")
    for name, pin in skills.items():
        if not pin.get("version") or not SHA256.fullmatch(str(pin.get("sha256", ""))):
            fail(f"{lock_path}: invalid pin for {name}")
    if not lock.get("project", {}).get("protocol_root"):
        fail(f"{lock_path}: project.protocol_root is required")


def validate_locks(packets: dict[str, dict[str, Any]]) -> None:
    active = {
        packet_id: packet
        for packet_id, packet in packets.items()
        if packet["state"] not in {"Planned", "Complete", "Cancelled"}
    }
    resources: dict[str, str] = {}
    for packet_id, packet in active.items():
        for lock in packet["locks"]:
            if lock in resources:
                fail(f"locks: {lock} claimed by both {resources[lock]} and {packet_id}")
            resources[lock] = packet_id


def validate_dependency_graph(packets: dict[str, dict[str, Any]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(packet_id: str) -> None:
        if packet_id in visiting:
            fail(f"dependencies: cycle detected at {packet_id}")
        if packet_id in visited:
            return
        visiting.add(packet_id)
        for dependency in packets[packet_id]["dependencies"]:
            visit(dependency)
        visiting.remove(packet_id)
        visited.add(packet_id)

    for packet_id in packets:
        visit(packet_id)


def validate_references(root: Path, packets: dict[str, dict[str, Any]]) -> None:
    evidence_dir = root / "evidence"
    handoff_dir = root / "handoffs"
    for packet_id, packet in packets.items():
        for evidence_ref in packet.get("evidence_refs", []):
            path = evidence_dir / f"{evidence_ref}.md"
            if not path.is_file():
                fail(f"{packet_id}: missing evidence {evidence_ref}")
        handoff_ref = packet.get("handoff_ref")
        if handoff_ref and not (handoff_dir / f"{handoff_ref}.yaml").is_file():
            fail(f"{packet_id}: missing handoff {handoff_ref}")
    for path in sorted(handoff_dir.glob("*.yaml")):
        handoff = load_yaml(path)
        required = {"handoff_id", "packet_id", "sender", "receiver", "receiver_status"}
        if not isinstance(handoff, dict) or not required <= handoff.keys():
            fail(f"{path}: incomplete handoff")
        if handoff["handoff_id"] != path.stem:
            fail(f"{path}: handoff_id does not match filename")
        if handoff["packet_id"] not in packets:
            fail(f"{path}: unknown packet reference")
        if handoff["receiver_status"] not in {"pending", "accepted", "rejected"}:
            fail(f"{path}: invalid receiver status")
        if handoff["receiver_status"] == "accepted" and not handoff.get("receiver_notes"):
            fail(f"{path}: accepted handoff requires receiver notes")
    for path in sorted(evidence_dir.glob("*.md")):
        if not path.read_text().startswith(f"# {path.stem}"):
            fail(f"{path}: evidence heading must match filename")


def enforce_scope(packet: dict[str, Any], changed_paths: list[str]) -> None:
    included = packet["scope"]["in"]
    excluded = packet["scope"]["out"]
    for changed in changed_paths:
        if any(path_matches(changed, rule) for rule in excluded):
            fail(f"{packet['packet_id']}: changed path is explicitly out of scope: {changed}")
        if not any(path_matches(changed, rule) for rule in included):
            fail(f"{packet['packet_id']}: changed path is outside scope.in: {changed}")


def validate_canonical_tracker(root: Path) -> None:
    if not (root / "tracker/index.yaml").is_file():
        return
    script = Path(__file__).with_name("validate-tracker.py")
    spec = importlib.util.spec_from_file_location("validate_tracker", script)
    if spec is None or spec.loader is None:
        fail(f"{script}: cannot load canonical tracker validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate(root)
    render_script = Path(__file__).with_name("render-tracker.py")
    render_spec = importlib.util.spec_from_file_location("render_tracker", render_script)
    if render_spec is None or render_spec.loader is None:
        fail(f"{render_script}: cannot load tracker renderer")
    renderer = importlib.util.module_from_spec(render_spec)
    render_spec.loader.exec_module(renderer)
    renderer.render_projections(root, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, help="explicit project protocol root")
    parser.add_argument("--project-dir", default=".", type=Path)
    parser.add_argument("--mode", choices=("off", "advisory", "enforced"))
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--changed-path", action="append", default=[])
    args = parser.parse_args()
    result = run_validation(
        args.project_dir,
        explicit_root=args.root,
        mode=args.mode,
        packet_path=args.packet,
        changed_paths=args.changed_path,
    )
    for message in result.messages:
        print(f"contract validation advisory: {message}", file=sys.stderr)
    if result.skipped:
        print("contract validation skipped (mode=off)")
    elif result.valid:
        print(f"contract validation valid (mode={result.mode})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"contract validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
