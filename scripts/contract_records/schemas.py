"""JSON Schema validation for canonical records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema
from referencing import Registry, Resource

from .loaders import (
    _tracker_instance_paths,
    fail,
    load_json_schema,
    load_yaml,
    validate_identifier,
    validate_instance,
)


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
