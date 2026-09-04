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
            "Frontend.toml": ("Frontend", "gemini-3.8-flash", "high", "workspace-write"),
            "FrontendFast.toml": ("FrontendFast", "gemini-3.7-flash", "high", "workspace-write"),
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
        for filename in ("Explorer.toml", "Executor.toml", "Frontend.toml", "FrontendFast.toml", "Reviewer.toml"):
            with self.subTest(filename=filename):
                data = tomllib.loads((PROFILES / filename).read_text(encoding="utf-8"))
                self.assertIn("Do not spawn subagents", data["developer_instructions"])

    def test_frontend_profiles_keep_ui_work_inside_frontend_boundary(self) -> None:
        for filename in ("Frontend.toml", "FrontendFast.toml"):
            with self.subTest(filename=filename):
                data = tomllib.loads((PROFILES / filename).read_text(encoding="utf-8"))
                instructions = data["developer_instructions"]
                for phrase in (
                    "frontend slice",
                    "existing design system",
                    "tokens",
                    "components",
                    "accessibility patterns",
                    "responsive conventions",
                    "frontend code, styles, assets",
                    "focused UI tests",
                    "backend code",
                    "database schemas",
                    "authentication or authorization",
                    "API contracts",
                    "endpoint payloads",
                    "generated contracts",
                    "server configuration",
                    "Do not spawn subagents or descendants",
                    "Do not publish or deploy externally",
                ):
                    with self.subTest(phrase=phrase):
                        self.assertIn(phrase, instructions)

    def test_frontend_dispatch_contract_covers_role_selection_and_visual_acceptance(self) -> None:
        profile = (PROFILES / "FrontendFast.toml").read_text(encoding="utf-8")
        reference = (ROOT / "references" / "frontend-ui.md").read_text(encoding="utf-8")
        contract = " ".join((profile + " " + reference).split()).lower()

        # A UI specialist is the safe default when the parent cannot distinguish
        # between a general implementation slice and a frontend-only slice.
        self.assertRegex(contract, r"(?:when|if).{0,120}uncertain.{0,120}frontend")
        self.assertIn("supplementary only", contract)
        self.assertRegex(contract, r"frontend.{0,100}(?:normal|default)")

        # The fast role is intentionally narrow: it assumes fixed contracts and
        # is reserved for localized, low-risk, deterministic work.
        self.assertRegex(contract, r"(?:fixed|stable).{0,120}(?:design|api)")
        self.assertRegex(contract, r"(?:localized|narrow|small|limited).{0,100}low[- ]risk")
        self.assertRegex(contract, r"deterministic.{0,100}(?:checks|scope|slice)")
        self.assertRegex(contract, r"target files?.{0,100}(?:known|assigned|scope)")
        self.assertRegex(contract, r"material.{0,100}(?:speed|cost)")

        # It cannot be used as an error fallback or as a second writer taking
        # over a slice already assigned to another frontend agent.
        self.assertRegex(contract, r"(?:not|never|do not|does not|neither|nor).{0,100}failure fallback")
        self.assertRegex(contract, r"(?:not|never|do not|does not|neither|nor).{0,100}(?:concurrent takeover|takeover)")

        # Standard visual evidence must cover responsive viewports and the
        # relevant states, while final visual acceptance remains with the parent.
        self.assertRegex(contract, r"desktop.{0,100}mobile|mobile.{0,100}desktop")
        self.assertRegex(contract, r"relevant.{0,100}states?")
        self.assertRegex(contract, r"states?.{0,100}in scope")
        self.assertRegex(contract, r"final.{0,100}visual.{0,100}accept")
        self.assertRegex(contract, r"(?:main thread|parent).{0,100}(?:final|visual)")

    def test_guard_is_fail_closed_and_has_no_work_instructions(self) -> None:
        data = tomllib.loads((PROFILES / "default.toml").read_text(encoding="utf-8"))
        instructions = data["developer_instructions"]
        self.assertIn("dispatch guard, not a working subagent", instructions)
        self.assertIn("Do not inspect files, call tools, spawn", instructions)
        self.assertIn("DISPATCH BLOCKED", instructions)
        self.assertIn("agent_type=Explorer, Executor, Frontend, FrontendFast, or Reviewer", instructions)

    def test_workspace_write_authority_allows_only_declared_writer_roles(self) -> None:
        modes = {}
        for path in PROFILES.glob("*.toml"):
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            modes[data["name"]] = data["sandbox_mode"]
        self.assertEqual(
            {name for name, mode in modes.items() if mode == "workspace-write"},
            {"Executor", "Frontend", "FrontendFast"},
        )


if __name__ == "__main__":
    unittest.main()
