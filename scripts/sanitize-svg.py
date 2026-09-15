#!/usr/bin/env python3
"""Reject unsafe SVG content before it is previewed or committed."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_SVG_BYTES = 2 * 1024 * 1024
REMOTE_REFERENCE = re.compile(r"(?:https?:|data:|//)", re.IGNORECASE)


class SafetyError(ValueError):
    """Raised when an artifact violates the offline safety policy."""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def sanitize_svg(path: Path, output: Path | None = None) -> str:
    """Validate an SVG and optionally write the unchanged safe document."""
    raw = path.read_bytes()
    if len(raw) > MAX_SVG_BYTES:
        raise SafetyError(f"SVG exceeds {MAX_SVG_BYTES} bytes")
    text = raw.decode("utf-8")
    if "<!doctype" in text.lower() or "<!entity" in text.lower():
        raise SafetyError("SVG declarations and entities are not allowed")
    if REMOTE_REFERENCE.search(text):
        # The XML namespace declaration is allowed; only references are not.
        without_namespace = text.replace(
            'xmlns="http://www.w3.org/2000/svg"', ""
        )
        if REMOTE_REFERENCE.search(without_namespace):
            raise SafetyError("SVG contains a remote or data reference")

    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, UnicodeDecodeError) as exc:
        raise SafetyError(f"SVG is not valid XML: {type(exc).__name__}") from exc

    for element in root.iter():
        if _local_name(element.tag) in {"script", "foreignobject"}:
            raise SafetyError(f"SVG contains forbidden element: {_local_name(element.tag)}")
        for attribute, value in element.attrib.items():
            if attribute.rsplit("}", 1)[-1].lower() in {"href", "onclick"}:
                raise SafetyError("SVG contains an external reference or handler")
            if re.fullmatch(r"on[a-z0-9_-]+", attribute, re.IGNORECASE):
                raise SafetyError("SVG contains an event handler")
            if REMOTE_REFERENCE.search(value):
                raise SafetyError("SVG contains a remote or data reference")

    safe_text = text
    if output is not None:
        output.write_text(safe_text, encoding="utf-8")
    return safe_text


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("usage: sanitize-svg.py INPUT [OUTPUT]", file=sys.stderr)
        return 2
    try:
        output = Path(sys.argv[2]) if len(sys.argv) == 3 else None
        sanitize_svg(Path(sys.argv[1]), output)
    except (OSError, SafetyError) as exc:
        print(f"unsafe SVG: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("SVG safety validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
