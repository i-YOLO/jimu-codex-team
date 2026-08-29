# Evaluate Jimu Codex Team

Read this reference only when the user asks whether delegation was worthwhile, requests runtime verification, or wants model and token usage by Agent.

## Establish The Trial

Record the root task ID, baseline artifact, acceptance checks, installed role-to-model mapping, and intended independent slices. Verify actual runtime role, model, effort, and sandbox from retained traces; Profile files alone do not prove runtime selection.

Do not create duplicate work solely to benchmark agents. When comparison matters, keep one comparable slice in the main thread or compare against a stable previous baseline.

## Measure

Run:

```bash
python3 scripts/inspect-team-runs.py --task-id current --by-session --json
```

Record:

- correctness and requirement coverage;
- briefing completeness and missing sources;
- main-thread context avoided;
- briefing, waiting, inspection, and rework cost;
- wall-clock effect from useful parallelism;
- processed input, cached input, output, and reasoning output tokens;
- runtime model, effort, effective sandbox, terminal status, and depth;
- retries, interruptions, partial artifacts, and duplicated work.

Treat `completed` only as evidence that the trace contains a completion marker. It does not prove a correct artifact or useful final report. Local retained traces may omit ephemeral or unavailable sessions.

## Interpret

- Keep Explorer when it returns compact evidence and avoids noisy main-thread discovery.
- Keep Executor for bounded work with deterministic checks and little rework.
- Keep Reviewer only when fresh judgment resolves a named risk.
- Improve decomposition and brief quality before increasing every role's model or effort.
- Change a Profile only after repeated task-scoped evidence shows the role cannot meet its boundary.

Report confirmed evidence separately from one-off impressions.
