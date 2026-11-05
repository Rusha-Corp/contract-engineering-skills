"""Constants and identifier utilities for contract record validation."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

# Load the identifiers module from scripts/ (one level up from this package).
_IDENTIFIERS = Path(__file__).resolve().parent.parent / "identifiers.py"
_IDENTIFIER_SPEC = importlib.util.spec_from_file_location("identifiers", _IDENTIFIERS)
assert _IDENTIFIER_SPEC and _IDENTIFIER_SPEC.loader
identifiers = importlib.util.module_from_spec(_IDENTIFIER_SPEC)
_IDENTIFIER_SPEC.loader.exec_module(identifiers)

STATES = {
    "Planned",
    "Claimed",
    "DesignReview",
    "DesignBlocked",
    "DataReview",
    "DataBlocked",
    "Ready",
    "Implementing",
    "Validation",
    "Rework",
    "Handoff",
    "Complete",
    "Interrupted",
    "Cancelled",
}
DOMAINS = {"coding", "browser", "design", "data", "documentation", "security"}
TASK_ID = identifiers.TASK_ID
PACKET_ID = identifiers.PACKET_ID
BASE_REVISION = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_YAML_BYTES = 1 * 1024 * 1024
MAX_SCALAR_BYTES = 256 * 1024
MAX_YAML_NODES = 10_000
MAX_YAML_DEPTH = 64
MAX_YAML_ALIASES = 50
MAX_CPU_SECONDS = 10
MAX_ADDRESS_SPACE = 512 * 1024 * 1024
SECURITY_SCOPE_PATTERNS = (
    ".github/workflows/",
    "adapters/",
    "docs/agent-security.md",
    "docs/adapter-security.md",
    "docs/approval-integrity.md",
    "docs/incident-response.md",
    "docs/release-integrity.md",
    "schemas/",
    "templates/adapter-",
    "templates/agent-",
)
PACKET_CLASSES = {
    "single-domain",
    "cross-cutting",
    "parent-coordination",
    "child-implementation",
}
ACCEPTANCE_CRITERION_ID = re.compile(r"^[A-Z0-9-]+-AC\d{3}$")
VALIDATION_PLAN_ID = re.compile(r"^[A-Z0-9-]+-VAL\d{3}$")
OPEN_QUESTION_ID = re.compile(r"^[A-Z0-9-]+-OQ\d{3}$")
EPIC_ID = re.compile(r"^(?:[A-Z][A-Z0-9]*-)+E\d{3}$")
WORK_TYPES = {"discovery", "delivery", "bugfix", "enabler"}
PRIORITIES = {"critical", "high", "normal", "deferred"}
QUESTION_DISPOSITIONS = {"blocking", "bounded", "resolved", "follow_up", "deferred"}
EXECUTION_CONTROL_REFS = (
    "trust_boundary_ref",
    "execution_budget_ref",
    "checkpoint_ref",
    "evaluation_ref",
    "agent_run_ref",
    "observability_refs",
    "incident_refs",
)
FORBIDDEN_CAPABILITIES = {
    "admin:repository",
    "write:outside-scope",
    "execute:untrusted",
}

# Tracker constants
ARCHIVE_PACKET_DIR = "archive/work-packets"
ARCHIVE_TRACKER = "archive/execution-tracker-archive.md"
TRACKER_SHARD_DIR = "tracker-shards"
MAX_INDEX_PACKET_ROWS = 25
MAX_SHARD_PACKET_ROWS = 50
TERMINAL_STATES = {"Complete", "Cancelled"}
