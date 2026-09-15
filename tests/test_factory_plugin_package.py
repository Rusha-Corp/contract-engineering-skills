#!/usr/bin/env python3
"""Tests for root-level Factory plugin packaging."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class FactoryPluginPackageTests(unittest.TestCase):
    def test_marketplace_points_to_root_plugin(self):
        marketplace = json.loads((ROOT / ".factory-plugin/marketplace.json").read_text())
        self.assertEqual(marketplace["plugins"][0]["source"], "./")

    def test_plugin_contains_governed_interfaces_and_runtime(self):
        for relative in (
            ".factory-plugin/plugin.json",
            "skills/contract-design/SKILL.md",
            "skills/contract-review/SKILL.md",
            "skills/contract-admission/SKILL.md",
            "skills/contract-visual-review/SKILL.md",
            "skills/contract-handoff-acceptance/SKILL.md",
            "commands/design-preview.md",
            "droids/contract-supervisor.md",
            "hooks/hooks.json",
            "runtime/mermaid.min.js",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_validator_and_reproducibility_check_pass(self):
        for script in ("validate-factory-plugin.py", "build-factory-plugin.py"):
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / script), "--check"]
                if script.startswith("build")
                else [sys.executable, str(ROOT / "scripts" / script), "--root", str(ROOT)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_plugin_paths_do_not_escape_root(self):
        marketplace = json.loads((ROOT / ".factory-plugin/marketplace.json").read_text())
        source = Path(marketplace["plugins"][0]["source"])
        self.assertEqual((ROOT / source).resolve(), ROOT.resolve())

    def test_superpowers_installation_is_documented_separately(self):
        text = (ROOT / "docs/superpowers/specs/2026-09-15-design-contract-factory-plugin-superpowers-design.md").read_text()
        self.assertIn("obra/superpowers", text)
        self.assertIn("source is", text)


if __name__ == "__main__":
    unittest.main()
