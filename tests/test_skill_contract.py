from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class SkillContractTests(unittest.TestCase):
    def test_frontmatter_and_ui_identity_are_consistent(self) -> None:
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", skill_text, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)
        self.assertRegex(frontmatter, r"(?m)^name:\s+jimu-codex-team$")
        self.assertRegex(frontmatter, r"(?m)^description:\s+.+\$jimu-codex-team.+$")

        ui = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertRegex(ui, r'(?m)^\s+display_name:\s+"Jimu Codex Team"$')
        self.assertRegex(ui, r'(?m)^\s+default_prompt:\s+"[^\n]*\$jimu-codex-team[^\n]*"$')
        self.assertRegex(ui, r"(?m)^\s+allow_implicit_invocation:\s+false$")
        short = re.search(r'(?m)^\s+short_description:\s+"([^\n]+)"$', ui)
        self.assertIsNotNone(short)
        self.assertGreaterEqual(len(short.group(1)), 25)
        self.assertLessEqual(len(short.group(1)), 64)

    def test_dispatch_packet_and_profile_gate_are_complete(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for label in ("Outcome", "Benefit", "Sources", "Scope", "Checks", "Stop when", "Return"):
            with self.subTest(label=label):
                self.assertIn(f"`{label}`", skill)
        for label in ("Unresolved risk", "Evidence", "Checks already passed", "Do not repeat"):
            with self.subTest(label=label):
                self.assertIn(f"`{label}`", skill)
        self.assertIn("explicitly pass `agent_type`", skill)
        self.assertIn("never use `task_name` to select a profile", skill)
        self.assertIn("Children never spawn descendants", skill)
        self.assertIn('fork_turns="none"', skill)

    def test_all_conditional_references_and_diagnostics_exist(self) -> None:
        for relative in (
            "references/agent-setup.md",
            "references/evaluation.md",
            "references/interactive-testing.md",
            "scripts/inspect-team-runs.py",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_no_scaffold_placeholders_remain(self) -> None:
        text_paths = [
            ROOT / "SKILL.md",
            ROOT / "agents" / "openai.yaml",
            *sorted((ROOT / "references").glob("*.md")),
            *sorted((ROOT / "assets" / "agent-profiles").glob("*.toml")),
        ]
        for path in text_paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("[TODO:", text)


if __name__ == "__main__":
    unittest.main()
