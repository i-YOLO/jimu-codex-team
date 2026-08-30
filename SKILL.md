---
name: jimu-codex-team
description: Coordinate substantial work with an explicitly invoked Jimu Codex agent team. Use only when the user invokes $jimu-codex-team or explicitly asks for the Jimu team, parallel agents, delegation, or independent agent review. Route evidence gathering, bounded execution, and fresh review to the smallest useful set of configured custom agents while the main thread keeps unresolved decisions and final acceptance. Do not use for ordinary single-slice tasks.
---

# Jimu Codex Team

Lead the task from the main thread. Use the smallest useful set of custom agents to isolate noisy discovery, run independent work in parallel, perform bounded execution, or obtain fresh review. Team Mode is optional orchestration, not a mandatory Explorer-to-Executor-to-Reviewer pipeline.

When this Skill activates, immediately send one brief commentary update in the user's language. In Chinese, say exactly:

```text
👾 已开启 Jimu Codex 小队模式。
```

Announce activation once per user task, not once per spawn.

## Runtime Gate

Before any spawn, inspect the model-visible `spawn_agent` schema.

- Every working spawn must explicitly pass `agent_type` as exactly `Explorer`, `Executor`, or `Reviewer`.
- Never omit `agent_type`, never pass `default`, and never use `task_name` to select a profile.
- The only omission exception is one explicitly authorized, no-tool guard self-test during installation or repair verification, as described in the setup reference. It is never a working dispatch.
- If `agent_type` or the intended custom profile is unavailable, do not spawn a generic child. Keep the work in the main thread and report that custom-profile routing is unavailable.
- If a child returns the dispatch-guard message or its trace shows `default` or `subagent/unknown`, reject the output. Repair routing before retrying.
- `agent type is currently not available` is not proof of a missing parameter. It can also mean an unregistered role or a Profile load failure. For installation/repair, inspect the underlying error and active file type before retrying another role.
- Read [references/agent-setup.md](references/agent-setup.md) only for installation, repair, runtime verification, guard enablement, or profile customization.

The `default` profile is a fail-closed dispatch guard, not a working role. Its read-only setting is not an operating-system security boundary; the parent task's live permission mode remains authoritative.

The Skill directory may remain symlinked. Install active Agent Profiles as ordinary TOML files copied from the canonical templates, using `scripts/install-agent-profiles.py`. Check file types and template hashes during setup/repair only, not during every normal task. Validate with the affected Desktop runtime and task, not a different CLI selected from PATH.

## Decomposition And Dispatch

Start with a short decomposition pass. Keep genuinely short or tightly coupled work in the main thread. Delegate only when parallelism, context isolation, lower-cost bounded execution, or independent judgment creates material value after briefing, waiting, inspection, and possible rework are counted.

Each child brief must be self-contained and contain these labeled fields:

- `Outcome`: independently finishable result.
- `Benefit`: material advantage over main-thread execution.
- `Sources`: exact paths, URLs, datasets, or raw artifacts required.
- `Scope`: allowed reads or writes, ownership, exclusions, and external-action authority.
- `Checks`: acceptance criteria and validation owned by the child.
- `Stop when`: bounded completion, blocker, or evidence threshold.
- `Return`: concise report or artifact format.

Do not spawn when `Outcome`, `Benefit`, required `Sources`, `Checks`, or `Stop when` is missing. For a `Reviewer`, also include:

- `Unresolved risk`
- `Evidence`
- `Checks already passed`
- `Do not repeat`

Use `fork_turns="none"` by default and always for a new Reviewer. With fresh context, name every source required for factual claims.

## Role Routing

### Explorer

Use `Explorer` for non-trivial read-only discovery across current web sources, documents, datasets, code, schemas, APIs, logs, and configuration.

- Give independent evidence slices to separate Explorers only when the slices do not duplicate one another.
- Do not tell an Explorer the desired conclusion.
- Do not repeat the same discovery in the main thread; inspect the returned evidence needed for acceptance.

### Executor

Use `Executor` only after the main thread has fixed unresolved architecture, product, editorial, safety, scope, and acceptance decisions.

- Assign an explicit file, module, artifact, or mutable-system ownership boundary.
- Multiple Executors may work in parallel only when write ownership is disjoint and stable.
- Keep novel architecture, weak or visual verification, compiler or exporter design, high-consequence security, and rollback judgment in the main thread.

### Reviewer

Use a fresh `Reviewer` for one concrete unresolved risk after the artifact is stable and relevant checks have passed.

- Reviewer is read-only and reports findings; it does not edit or generate patches.
- For substantial code changes, cover code quality, performance, and reuse as distinct review lenses. Use up to one fresh Reviewer per lens only when parallel capacity is useful.
- Do not ask a Reviewer to repeat broad checks unless the integrity or relevance of those checks is the unresolved risk.

## Ownership And Recovery

- Keep all routing and fan-out in the main thread. Children never spawn descendants.
- Assign one current writer to every file, shared artifact, browser session, account, device, or mutable-system boundary.
- Tell each writer that other work may be active and unrelated changes must be preserved.
- When ownership changes, stop the previous writer and state the handoff before starting the next.
- If a child errors, times out, or is interrupted, inspect shared artifacts and trace evidence before retrying.
- Retry a transient failure at most once and only when no usable result exists. Otherwise recover in the main thread or narrow the remaining work.
- If a Reviewer crosses `Stop when` without a usable result, request a partial verdict once, then interrupt it.

## Interactive Work

When success depends on live UI, browser, device, account, or external interactive state that code inspection and automated checks cannot prove, read [references/interactive-testing.md](references/interactive-testing.md). Keep one active operator per shared interactive environment.

## Acceptance

The main thread keeps unresolved user intent, product, editorial, architecture, safety, permission, and acceptance decisions. Before accepting delegated work:

1. Inspect the actual sources, files, artifacts, diffs, or external-state evidence.
2. Confirm the named checks ran and match the intended behavior.
3. Validate Reviewer findings against the underlying artifact before acting.
4. Apply or delegate only bounded repairs, then rerun relevant checks.
5. Return one coherent final result rather than a transcript of agent activity.

Delegation never expands authority. Do not commit, publish, deploy, send messages, alter external state, or handle sensitive data beyond the user's request.

## Diagnostics

When the user asks whether delegation was useful, wants model or subagent consumption, or requests runtime verification, read [references/evaluation.md](references/evaluation.md) and run:

```bash
python3 scripts/inspect-team-runs.py --task-id current --by-session
```

The script reads retained local session traces only. Report that local traces may omit unavailable or ephemeral sessions and that a completed trace does not prove artifact correctness.
