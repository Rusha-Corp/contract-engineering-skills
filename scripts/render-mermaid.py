#!/usr/bin/env python3
"""Render Mermaid with an explicitly installed local CLI only."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "sanitize_svg", Path(__file__).with_name("sanitize-svg.py")
)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
sanitize_svg = _MODULE.sanitize_svg
SafetyError = _MODULE.SafetyError


def render_mermaid(source: Path, output: Path, cli: str = "mmdc") -> None:
    """Render source through a host CLI, then validate the derived SVG."""
    executable = shutil.which(cli)
    if executable is None:
        raise RuntimeError("Mermaid renderer is unavailable")
    result = subprocess.run(
        [executable, "--input", str(source), "--output", str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 or not output.is_file():
        raise RuntimeError("Mermaid renderer failed")
    sanitize_svg(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cli", default="mmdc")
    args = parser.parse_args()
    try:
        render_mermaid(args.source, args.output, args.cli)
    except (OSError, RuntimeError, SafetyError):
        print("Mermaid rendering unavailable or unsafe", file=sys.stderr)
        return 1
    print("Mermaid SVG rendered and validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
