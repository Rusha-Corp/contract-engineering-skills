#!/usr/bin/env python3
"""Validate design contract records against schema and semantic rules."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema
import yaml

SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "design-contract.schema.json"
DESIGNS_DIR = Path(".contract-engineering") / "designs"

SHA256 = re.compile(r"^[0-9a-f]{64}$")
DESIGN_ID = re.compile(r"^[A-Z0-9-]+-DC[0-9]{3}$")
TASK_ID = re.compile(r"^[A-Z0-9-]+-T[0-9]{3}$")

# Required artifacts by design type
REQUIRED_ARTIFACTS = {
    "text": {"architecture"},
    "ui": {"html"},
    "ux": {"html"},
    "architecture": {"mermaid", "svg"},
    "workflow": {"mermaid", "svg"},
    "data-flow": {"mermaid", "svg"},
    "mixed": {"html", "mermaid", "svg"},  # Union of applicable types
}

# Required reviews by design type
REQUIRED_REVIEWS = {
    "text": {"design"},
    "ui": {"design", "visual"},
    "ux": {"design", "visual"},
    "architecture": {"design", "architecture"},
    "workflow": {"design"},
    "data-flow": {"design", "architecture"},
    "mixed": {"design", "architecture", "visual"},
}


def load_schema() -> dict[str, Any]:
    """Load the design contract JSON schema."""
    return json.loads(SCHEMA_PATH.read_text())


def load_design(path: Path) -> dict[str, Any]:
    """Load a design contract YAML file."""
    try:
        return yaml.safe_load(path.read_text())
    except Exception as exc:
        raise ValueError(f"{path}: invalid YAML ({type(exc).__name__})")


def validate_schema(design: dict[str, Any], schema: dict[str, Any], source: str = "design") -> None:
    """Validate design contract against JSON schema."""
    try:
        jsonschema.validate(design, schema)
    except jsonschema.ValidationError as exc:
        raise ValueError(f"{source}: schema validation failed - {exc.message}")


def validate_artifact_requirements(design: dict[str, Any], source: str = "design") -> None:
    """Validate that design has required artifacts for its type."""
    design_type = design["design_type"]
    required_kinds = REQUIRED_ARTIFACTS.get(design_type, set())
    
    artifact_kinds = {a["kind"] for a in design.get("artifacts", [])}
    
    missing = required_kinds - artifact_kinds
    if missing:
        raise ValueError(f"{source}: missing required artifact kinds for {design_type}: {sorted(missing)}")


def validate_review_requirements(design: dict[str, Any], source: str = "design") -> None:
    """Validate that design has required reviews for its type."""
    design_type = design["design_type"]
    required_kinds = REQUIRED_REVIEWS.get(design_type, set())
    
    review_kinds = {r["kind"] for r in design.get("reviews", []) if r["status"] == "accepted"}
    
    missing = required_kinds - review_kinds
    if missing:
        raise ValueError(f"{source}: missing required review kinds for {design_type}: {sorted(missing)}")


def validate_approval_revision(design: dict[str, Any], source: str = "design") -> None:
    """Validate approval binds to artifact manifest."""
    if design["status"] != "approved":
        return
    
    approved_revision = design["approval"]["approved_revision"]
    if not SHA256.fullmatch(approved_revision):
        raise ValueError(f"{source}: approved_revision must be a 64-character hex string")
    
    # Compute artifact manifest hash
    artifact_data = json.dumps(design["artifacts"], sort_keys=True).encode("utf-8")
    manifest_hash = hashlib.sha256(artifact_data).hexdigest()
    
    if approved_revision != manifest_hash:
        raise ValueError(
            f"{source}: approved_revision does not match artifact manifest hash "
            f"(approved: {approved_revision[:16]}..., actual: {manifest_hash[:16]}...)"
        )


def validate_design(design: dict[str, Any], source: str = "design") -> None:
    """Validate a design contract semantically."""
    schema = load_schema()
    
    # Schema validation
    validate_schema(design, schema, source)
    
    # Identifier validation
    if not DESIGN_ID.fullmatch(design["design_id"]):
        raise ValueError(f"{source}: invalid design_id format")
    if not TASK_ID.fullmatch(design["task_id"]):
        raise ValueError(f"{source}: invalid task_id format")
    
    # Artifact requirements
    validate_artifact_requirements(design, source)
    
    # Review requirements
    validate_review_requirements(design, source)
    
    # Approval validation
    if design["status"] == "approved":
        validate_approval_revision(design, source)


def load_designs(root: Path = DESIGNS_DIR) -> dict[str, dict[str, Any]]:
    """Load all design contracts from the designs directory."""
    designs = {}
    if not root.exists():
        return designs
    
    for task_dir in sorted(root.iterdir()):
        if not task_dir.is_dir():
            continue
        design_path = task_dir / "design.yaml"
        if design_path.is_file():
            design = load_design(design_path)
            task_id = task_dir.name
            designs[task_id] = design
    
    return designs


def validate_all_designs(root: Path = DESIGNS_DIR) -> int:
    """Validate all design contracts and return exit code."""
    designs = load_designs(root)
    
    if not designs:
        print("no design contracts found")
        return 0
    
    errors = []
    for task_id, design in designs.items():
        try:
            validate_design(design, f"{task_id}/design.yaml")
        except ValueError as exc:
            errors.append(str(exc))
    
    if errors:
        for error in errors:
            print(f"design validation failed: {error}", file=sys.stderr)
        return 1
    
    print(f"design contracts valid: {len(designs)} designs")
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Validate design contracts")
    parser.add_argument("--root", type=Path, default=DESIGNS_DIR, help="Designs directory root")
    parser.add_argument("--design", type=Path, help="Validate a specific design file")
    args = parser.parse_args()
    
    if args.design:
        design = load_design(args.design)
        try:
            validate_design(design, str(args.design))
            print(f"design contract valid: {args.design}")
            return 0
        except ValueError as exc:
            print(f"design validation failed: {exc}", file=sys.stderr)
            return 1
    
    return validate_all_designs(args.root)


if __name__ == "__main__":
    raise SystemExit(main())
