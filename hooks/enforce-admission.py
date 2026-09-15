#!/usr/bin/env python3
"""Factory hook for fail-closed packet admission before execution."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(os.environ.get("DROID_PROJECT_ROOT", os.getcwd())).resolve()
    validator = root / "scripts" / "validate-admission.py"
    if not validator.is_file():
        print("deny: admission validator is unavailable")
        return 2
    result = subprocess.run(
        [sys.executable, str(validator), "--root", str(root / ".contract-engineering"), "--all-ready"],
        cwd=root,
        check=False,
    )
    if result.returncode:
        print("deny: packet admission failed")
        return 2
    print("allow: packet admission passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
