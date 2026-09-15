#!/usr/bin/env python3
"""Tests for fail-closed packet scope and admission policy."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "contract_policy", ROOT / "runtime" / "contract_policy.py"
)
assert SPEC and SPEC.loader
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class FactoryHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        packet_dir = self.root / ".contract-engineering" / "work-packets"
        packet_dir.mkdir(parents=True)
        (packet_dir / "TEST-T001-P001.yaml").write_text(
            yaml.safe_dump(
                {
                    "packet_id": "TEST-T001-P001",
                    "state": "Implementing",
                    "scope": {"in": ["src/"], "out": []},
                }
            ),
            encoding="utf-8",
        )
        (self.root / "src").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_edit_without_claimed_packet_is_denied(self):
        (self.root / ".contract-engineering" / "work-packets" / "TEST-T001-P001.yaml").unlink()
        self.assertEqual(
            policy.evaluate_tool_call(self.root, "Edit", {"file_path": "src/a.py"})[0],
            "deny",
        )

    def test_edit_outside_scope_is_denied(self):
        decision, _ = policy.evaluate_tool_call(self.root, "Edit", {"file_path": "docs/a.md"})
        self.assertEqual(decision, "deny")

    def test_execute_publish_requires_approval(self):
        decision, _ = policy.evaluate_tool_call(self.root, "Execute", {"command": "git push origin main"})
        self.assertEqual(decision, "ask")

    def test_read_only_design_review_is_allowed(self):
        decision, _ = policy.evaluate_tool_call(self.root, "Read", {"file_path": "docs/design.md"})
        self.assertEqual(decision, "allow")

    def test_direct_tracker_state_edit_is_denied(self):
        decision, _ = policy.evaluate_tool_call(
            self.root, "Edit", {"file_path": ".contract-engineering/tracker/index.yaml"}
        )
        self.assertEqual(decision, "deny")

    def test_hook_input_paths_are_sanitized(self):
        decision, _ = policy.evaluate_tool_call(
            self.root, "Edit", {"file_path": "../outside.txt"}
        )
        self.assertEqual(decision, "deny")

    def test_in_scope_edit_is_allowed(self):
        decision, _ = policy.evaluate_tool_call(self.root, "Edit", {"file_path": "src/a.py"})
        self.assertEqual(decision, "allow")


if __name__ == "__main__":
    unittest.main()
