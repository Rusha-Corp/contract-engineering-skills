#!/usr/bin/env python3
"""Tests for consumer migration and compatibility documentation."""

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class DesignDocumentationTests(unittest.TestCase):
    def test_templates_and_workflow_exist(self):
        for path in (
            "templates/design-review.yaml",
            "templates/design-artifact-manifest.yaml",
            "templates/factory-consumer.yaml",
            "docs/supervisor-workflow.md",
        ):
            self.assertTrue((ROOT / path).is_file(), path)

    def test_protocol_configuration_explains_composition(self):
        text = (ROOT / "docs/protocol-configuration.md").read_text()
        self.assertIn("obra/superpowers", text)
        self.assertIn("Repository validators and CI", text)
        self.assertIn("contract-admission", text)

    def test_consumer_template_preserves_legacy_migration(self):
        text = (ROOT / "templates/factory-consumer.yaml").read_text()
        self.assertIn("legacy_records_allowed: true", text)
        self.assertIn("mandatory_designs_for_new_visual_work: true", text)
        self.assertIn("rollback:", text)

    def test_supervisor_workflow_has_stop_and_rollback_rules(self):
        text = (ROOT / "docs/supervisor-workflow.md").read_text()
        self.assertIn("must stop", text)
        self.assertIn("Rollback", text)
        self.assertIn("separately installed", text)


if __name__ == "__main__":
    unittest.main()
