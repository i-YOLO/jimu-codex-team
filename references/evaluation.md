# Evaluate Jimu Codex Team

Read this reference only when the user asks whether delegation was worthwhile, requests runtime verification, or wants model and token usage by Agent.

## Establish The Trial

Record the root task ID, baseline artifact, acceptance checks, installed role-to-model mapping, and intended independent slices. Verify actual runtime role, model, effort, and sandbox from retained traces; Profile files alone do not prove runtime selection.

Record the affected client, executable path, and runtime version. A successful probe using a different CLI build does not establish Desktop compatibility. The installed set is five working profiles (`Explorer`, `Executor`, `Frontend`, `FrontendFast`, and `Reviewer`) plus the `default` guard, six profiles total. During setup/repair, run `python3 scripts/install-agent-profiles.py --check --roles Explorer Executor Frontend FrontendFast Reviewer default` to confirm ordinary files match the templates. Do not add this scan to normal task routing.

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
- Profile file type and template hash during setup, actual child tool calls, and underlying loading errors if a spawn fails;
- retries, interruptions, partial artifacts, and duplicated work.

Treat `completed` only as evidence that the trace contains a completion marker. It does not prove a correct artifact or useful final report. Local retained traces may omit ephemeral or unavailable sessions.

Distinguish installed files, successful runtime routing, and accepted task output. For a no-side-effect probe, require no child tool calls and no business-file changes. When verifying a repair, include the originally affected task rather than only an isolated new CLI session. For the one authorized guard omission test, `subagent/unknown` can be expected; require the exact guard reply and then successful explicit-role routing.

## Interpret

- Keep Explorer when it returns compact evidence and avoids noisy main-thread discovery.
- Keep Executor for bounded work with deterministic checks and little rework.
- Interpret `Frontend` as the normal UI role and use it by default for frontend work, especially new pages, cross-component work, responsive or multi-state work, client integration, and visual ambiguity. Treat `FrontendFast` as supplementary only for fixed design-system/API-contract work that is very localized, low-risk, file-known, covered by deterministic checks, and has a material speed or cost benefit.
- When frontend-role selection is uncertain, choose `Frontend`; treat `FrontendFast` as neither a failure fallback nor a concurrent takeover of an owned slice.
- Keep Reviewer only when fresh judgment resolves a named risk.
- Improve decomposition and brief quality before increasing every role's model or effort.
- Change a Profile only after repeated task-scoped evidence shows the role cannot meet its boundary.

Report confirmed evidence separately from one-off impressions.
