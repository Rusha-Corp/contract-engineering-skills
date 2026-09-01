#!/usr/bin/env python3
"""Validate Contract Spark SVG assets for accessibility, safety, and palette."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PALETTE = {"#173F5F", "#20639B", "#3CAEA3", "#F6D55C", "#ED553B", "#FFFFFF", "#ffffff", "none", "white"}
NS = {"svg": "http://www.w3.org/2000/svg"}


def validate_svg(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [f"{path}: invalid XML ({exc})"]
    root = tree.getroot()
    if not root.get("viewBox"):
        errors.append(f"{path}: missing viewBox")
    if root.find(".//svg:title", NS) is None:
        errors.append(f"{path}: missing <title> for accessibility")
    if root.find(".//svg:desc", NS) is None:
        errors.append(f"{path}: missing <desc> for accessibility")
    if root.findall(".//svg:script", NS):
        errors.append(f"{path}: contains <script> tag")
    for elem in root.iter():
        for attr in ("href", "xlink:href"):
            if attr in elem.attrib:
                errors.append(f"{path}: contains external reference ({attr})")
    text = path.read_text()
    colors = set(re.findall(r"#[0-9A-Fa-f]{6}", text))
    off_palette = colors - PALETTE
    if off_palette:
        errors.append(f"{path}: off-palette colors: {sorted(off_palette)}")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: validate-svg-assets.py <svg-dir-or-file>...", file=sys.stderr)
        return 2
    all_errors: list[str] = []
    count = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            files = sorted(p.glob("*.svg"))
        else:
            files = [p]
        for f in files:
            count += 1
            all_errors.extend(validate_svg(f))
    if all_errors:
        for e in all_errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(f"svg assets valid: {count} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
