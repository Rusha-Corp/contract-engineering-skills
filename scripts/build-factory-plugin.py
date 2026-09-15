#!/usr/bin/env python3
"""Check reproducible root-level packaging without copying files."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        parser.error("only --check is supported; packaging never copies or overwrites sources")
    validator = Path(__file__).with_name("validate-factory-plugin.py")
    result = subprocess.run(
        [sys.executable, str(validator), "--root", "."],
        check=False,
    )
    if result.returncode == 0:
        print("Factory plugin reproducibility check passed")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
