#!/usr/bin/env python3
"""Validate packet admission against design contract requirements."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

DESIGNS_DIR = Path(".contract-engineering") / "designs"
PACKETS_DIR = Path(".contract-engineering") / "work-packets"

SHA256 = re.compile(r"^[0-9a-f]{64}$")
PACKET_ID = re.compile(r"^[A-Z0-9-]+-T\d{3}-P\d{3}$")


def load_yaml(path: Path) -> Any:
    """Load a YAML file."""
    try:
        return yaml.safe_load(path.read_text())
    except Exception as exc:
        raise ValueError(f"{path}: invalid YAML ({type(exc).__name__})")


def load_designs(root: Path = DESIGNS_DIR) -> dict[str, dict[str, Any]]:
    """Load all design contracts."""
    designs = {}
    if not root.exists():
        return designs
    
    for task_dir in sorted(root.iterdir()):
        if not task_dir.is_dir():
            continue
        design_path = task_dir / "design.yaml"
        if design_path.is_file():
            design = load_yaml(design_path)
            task_id = task_dir.name
            designs[task_id] = design
    
    return designs


def load_packets(root: Path = PACKETS_DIR) -> dict[str, dict[str, Any]]:
    """Load all work packets."""
    packets = {}
    if not root.exists():
        return packets
    
    for path in sorted(root.glob("*.yaml")):
        packet = load_yaml(path)
        packet_id = packet.get("packet_id", path.stem)
        packets[packet_id] = packet
    
    return packets


def compute_artifact_hash(artifacts: list[dict[str, Any]]) -> str:
    """Compute SHA-256 hash of artifact manifest."""
    artifact_data = json.dumps(artifacts, sort_keys=True).encode("utf-8")
    return hashlib.sha256(artifact_data).hexdigest()


def path_matches(candidate: str, rule: str) -> bool:
    """Check if a path matches a scope rule."""
    candidate = candidate.rstrip("/")
    rule = rule.rstrip("/")
    return candidate == rule or candidate.startswith(rule + "/")


def validate_design_approval(design: dict[str, Any], packet: dict[str, Any]) -> None:
    """Validate design is approved."""
    if design["status"] != "approved":
        raise ValueError(
            f"{packet['packet_id']}: design {design['design_id']} is not approved (status: {design['status']})"
        )


def validate_approval_revision(design: dict[str, Any], packet: dict[str, Any]) -> None:
    """Validate approval binds to current artifact manifest."""
    approved_revision = design["approval"]["approved_revision"]
    manifest_hash = compute_artifact_hash(design["artifacts"])
    
    if approved_revision != manifest_hash:
        raise ValueError(
            f"{packet['packet_id']}: artifact manifest changed since approval "
            f"(approved: {approved_revision[:16]}..., current: {manifest_hash[:16]}...)"
        )


def validate_required_reviews(design: dict[str, Any], packet: dict[str, Any]) -> None:
    """Validate required reviews are accepted."""
    required_reviews = {
        "text": {"design"},
        "ui": {"design", "visual"},
        "ux": {"design", "visual"},
        "architecture": {"design", "architecture"},
        "workflow": {"design"},
        "data-flow": {"design", "architecture"},
        "mixed": {"design", "architecture", "visual"},
    }
    
    design_type = design["design_type"]
    required = required_reviews.get(design_type, set())
    accepted = {r["kind"] for r in design.get("reviews", []) if r["status"] == "accepted"}
    
    missing = required - accepted
    if missing:
        raise ValueError(
            f"{packet['packet_id']}: missing required reviews for {design_type}: {sorted(missing)}"
        )


def validate_design_reference(packet: dict[str, Any], designs: dict[str, Any]) -> None:
    """Validate packet references a design."""
    design_ref = packet.get("design_decision_ref")
    if not design_ref:
        # Legacy packets without design contracts are allowed
        return
    
    # Find the design by design_id
    found = False
    for task_id, design in designs.items():
        if design.get("design_id") == design_ref:
            found = True
            break
    
    if not found:
        raise ValueError(
            f"{packet['packet_id']}: design_decision_ref {design_ref} not found"
        )


def validate_scope_coverage(design: dict[str, Any], packet: dict[str, Any]) -> None:
    """Validate packet scope is covered by design scope."""
    design_scope_in = set(design["scope"]["in"])
    design_scope_out = set(design["scope"]["out"])
    packet_scope_in = set(packet["scope"]["in"])
    
    # Check packet scope is not explicitly excluded by design
    for path in packet_scope_in:
        for excluded in design_scope_out:
            if path_matches(path, excluded):
                raise ValueError(
                    f"{packet['packet_id']}: packet scope path {path} is excluded by design scope"
                )
    
    # Check packet scope is covered by design scope
    for path in packet_scope_in:
        if not any(path_matches(path, included) for included in design_scope_in):
            raise ValueError(
                f"{packet['packet_id']}: packet scope path {path} is outside design scope"
            )


def validate_criterion_traceability(
    design: dict[str, Any],
    packet: dict[str, Any],
    all_packets: dict[str, Any],
) -> None:
    """Validate packet criteria against design criteria and local validation."""
    design_criteria = {
        c["id"]: c
        for c in design.get("acceptance_contract", {}).get("criteria", [])
    }
    
    packet_contract = packet.get("acceptance_contract", {})
    
    # A packet validation_ref names its own validation plan. Design
    # traceability uses the explicit design_criterion_refs field.
    if packet_contract.get("criteria"):
        for criterion in packet_contract["criteria"]:
            design_refs = criterion.get("design_criterion_refs")
            if not isinstance(design_refs, list) or not design_refs:
                raise ValueError(
                    f"{packet['packet_id']}: criterion {criterion.get('id', 'unknown')} "
                    "must reference at least one design criterion"
                )
            missing = set(design_refs) - set(design_criteria)
            if missing:
                raise ValueError(
                    f"{packet['packet_id']}: criterion {criterion.get('id', 'unknown')} "
                    f"references unknown design criteria: {sorted(missing)}"
                )


def validate_packet_gates(packet: dict[str, Any], all_packets: dict[str, Any]) -> None:
    """Validate packet gates, dependencies, and resources.
    
    - Dependencies must exist and be Complete
    - Active locks must be present and conflict-free/owned
    - Packet must have owner when Ready
    """
    # Check dependencies are satisfied
    dependencies = packet.get("dependencies", [])
    for dep_id in dependencies:
        if dep_id not in all_packets:
            raise ValueError(
                f"{packet['packet_id']}: dependency {dep_id} does not exist"
            )
        dep_packet = all_packets[dep_id]
        if dep_packet["state"] != "Complete":
            raise ValueError(
                f"{packet['packet_id']}: dependency {dep_id} is not Complete (state: {dep_packet['state']})"
            )
    
    # Check locks are held and conflict-free
    locks = packet.get("locks", [])
    if locks and packet["state"] in {"Ready", "Implementing", "Validation", "Handoff"}:
        # Verify no other active packet holds the same lock
        for lock in locks:
            for other_id, other_packet in all_packets.items():
                if other_id == packet["packet_id"]:
                    continue
                if other_packet["state"] not in {"Complete", "Cancelled"}:
                    if lock in other_packet.get("locks", []):
                        raise ValueError(
                            f"{packet['packet_id']}: lock {lock} is also held by active packet {other_id}"
                        )
    
    # Check authorization
    if packet["state"] == "Ready":
        if not packet.get("owner") or packet["owner"] == "unassigned":
            raise ValueError(f"{packet['packet_id']}: packet must have an owner to be Ready")


def validate_admission(packet: dict[str, Any], designs: dict[str, Any], all_packets: dict[str, Any]) -> None:
    """Validate a packet is admissible for implementation."""
    if packet["state"] not in {"Ready", "Implementing", "Validation", "Handoff"}:
        return  # Only validate Ready or active packets
    
    # Design reference check
    validate_design_reference(packet, designs)
    
    # If packet has design reference, validate design contract
    design_ref = packet.get("design_decision_ref")
    if design_ref:
        # Find design by design_id
        design = None
        for task_id, d in designs.items():
            if d.get("design_id") == design_ref:
                design = d
                break
        
        if design:
            validate_design_approval(design, packet)
            validate_approval_revision(design, packet)
            validate_required_reviews(design, packet)
            validate_scope_coverage(design, packet)
            validate_criterion_traceability(design, packet, all_packets)
    
    # Packet gates
    validate_packet_gates(packet, all_packets)


def validate_all_admission(root: Path = Path(".contract-engineering")) -> int:
    """Validate admission for all Ready packets."""
    designs = load_designs(root / "designs")
    packets = load_packets(root / "work-packets")
    
    errors = []
    ready_count = 0
    
    for packet_id, packet in packets.items():
        if packet["state"] == "Ready":
            ready_count += 1
            try:
                validate_admission(packet, designs, packets)
            except ValueError as exc:
                errors.append(str(exc))
    
    if errors:
        for error in errors:
            print(f"admission failed: {error}", file=sys.stderr)
        return 1
    
    print(f"packet admission valid: {ready_count} ready packets")
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Validate packet admission")
    parser.add_argument("--root", type=Path, default=Path(".contract-engineering"), help="Contract engineering root")
    parser.add_argument("--packet", type=Path, help="Validate a specific packet")
    parser.add_argument("--all-ready", action="store_true", help="Validate all Ready packets")
    args = parser.parse_args()
    
    if args.all_ready:
        return validate_all_admission(args.root)
    
    if args.packet:
        packet = load_yaml(args.packet)
        designs = load_designs(args.root / "designs")
        packets = load_packets(args.root / "work-packets")
        try:
            validate_admission(packet, designs, packets)
            print(f"packet admission valid: {args.packet}")
            return 0
        except ValueError as exc:
            print(f"admission failed: {exc}", file=sys.stderr)
            return 1
    
    # Default: validate all Ready packets
    return validate_all_admission(args.root)


if __name__ == "__main__":
    raise SystemExit(main())
