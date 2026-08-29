from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PROFILES = ROOT / "assets" / "agent-profiles"


class AgentProfileTests(unittest.TestCase):
    def test_profiles_parse_and_match_role_contract(self) -> None:
        expected = {
            "Explorer.toml": ("Explorer", "gpt-5.6-luna", "medium", "read-only"),
            "Executor.toml": ("Executor", "gpt-5.6-luna", "high", "workspace-write"),
            "Reviewer.toml": ("Reviewer", "gpt-5.6-terra", "medium", "read-only"),
            "default.toml": ("default", "gpt-5.6-terra", "low", "read-only"),
        }
        self.assertEqual({path.name for path in PROFILES.glob("*.toml")}, set(expected))
        for filename, contract in expected.items():
            with self.subTest(filename=filename):
                data = tomllib.loads((PROFILES / filename).read_text(encoding="utf-8"))
                actual = (
                    data["name"],
                    data["model"],
                    data["model_reasoning_effort"],
                    data["sandbox_mode"],
                )
                self.assertEqual(actual, contract)
                self.assertTrue(data["description"].strip())
                self.assertTrue(data["developer_instructions"].strip())

    def test_working_profiles_disable_descendant_fanout(self) -> None:
        for filename in ("Explorer.toml", "Executor.toml", "Reviewer.toml"):
            with self.subTest(filename=filename):
                data = tomllib.loads((PROFILES / filename).read_text(encoding="utf-8"))
                self.assertIn("Do not spawn subagents", data["developer_instructions"])

    def test_guard_is_fail_closed_and_has_no_work_instructions(self) -> None:
        data = tomllib.loads((PROFILES / "default.toml").read_text(encoding="utf-8"))
        instructions = data["developer_instructions"]
        self.assertIn("dispatch guard, not a working subagent", instructions)
        self.assertIn("Do not inspect files, call tools, spawn", instructions)
        self.assertIn("DISPATCH BLOCKED", instructions)
        self.assertIn("agent_type=Explorer, Executor, or Reviewer", instructions)

    def test_mutation_authority_is_confined_to_executor(self) -> None:
        modes = {}
        for path in PROFILES.glob("*.toml"):
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            modes[data["name"]] = data["sandbox_mode"]
        self.assertEqual(
            {name for name, mode in modes.items() if mode == "workspace-write"},
            {"Executor"},
        )


if __name__ == "__main__":
    unittest.main()
