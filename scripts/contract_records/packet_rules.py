"""Per-packet validation rules: acceptance, metadata, owner, planning."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import (
    ACCEPTANCE_CRITERION_ID,
    BASE_REVISION,
    DOMAINS,
    EPIC_ID,
    OPEN_QUESTION_ID,
    PACKET_CLASSES,
    PACKET_ID,
    PRIORITIES,
    QUESTION_DISPOSITIONS,
    STATES,
    TASK_ID,
    VALIDATION_PLAN_ID,
    WORK_TYPES,
)
from .loaders import fail, load_yaml
from .security import validate_security_semantics


def validate_acceptance_contract(path: Path, packet: dict[str, Any]) -> None:
    """Enforce structured acceptance contracts when present.

    Historical packets may use only the legacy acceptance_criteria list.
    New packets SHOULD provide acceptance_contract with structured
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


def validate_owner(packet: dict[str, Any], path: Path) -> None:
    """Enforce human-signed owner for new (non-terminal) packets.

    Legacy packets with bare string owners remain valid only when terminal.
    New packets must have a structured owner with identity_type=human,
    authentication_ref, and signed_at. The owner identity must not match
    the implementor agent_id.
    """
    owner = packet.get("owner")
    state = packet.get("state", "")
    terminal = state in {"Complete", "Cancelled"}
    if isinstance(owner, str):
        if not terminal and owner in {"", "unassigned"}:
            fail(f"{path}: active packet must have an owner")
        if not terminal:
            fail(f"{path}: non-terminal packet must have a structured human owner, not a bare string")
        return
    if not isinstance(owner, dict):
        fail(f"{path}: owner must be a structured object or a legacy string")
        return
    if terminal:
        return
    required = {"identity", "identity_type", "authentication_ref", "signed_at"}
    missing = required - owner.keys()
    if missing:
        fail(f"{path}: owner missing required fields: {sorted(missing)}")
    if owner.get("identity_type") != "human":
        fail(f"{path}: owner.identity_type must be 'human'")
    if not owner.get("authentication_ref"):
        fail(f"{path}: owner.authentication_ref is required for new packets")
    if not owner.get("signed_at"):
        fail(f"{path}: owner.signed_at is required for new packets")
    implementor = packet.get("implementor") or packet.get("actor")
    if implementor and owner.get("identity") == implementor.get("agent_id"):
        fail(f"{path}: owner identity must not match implementor agent_id")


def validate_packet(path: Path, packet: dict[str, Any], packets: dict[str, dict[str, Any]]) -> None:
    required = {
        "packet_id", "task_id", "phase", "domain", "title", "objective",
        "scope", "owner", "reviewer", "cleanup_owner", "dependencies",
        "locks", "baseline_refs", "acceptance_criteria", "validation_plan",
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
        owner = packet["owner"]
        owner_str = owner if isinstance(owner, str) else owner.get("identity", "")
        if owner_str in {"", "unassigned"} or not packet.get("claim_timestamp"):
            fail(f"{path}: active packet must have an owner and claim timestamp")
    validate_owner(packet, path)
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
