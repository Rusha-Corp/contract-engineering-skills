#!/usr/bin/env python3
"""Validate Contract Engineering records and optionally enforce packet scope.

This is a thin entry point that delegates to the ``scripts.contract_records``
package. All public names are re-exported so that path-based test imports
(via ``importlib.util.spec_from_file_location``) continue to work unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from scripts.contract_records import *  # noqa: F401,F403
from scripts.contract_records import main
from scripts.contract_records import code_health  # noqa: F401

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"contract validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
