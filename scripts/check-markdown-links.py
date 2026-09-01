#!/usr/bin/env python3
"""Check relative Markdown links and image references resolve to real files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#+\s+(.+)$")


def collect_headings(text: str) -> set[str]:
    headings: set[str] = set()
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            slug = re.sub(r"[^\w\s-]", "", m.group(1).strip().lower())
            slug = re.sub(r"[\s]+", "-", slug)
            headings.add(slug)
    return headings


def check_file(md_path: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    text = md_path.read_text()
    for m in LINK_RE.finditer(text):
        label, target = m.group(1), m.group(2).strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        # Strip anchor
        path_part, _, anchor = target.partition("#")
        if not path_part:
            # Pure anchor link — check heading in same file
            headings = collect_headings(text)
            if anchor.lower() not in headings:
                errors.append(f"{md_path}: anchor #{anchor} not found in file")
            continue
        resolved = (md_path.parent / path_part).resolve()
        if not resolved.exists():
            errors.append(f"{md_path}: link '{label}' -> {target} (file not found: {resolved})")
            continue
        if anchor:
            target_text = resolved.read_text()
            headings = collect_headings(target_text)
            if anchor.lower() not in headings:
                errors.append(f"{md_path}: anchor #{anchor} not found in {resolved}")
    return errors


def main() -> int:
    repo_root = Path.cwd()
    md_files = sorted(
        list(repo_root.glob("*.md"))
        + list(repo_root.glob("docs/*.md"))
        + list((repo_root / "adapters").glob("**/*.md"))
    )
    all_errors: list[str] = []
    for md_path in md_files:
        all_errors.extend(check_file(md_path, repo_root))
    if all_errors:
        for e in all_errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(f"markdown links valid: {len(md_files)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
