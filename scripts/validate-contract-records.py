#!/usr/bin/env python3
"""Validate Contract Engineering records and optionally enforce packet scope."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml
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
DOMAINS = {"coding", "browser", "design", "data", "documentation"}
SEMANTIC_SCOPES = {"none", "affected", "defined"}
SEMANTIC_STATUSES = {"draft", "proposed", "approved", "superseded", "deprecated"}
SEMANTIC_MATURITIES = {"fuzzy", "emerging", "structured", "stable", "deprecated"}
SEMANTIC_PROFILES = {"architecture", "api", "event", "data", "workflow", "ui", "agent"}
PACKET_ID = re.compile(r"^[A-Z0-9-]+-T\d{3}-P\d{3}$")
SEMANTIC_CONTRACT_ID = re.compile(r"^[A-Z0-9-]+-SC\d{3}$")
BASE_REVISION = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_YAML_BYTES = 1 * 1024 * 1024
MAX_SCALAR_BYTES = 256 * 1024
MAX_YAML_NODES = 10_000
MAX_YAML_DEPTH = 64
MAX_YAML_ALIASES = 50
MAX_CPU_SECONDS = 10
MAX_ADDRESS_SPACE = 512 * 1024 * 1024
SECURITY_PACKET_TASK = "CENG-T005"
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
    telemetry = policy["telemetry"]
    if redaction.get("required") is not True or redaction.get("performed") is not True:
        fail(f"{source}: evidence redaction is incomplete")
    if scan.get("required") is not True or scan.get("result") != "pass":
        fail(f"{source}: evidence secret scan did not pass")
    if policy["classification"] in {"confidential", "restricted"}:
        if access.get("storage") not in {"encrypted_archive", "restricted_store"}:
            fail(f"{source}: sensitive evidence requires encrypted storage")
        if access.get("encryption_at_rest") is not True:
            fail(f"{source}: sensitive evidence requires encryption at rest")
    if telemetry.get("raw_content_allowed") is not False:
        fail(f"{source}: raw telemetry content must be denied")


def validate_security_semantics(packet: dict[str, Any]) -> None:
    """Enforce security controls for newly introduced security packets."""
    if packet.get("task_id") != SECURITY_PACKET_TASK:
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
        if not isinstance(effect, dict):
            fail(f"{packet['packet_id']}: external effects must be structured")
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


def validate_semantic_contract(path: Path, contract: dict[str, Any]) -> None:
    """Validate the portable shape of a semantic contract without judging domain meaning."""
    required = {
        "contract_id",
        "contract_version",
        "status",
        "maturity",
        "title",
        "purpose",
        "scope",
        "vocabulary",
        "concepts",
        "invariants",
        "boundaries",
        "failure_semantics",
        "temporal_semantics",
        "examples",
        "counterexamples",
        "compatibility",
        "profiles",
        "open_questions",
        "change_log",
        "owners",
        "review",
        "evidence_refs",
        "rollback",
    }
    missing = required - contract.keys()
    if missing:
        fail(f"{path}: missing semantic contract fields: {sorted(missing)}")
    contract_id = contract["contract_id"]
    if path.stem != contract_id or not SEMANTIC_CONTRACT_ID.fullmatch(str(contract_id)):
        fail(f"{path}: semantic contract ID does not match filename or identifier contract")
    if not isinstance(contract["status"], str) or contract["status"] not in SEMANTIC_STATUSES:
        fail(f"{path}: invalid semantic contract status")
    if not isinstance(contract["maturity"], str) or contract["maturity"] not in SEMANTIC_MATURITIES:
        fail(f"{path}: invalid semantic contract maturity")
    if (
        not isinstance(contract["scope"], dict)
        or not isinstance(contract["scope"].get("in"), list)
        or not contract["scope"]["in"]
        or not isinstance(contract["scope"].get("out"), list)
    ):
        fail(f"{path}: semantic contract scope.in and scope.out are required")
    for name in ("vocabulary", "invariants", "boundaries", "failure_semantics", "examples", "counterexamples", "change_log", "owners"):
        value = contract[name]
        if not isinstance(value, list) or not value:
            fail(f"{path}: semantic contract {name} must be a non-empty list")
    item_requirements = {
        "vocabulary": ("term", "meaning"),
        "invariants": ("id", "statement"),
        "boundaries": ("name", "meaning", "inputs", "outputs", "failure_semantics"),
        "failure_semantics": ("id", "condition", "behavior", "recovery"),
        "examples": ("name", "scenario", "expected", "prohibited"),
        "counterexamples": ("name", "scenario", "lesson"),
        "change_log": ("version", "date", "change", "reason", "approved_by"),
    }
    for name, fields in item_requirements.items():
        for item in contract[name]:
            if not isinstance(item, dict) or not all(
                isinstance(item.get(field), str) and item[field]
                if field not in {"inputs", "outputs"}
                else isinstance(item.get(field), list)
                for field in fields
            ):
                fail(f"{path}: semantic contract {name} contains an incomplete item")
    if not all(isinstance(owner, str) and owner for owner in contract["owners"]):
        fail(f"{path}: semantic contract owners must be non-empty strings")
    temporal = contract["temporal_semantics"]
    if not isinstance(temporal, dict) or not all(
        isinstance(temporal.get(name), str) for name in ("ordering", "consistency", "idempotency", "freshness")
    ):
        fail(f"{path}: semantic contract temporal_semantics is incomplete")
    compatibility = contract["compatibility"]
    if not isinstance(compatibility, dict) or not all(
        isinstance(compatibility.get(name), str) and compatibility[name]
        for name in ("versioning", "backward_compatibility", "migration", "deprecation")
    ):
        fail(f"{path}: semantic contract compatibility is incomplete")
    profiles = contract["profiles"]
    if (
        not isinstance(profiles, list)
        or not profiles
        or not all(isinstance(profile, str) and profile in SEMANTIC_PROFILES for profile in profiles)
    ):
        fail(f"{path}: semantic contract profiles are invalid")
    questions = contract["open_questions"]
    if not isinstance(questions, list):
        fail(f"{path}: semantic contract open_questions must be a list")
    for question in questions:
        if not isinstance(question, dict) or not all(
            isinstance(question.get(field), str) and question[field]
            for field in ("id", "question", "owner")
        ) or not isinstance(question.get("status"), str) or question["status"] not in {
            "open",
            "answered",
            "deferred",
            "rejected",
        }:
            fail(f"{path}: semantic contract open_questions contains an incomplete item")
    review = contract["review"]
    if (
        not isinstance(review, dict)
        or not isinstance(review.get("status"), str)
        or review["status"] not in {"pending", "approved", "rejected"}
    ):
        fail(f"{path}: semantic contract review is invalid")
    if contract["status"] == "approved" and review.get("status") != "approved":
        fail(f"{path}: approved semantic contract requires approved review")


def load_semantic_contracts(root: Path) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    directory = root / "semantic-contracts"
    if not directory.is_dir():
        return contracts
    for path in sorted(directory.glob("*.yaml")):
        contract = load_yaml(path)
        if not isinstance(contract, dict) or "contract_id" not in contract:
            fail(f"{path}: semantic contract must be a YAML mapping with contract_id")
        contract_id = contract["contract_id"]
        if contract_id in contracts:
            fail(f"duplicate semantic contract ID {contract_id}")
        validate_semantic_contract(path, contract)
        contracts[contract_id] = contract
    return contracts


def path_matches(candidate: str, rule: str) -> bool:
    candidate = candidate.rstrip("/")
    rule = rule.rstrip("/")
    return candidate == rule or candidate.startswith(rule + "/")


def validate_packet(
    path: Path,
    packet: dict[str, Any],
    packets: dict[str, dict[str, Any]],
    semantic_contracts: dict[str, dict[str, Any]] | None = None,
) -> None:
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
    semantic_scope = packet.get("semantic_scope")
    if packet["state"] not in {"Complete", "Cancelled"} and semantic_scope is None:
        fail(f"{path}: active packet must declare semantic_scope")
    if semantic_scope is not None:
        if not isinstance(semantic_scope, str) or semantic_scope not in SEMANTIC_SCOPES:
            fail(f"{path}: invalid semantic_scope")
        semantic_ref = packet.get("semantic_contract_ref")
        if semantic_scope == "none":
            if semantic_ref not in {None, ""}:
                fail(f"{path}: semantic_scope none cannot reference a semantic contract")
        elif not semantic_ref:
            fail(f"{path}: semantic-bearing packet must reference a semantic contract")
        elif semantic_contracts is not None and semantic_ref not in semantic_contracts:
            fail(f"{path}: missing semantic contract {semantic_ref}")
        elif (
            semantic_contracts is not None
            and packet["state"] in {"Ready", "Implementing", "Validation", "Rework", "Handoff"}
        ):
            contract = semantic_contracts[semantic_ref]
            if contract["status"] != "approved" or contract["review"]["status"] != "approved":
                fail(f"{path}: semantic-bearing implementation requires an approved semantic contract")
    validate_security_semantics(packet)


def validate_tracker(root: Path, packets: dict[str, dict[str, Any]]) -> None:
    tracker = (root / "execution-tracker.md").read_text()
    rows = re.findall(
        r"^\| ([^|]+) \| ([A-Z0-9-]+-T\d{3}-P\d{3}) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$",
        tracker,
        re.MULTILINE,
    )
    seen: set[str] = set()
    for _, packet_id, state, owner, reviewer, _ in rows:
        if packet_id in seen:
            fail(f"tracker: duplicate packet row {packet_id}")
        seen.add(packet_id)
        if packet_id in packets:
            packet = packets[packet_id]
            if state.strip() != packet["state"]:
                fail(f"tracker: state mismatch for {packet_id}")
            if owner.strip() != str(packet["owner"]):
                fail(f"tracker: owner mismatch for {packet_id}")
            if reviewer.strip() != str(packet["reviewer"]):
                fail(f"tracker: reviewer mismatch for {packet_id}")
    missing = set(packets) - seen
    if missing:
        fail(f"tracker: missing packet rows {sorted(missing)}")


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".contract-engineering", type=Path)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--changed-path", action="append", default=[])
    args = parser.parse_args()
    configure_resource_limits()
    root = args.root
    packet_paths = sorted((root / "work-packets").glob("*.yaml"))
    semantic_contracts = load_semantic_contracts(root)
    packets: dict[str, dict[str, Any]] = {}
    for path in packet_paths:
        packet = load_yaml(path)
        if not isinstance(packet, dict) or "packet_id" not in packet:
            fail(f"{path}: packet must be a YAML mapping with packet_id")
        packet_id = packet["packet_id"]
        if packet_id in packets:
            fail(f"duplicate packet ID {packet_id}")
        packets[packet_id] = packet
    for path in packet_paths:
        validate_packet(path, packets[path.stem], packets, semantic_contracts)
    validate_project_lock(root)
    validate_tracker(root, packets)
    validate_dependency_graph(packets)
    validate_locks(packets)
    validate_references(root, packets)
    if args.packet:
        packet = packets.get(args.packet.stem)
        if packet is None:
            fail(f"unknown packet {args.packet}")
        enforce_scope(packet, args.changed_path)
    print(f"contract records valid: {len(packets)} packets")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"contract validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
