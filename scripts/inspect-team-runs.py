#!/usr/bin/env python3
"""Inspect locally retained Codex task and subagent runtime metadata.

The report intentionally excludes prompts, tool inputs, tool outputs, and full
session content. It reports only routing metadata, runtime settings, terminal
state, timing, and token counters present in local trace events.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


def default_sessions_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return (Path(codex_home) if codex_home else Path.home() / ".codex") / "sessions"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report local Codex role, runtime, status, timing, and token metadata."
    )
    period = parser.add_mutually_exclusive_group()
    period.add_argument(
        "--days",
        type=int,
        default=1,
        help="Include the last N local calendar days (default: 1).",
    )
    period.add_argument("--all", action="store_true", help="Include all retained sessions.")
    period.add_argument(
        "--task-id",
        metavar="ID|current",
        help="Include one root task and its children; current reads CODEX_THREAD_ID.",
    )
    parser.add_argument("--by-session", action="store_true", help="Show each session separately.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--sessions-root",
        type=Path,
        default=default_sessions_root(),
        help="Override the local sessions directory.",
    )
    args = parser.parse_args()
    if not args.all and args.days < 1:
        parser.error("--days must be at least 1")
    if args.task_id == "current":
        args.task_id = os.environ.get("CODEX_THREAD_ID")
        if not args.task_id:
            parser.error("--task-id current requires CODEX_THREAD_ID")
    return args


def session_date(path: Path, root: Path) -> date:
    try:
        year, month, day = path.relative_to(root).parts[:3]
        return date(int(year), int(month), int(day))
    except (ValueError, IndexError):
        return date.fromtimestamp(path.stat().st_mtime)


def trace_files(root: Path, cutoff: date | None) -> Iterable[Path]:
    for path in root.rglob("*.jsonl"):
        if cutoff is None or session_date(path, root) >= cutoff:
            yield path


def nested_spawn(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("source")
    if not isinstance(source, dict):
        return {}
    subagent = source.get("subagent")
    if not isinstance(subagent, dict):
        return {}
    spawn = subagent.get("thread_spawn")
    return spawn if isinstance(spawn, dict) else {}


def parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def read_trace_metadata(path: Path) -> tuple[dict[str, Any], int]:
    malformed = 0
    try:
        lines = path.open("r", encoding="utf-8")
    except OSError:
        return {}, malformed
    with lines:
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if event.get("type") != "session_meta":
                continue
            payload = event.get("payload") or {}
            spawn = nested_spawn(payload)
            session_id = payload.get("id") or path.stem
            parent = payload.get("parent_thread_id") or spawn.get("parent_thread_id")
            is_child = bool(parent or spawn)
            role = payload.get("agent_role") or spawn.get("agent_role")
            return {
                "path": path,
                "session_id": str(session_id),
                "task_hint": payload.get("session_id"),
                "parent_thread_id": parent,
                "agent_role": role or ("subagent/unknown" if is_child else "main"),
                "agent_path": payload.get("agent_path") or spawn.get("agent_path"),
            }, malformed
    return {}, malformed


def resolve_tasks(metadata: list[dict[str, Any]]) -> None:
    by_session = {item["session_id"]: item for item in metadata}

    def root_task(item: dict[str, Any]) -> str:
        hint = item.get("task_hint")
        if isinstance(hint, str) and hint:
            return hint
        current = item
        seen: set[str] = set()
        while True:
            session_id = str(current["session_id"])
            if session_id in seen:
                return session_id
            seen.add(session_id)
            parent = current.get("parent_thread_id")
            if not isinstance(parent, str) or not parent:
                return session_id
            parent_metadata = by_session.get(parent)
            if parent_metadata is None:
                return parent
            hint = parent_metadata.get("task_hint")
            if isinstance(hint, str) and hint:
                return hint
            current = parent_metadata

    def depth(item: dict[str, Any]) -> int:
        current = item
        seen: set[str] = set()
        value = 0
        while True:
            session_id = str(current["session_id"])
            if session_id in seen:
                return value
            seen.add(session_id)
            parent = current.get("parent_thread_id")
            if not isinstance(parent, str) or parent not in by_session:
                return value
            value += 1
            current = by_session[parent]

    for item in metadata:
        item["task_id"] = root_task(item)
        item["depth"] = depth(item)


def discover(root: Path, cutoff: date | None) -> tuple[list[dict[str, Any]], int, int]:
    metadata: list[dict[str, Any]] = []
    file_count = 0
    malformed = 0
    for path in trace_files(root, cutoff):
        file_count += 1
        item, item_malformed = read_trace_metadata(path)
        malformed += item_malformed
        if item:
            metadata.append(item)
    resolve_tasks(metadata)
    return metadata, file_count, malformed


def resolve_requested_task(metadata: list[dict[str, Any]], requested: str | None) -> str | None:
    if requested is None:
        return None
    for item in metadata:
        if item["session_id"] == requested:
            return str(item["task_id"])
    return requested


def blank_usage() -> dict[str, int]:
    return {"events": 0, "input": 0, "cached": 0, "output": 0, "reasoning": 0}


def add_usage(target: dict[str, int], usage: dict[str, Any]) -> None:
    target["events"] += 1
    target["input"] += int(usage.get("input_tokens") or 0)
    target["cached"] += int(usage.get("cached_input_tokens") or 0)
    target["output"] += int(usage.get("output_tokens") or 0)
    target["reasoning"] += int(usage.get("reasoning_output_tokens") or 0)


def merge_usage(target: dict[str, int], source: dict[str, int]) -> None:
    for key in target:
        target[key] += source[key]


def scan(
    root: Path,
    cutoff: date | None,
    task_id: str | None = None,
) -> tuple[dict[str, dict[str, int]], list[dict[str, Any]], int, int, int, str | None]:
    by_role: dict[str, dict[str, int]] = defaultdict(blank_usage)
    sessions: list[dict[str, Any]] = []
    metadata, file_count, malformed_lines = discover(root, cutoff)
    resolved_task_id = resolve_requested_task(metadata, task_id)
    included_count = 0

    for trace in metadata:
        if resolved_task_id is not None and trace["task_id"] != resolved_task_id:
            continue
        included_count += 1
        model: str | None = None
        effort: str | None = None
        usage_segments: dict[tuple[str, str | None], dict[str, int]] = defaultdict(blank_usage)
        timestamps: list[datetime] = []
        sandboxes: set[str] = set()
        approvals: set[str] = set()
        interrupted_count = 0
        has_complete = False
        last_terminal: str | None = None
        seen_metadata = False

        try:
            lines = trace["path"].open("r", encoding="utf-8")
        except OSError:
            continue
        with lines:
            for line in lines:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    if seen_metadata:
                        malformed_lines += 1
                    continue
                payload = event.get("payload") or {}
                timestamp = parse_timestamp(event.get("timestamp") or payload.get("timestamp"))
                if timestamp:
                    timestamps.append(timestamp)
                if event.get("type") == "session_meta":
                    seen_metadata = True
                elif event.get("type") == "turn_context":
                    model = payload.get("model") or model
                    effort = payload.get("effort")
                    sandbox = payload.get("sandbox_policy")
                    if isinstance(sandbox, dict):
                        sandbox = sandbox.get("type")
                    if isinstance(sandbox, str) and sandbox:
                        sandboxes.add(sandbox)
                    approval = payload.get("approval_policy")
                    if isinstance(approval, str) and approval:
                        approvals.add(approval)
                elif event.get("type") == "event_msg":
                    kind = payload.get("type")
                    if kind == "task_complete":
                        has_complete = True
                        last_terminal = "completed"
                    elif kind == "task_started":
                        last_terminal = None
                    elif kind == "turn_aborted":
                        interrupted_count += 1
                        last_terminal = "interrupted"
                    elif kind == "token_count" and model:
                        usage = (payload.get("info") or {}).get("last_token_usage")
                        if isinstance(usage, dict):
                            add_usage(usage_segments[(model, effort)], usage)

        if not usage_segments and model:
            usage_segments[(model, effort)]
        started = min(timestamps) if timestamps else None
        ended = max(timestamps) if timestamps else None
        role = trace["agent_role"]
        for (segment_model, segment_effort), usage in usage_segments.items():
            merge_usage(by_role[f"{role} · {segment_model}"], usage)
            sessions.append(
                {
                    **{key: value for key, value in trace.items() if key != "path"},
                    "model": segment_model,
                    "effort": segment_effort,
                    "usage": usage,
                    "started_at": started.isoformat().replace("+00:00", "Z") if started else None,
                    "ended_at": ended.isoformat().replace("+00:00", "Z") if ended else None,
                    "elapsed_seconds": (ended - started).total_seconds() if started and ended else None,
                    "terminal_status": last_terminal or "incomplete",
                    "completion_marker_present": has_complete,
                    "interrupted_count": interrupted_count,
                    "effective_sandbox": sorted(sandboxes),
                    "approval_policy": sorted(approvals),
                }
            )

    return dict(by_role), sessions, file_count, included_count, malformed_lines, resolved_task_id


def usage_row(name: str, usage: dict[str, int]) -> dict[str, Any]:
    uncached = max(usage["input"] - usage["cached"], 0)
    return {
        "name": name,
        "token_events": usage["events"],
        "processed_tokens": usage["input"] + usage["output"],
        "input_tokens": usage["input"],
        "cached_input_tokens": usage["cached"],
        "uncached_input_tokens": uncached,
        "output_tokens": usage["output"],
        "reasoning_output_tokens": usage["reasoning"],
    }


def role_rows(by_role: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    return [usage_row(name, usage) for name, usage in sorted(by_role.items())]


def session_rows(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for session in sessions:
        row = usage_row(f"{session['agent_role']} · {session['model']}", session["usage"])
        row.update({key: value for key, value in session.items() if key != "usage"})
        rows.append(row)
    rows.sort(key=lambda row: (row.get("agent_path") or "/root", row["session_id"], row["model"]))
    return rows


def totals(rows: list[dict[str, Any]]) -> dict[str, int]:
    keys = (
        "token_events",
        "processed_tokens",
        "input_tokens",
        "cached_input_tokens",
        "uncached_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
    )
    return {key: sum(int(row[key]) for row in rows) for key in keys}


def print_role_table(rows: list[dict[str, Any]]) -> None:
    print("By role and model")
    print(
        f"{'Role / Model':<34} {'Processed':>12} {'Uncached':>11} "
        f"{'Cached':>11} {'Output':>10} {'Reason':>10}"
    )
    print("-" * 94)
    for row in rows:
        print(
            f"{row['name']:<34} {row['processed_tokens']:>12,} "
            f"{row['uncached_input_tokens']:>11,} {row['cached_input_tokens']:>11,} "
            f"{row['output_tokens']:>10,} {row['reasoning_output_tokens']:>10,}"
        )
    summary = totals(rows)
    print("-" * 94)
    print(
        f"{'TOTAL':<34} {summary['processed_tokens']:>12,} "
        f"{summary['uncached_input_tokens']:>11,} {summary['cached_input_tokens']:>11,} "
        f"{summary['output_tokens']:>10,} {summary['reasoning_output_tokens']:>10,}"
    )
    print()


def print_session_table(rows: list[dict[str, Any]]) -> None:
    print("By session")
    print(
        f"{'Role / Model':<28} {'Status':<11} {'Depth':>5} {'Elapsed':>9} "
        f"{'Sandbox':<18} {'Processed':>11}"
    )
    print("-" * 92)
    for row in rows:
        elapsed = f"{row['elapsed_seconds']:.1f}s" if row.get("elapsed_seconds") is not None else "n/a"
        sandbox = ",".join(row.get("effective_sandbox") or []) or "n/a"
        print(
            f"{row['name']:<28} {row['terminal_status']:<11} {row['depth']:>5} "
            f"{elapsed:>9} {sandbox:<18} {row['processed_tokens']:>11,}"
        )
    print()


def main() -> int:
    args = parse_args()
    root = args.sessions_root.expanduser().resolve()
    if not root.is_dir():
        print(f"Sessions directory not found: {root}", file=sys.stderr)
        return 2

    cutoff = None if args.all or args.task_id else date.today() - timedelta(days=args.days - 1)
    by_role, sessions, scanned, included, malformed, task_id = scan(root, cutoff, args.task_id)
    if args.task_id and not included:
        print(f"Task not found in retained local sessions: {args.task_id}", file=sys.stderr)
        return 2

    roles = role_rows(by_role)
    details = session_rows(sessions)
    status_counts = {
        state: sum(1 for row in details if row["terminal_status"] == state)
        for state in ("completed", "interrupted", "incomplete")
    }
    period = f"task {task_id}" if task_id else (
        "all retained sessions" if cutoff is None else f"{cutoff.isoformat()} through {date.today().isoformat()}"
    )
    limitations = [
        "Local retained sessions only; ephemeral and unavailable sessions are excluded.",
        "A completion marker proves trace state, not artifact correctness or a useful final report.",
        "Runtime sandbox and approval values come from retained turn_context events.",
    ]

    if args.json:
        print(
            json.dumps(
                {
                    "period": period,
                    "task_id": task_id,
                    "sessions_root": str(root),
                    "files_scanned": scanned,
                    "session_files_included": included,
                    "malformed_lines_skipped": malformed,
                    "summary": totals(roles),
                    "roles": roles,
                    "sessions": details if args.by_session else [],
                    "session_status_counts": status_counts,
                    "max_subagent_depth": max((row["depth"] for row in details), default=0),
                    "limitations": limitations,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"Jimu Codex Team local trace report · {period}")
    print(f"Scanned {scanned} session files · included {included} · malformed lines skipped {malformed}")
    print("Processed tokens = input (cached included) + output; reasoning is already included in output.")
    print()
    print_role_table(roles)
    if args.by_session:
        print_session_table(details)
    print("Limitations: " + " ".join(limitations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
