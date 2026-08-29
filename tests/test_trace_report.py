from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "inspect-team-runs.py"
SPEC = importlib.util.spec_from_file_location("inspect_team_runs", SCRIPT)
assert SPEC and SPEC.loader
report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report)


def event(kind: str, payload: dict, timestamp: str | None = None) -> str:
    value = {"type": kind, "payload": payload}
    if timestamp:
        value["timestamp"] = timestamp
    return json.dumps(value) + "\n"


def write_trace(
    root: Path,
    filename: str,
    *,
    session_id: str,
    task_id: str,
    role: str | None,
    model: str,
    effort: str,
    parent: str | None = None,
    sandbox: str = "read-only",
    completed: bool = True,
) -> None:
    path = root / "2026" / "08" / "29" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"id": session_id, "session_id": task_id}
    if parent:
        metadata["parent_thread_id"] = parent
    if role:
        metadata["agent_role"] = role
    content = event("session_meta", metadata)
    content += event(
        "turn_context",
        {
            "model": model,
            "effort": effort,
            "sandbox_policy": {"type": sandbox},
            "approval_policy": "never",
        },
        "2026-08-29T00:00:00Z",
    )
    content += event(
        "event_msg",
        {
            "type": "token_count",
            "info": {
                "last_token_usage": {
                    "input_tokens": 100,
                    "cached_input_tokens": 40,
                    "output_tokens": 10,
                    "reasoning_output_tokens": 3,
                }
            },
        },
        "2026-08-29T00:00:01Z",
    )
    if completed:
        content += event("event_msg", {"type": "task_complete"}, "2026-08-29T00:00:02Z")
    path.write_text(content, encoding="utf-8")


class TraceReportTests(unittest.TestCase):
    def test_task_filter_reports_root_and_children_without_prompt_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_trace(
                root,
                "root.jsonl",
                session_id="task-a",
                task_id="task-a",
                role=None,
                model="gpt-5.6-sol",
                effort="high",
                sandbox="workspace-write",
            )
            write_trace(
                root,
                "explorer.jsonl",
                session_id="child-a",
                task_id="task-a",
                role="Explorer",
                model="gpt-5.6-luna",
                effort="medium",
                parent="task-a",
            )
            write_trace(
                root,
                "other.jsonl",
                session_id="task-b",
                task_id="task-b",
                role=None,
                model="gpt-5.6-sol",
                effort="high",
            )

            by_role, sessions, scanned, included, malformed, resolved = report.scan(
                root, None, "task-a"
            )
            self.assertEqual((scanned, included, malformed, resolved), (3, 2, 0, "task-a"))
            self.assertEqual(set(by_role), {"main · gpt-5.6-sol", "Explorer · gpt-5.6-luna"})
            rows = report.session_rows(sessions)
            self.assertEqual({row["session_id"] for row in rows}, {"task-a", "child-a"})
            explorer = next(row for row in rows if row["agent_role"] == "Explorer")
            self.assertEqual(explorer["depth"], 1)
            self.assertEqual(explorer["effective_sandbox"], ["read-only"])
            self.assertEqual(explorer["processed_tokens"], 110)
            self.assertNotIn("prompt", json.dumps(rows).lower())

    def test_incomplete_session_is_not_reported_as_completed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_trace(
                root,
                "incomplete.jsonl",
                session_id="task-i",
                task_id="task-i",
                role=None,
                model="gpt-5.6-sol",
                effort="medium",
                completed=False,
            )
            _, sessions, _, included, _, _ = report.scan(root, None, "task-i")
            self.assertEqual(included, 1)
            row = report.session_rows(sessions)[0]
            self.assertEqual(row["terminal_status"], "incomplete")
            self.assertFalse(row["completion_marker_present"])

    def test_usage_math_keeps_cached_and_reasoning_as_subsets(self) -> None:
        row = report.usage_row(
            "Explorer · gpt-5.6-luna",
            {"events": 1, "input": 100, "cached": 40, "output": 10, "reasoning": 3},
        )
        self.assertEqual(row["processed_tokens"], 110)
        self.assertEqual(row["uncached_input_tokens"], 60)
        self.assertEqual(row["reasoning_output_tokens"], 3)


if __name__ == "__main__":
    unittest.main()
