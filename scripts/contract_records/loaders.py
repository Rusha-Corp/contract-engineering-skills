"""YAML/JSON loading, resource limits, and shared validation helpers."""

from __future__ import annotations

import os
import sys
from collections import namedtuple
from pathlib import Path
from typing import Any

import jsonschema
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

from .constants import (
    MAX_ADDRESS_SPACE,
    MAX_CPU_SECONDS,
    MAX_SCALAR_BYTES,
    MAX_YAML_ALIASES,
    MAX_YAML_BYTES,
    MAX_YAML_DEPTH,
    MAX_YAML_NODES,
)


def fail(message: str) -> None:
    raise ValueError(message)


ValidationResult = namedtuple(
    "ValidationResult", ("mode", "valid", "skipped", "messages"),
    defaults=(False, ()),
)


def path_matches(candidate: str, rule: str) -> bool:
    candidate = candidate.rstrip("/")
    rule = rule.rstrip("/")
    return candidate == rule or candidate.startswith(rule + "/")


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


def validate_identifier(validator: Any, value: object, label: str) -> None:
    try:
        validator.validate(value)
    except jsonschema.ValidationError as exc:
        fail(f"{label}: JSON Schema validation failed: {exc.message}")


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
