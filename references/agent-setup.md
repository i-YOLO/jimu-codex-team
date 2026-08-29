# Agent Profile Setup

Read this reference only for installation, repair, runtime verification, guard enablement, disablement, or model customization.

## Canonical Sources

The four canonical templates live under `assets/agent-profiles/`. Active personal profiles live under `~/.codex/agents/`.

Install the three working profiles first:

- `Explorer.toml`
- `Executor.toml`
- `Reviewer.toml`

Do not install `default.toml` until all three working roles have passed runtime verification in a new Codex task.

## Personal Codex Configuration

Preserve unrelated settings and configure:

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
interrupt_message = true
```

The concurrency cap excludes the primary thread, allowing at most three direct children. Jimu Codex Team still uses the smallest useful team.

## Runtime Verification

After installing or changing profiles, restart Codex or open a new task.

1. Confirm the model-visible `spawn_agent` schema can explicitly select `Explorer`, `Executor`, and `Reviewer` through `agent_type`.
2. Spawn one no-side-effect probe for each working role using `fork_turns="none"`.
3. Inspect retained runtime traces rather than trusting child self-report. Confirm role, model, reasoning effort, and effective sandbox.
4. If `agent_type` remains unavailable, stop. Do not install the guard and do not use `task_name` as a substitute.
5. Only after the working probes pass, install `default.toml`, restart, and run one controlled omission test. The guard must return its exact `DISPATCH BLOCKED` line.
6. Run an explicit `Explorer` probe again to prove the guard did not block valid routing.

The parent task's live sandbox or approval mode can override Profile defaults. A read-only Profile is therefore both a configuration default and a behavioral instruction, not an absolute isolation boundary.

## Disable Or Restore The Guard

Disable only the guard with a recoverable move:

```bash
mkdir -p ~/.codex/agents-disabled
mv ~/.codex/agents/default.toml ~/.codex/agents-disabled/default.toml
```

Restart Codex or open a new task. Explorer, Executor, and Reviewer remain installed. Restore strict dispatch by moving `default.toml` back and restarting again.

## Customization Boundaries

- Keep Explorer and Reviewer read-only.
- Keep mutable workspace ownership with Executor.
- Keep child fan-out disabled through instructions; all routing stays in the main thread.
- Keep Reviewer fresh and independent.
- Keep unresolved decisions and final acceptance in the main thread.
- Ask before substituting an unavailable configured model.
