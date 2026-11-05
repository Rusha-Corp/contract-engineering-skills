"""Orchestration: root resolution, record loading, validation dispatch, CLI."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from .constants import ARCHIVE_PACKET_DIR
from .graph_rules import (
    enforce_scope,
    validate_dependency_graph,
    validate_locks,
    validate_references,
)
from .loaders import (
    ValidationResult,
    configure_resource_limits,
    fail,
)
from .lock_rules import validate_project_lock
from .packet_rules import validate_packet, validate_planning_records
from .schemas import validate_json_schemas
from .tracker_rules import validate_tracker

_PARENT = Path(__file__).resolve().parent.parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from scripts.record_store import FileStore


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


def _validate_records(
    root: Path,
    packet_path: Path | None,
    changed_paths: list[str],
    *,
    store: FileStore | None = None,
) -> None:
    if not root.is_dir():
        fail(f"protocol root does not exist: {root}")
    configure_resource_limits()

    if store is None:
        store = FileStore(root)
    live_packets = store.list_packets("active")
    archive_packets = store.list_packets("archive")
    cross_dup = set(live_packets) & set(archive_packets)
    if cross_dup:
        fail(f"duplicate packet IDs across partitions {sorted(cross_dup)}")
    packets = {**live_packets, **archive_packets}
    validate_json_schemas(root, packets)
    for directory, partition in (
        (root / "work-packets", live_packets),
        (root / ARCHIVE_PACKET_DIR, archive_packets),
    ):
        for packet_id, packet in partition.items():
            path = directory / f"{packet_id}.yaml"
            validate_packet(path, packet, packets)
    validate_project_lock(root)
    validate_canonical_tracker(root)
    validate_tracker(root, live_packets, archive_packets)
    validate_dependency_graph(packets)
    validate_locks(packets)
    validate_references(root, packets, store=store)
    validate_planning_records(root, packets)
    if packet_path:
        packet = packets.get(packet_path.stem)
        if packet is None:
            fail(f"unknown packet {packet_path}")
        enforce_scope(packet, changed_paths)


def run_validation(
    project_dir: Path | str = ".",
    *,
    explicit_root: Path | str | None = None,
    mode: str | None = None,
    environment: dict[str, str] | None = None,
    packet_path: Path | None = None,
    changed_paths: list[str] | None = None,
    store: FileStore | None = None,
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
        _validate_records(root, packet_path, changed_paths or [], store=store)
    except ValueError as exc:
        if selected == "enforced":
            raise
        return ValidationResult(selected, valid=False, messages=(str(exc),))
    return ValidationResult(selected, valid=True)


def validate_canonical_tracker(root: Path) -> None:
    if not (root / "tracker/index.yaml").is_file():
        return
    script = Path(__file__).resolve().parent.parent / "validate-tracker.py"
    spec = importlib.util.spec_from_file_location("validate_tracker", script)
    if spec is None or spec.loader is None:
        fail(f"{script}: cannot load canonical tracker validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate(root, store=FileStore(root))
    render_script = Path(__file__).resolve().parent.parent / "render-tracker.py"
    render_spec = importlib.util.spec_from_file_location("render_tracker", render_script)
    if render_spec is None or render_spec.loader is None:
        fail(f"{render_script}: cannot load tracker renderer")
    renderer = importlib.util.module_from_spec(render_spec)
    render_spec.loader.exec_module(renderer)
    renderer.render_projections(root, check=True)


def main() -> int:
    import argparse

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
