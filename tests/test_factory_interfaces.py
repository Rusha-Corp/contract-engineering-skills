#!/usr/bin/env python3
"""Metadata and ownership tests for Contract Engineering interfaces."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
FORBIDDEN_SKILLS = {
    "using-superpowers",
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "using-git-worktrees",
    "test-driven-development",
}
EXPECTED_SKILLS = {
    "contract-design",
    "contract-review",
    "contract-admission",
    "contract-visual-review",
    "contract-handoff-acceptance",
}


class FactoryInterfaceTests(unittest.TestCase):
    def test_governance_skills_are_unique_and_present(self):
        skills = {path.parent.name for path in (ROOT / "skills").glob("contract-*/SKILL.md")}
        self.assertEqual(skills, EXPECTED_SKILLS)
        self.assertFalse(skills & FORBIDDEN_SKILLS)

    def test_commands_and_droids_exist(self):
        self.assertEqual(
            {path.name for path in (ROOT / "commands").glob("*.md")},
            {"contract-plan.md", "contract-review.md", "contract-admit.md", "design-preview.md"},
        )
        self.assertEqual(
            {path.name for path in (ROOT / "droids").glob("*.md")},
            {"contract-designer.md", "contract-reviewer.md", "contract-supervisor.md"},
        )

    def test_interfaces_preserve_stop_points_and_boundaries(self):
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in list((ROOT / "commands").glob("*.md"))
            + list((ROOT / "droids").glob("*.md"))
        ).lower()
        self.assertIn("do not approve", text)
        self.assertIn("validators", text)
        self.assertNotRegex(text, r"approve.*without.*user")

    def test_skills_have_metadata_and_unique_names(self):
        for path in (ROOT / "skills").glob("contract-*/SKILL.md"):
            content = path.read_text(encoding="utf-8")
            self.assertRegex(content, rf"name:\s*{re.escape(path.parent.name)}")
            self.assertIn("description:", content)


if __name__ == "__main__":
    unittest.main()
