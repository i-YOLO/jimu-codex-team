<p align="right">
  <strong>English</strong> · <a href="./README.zh-CN.md">简体中文</a>
</p>

# Jimu Codex Team

`jimu-codex-team` is an explicitly invoked Codex Skill for coordinating a small, value-based team of custom agents across substantial development, research, analysis, document, data, and content work.

The main thread keeps unresolved product, editorial, architecture, safety, permission, and acceptance decisions. Three working agents handle evidence gathering, bounded execution, and fresh independent review. A separate `default` dispatch guard can fail closed when a spawn omits `agent_type`.

It is an orchestration guide, not a mandatory pipeline and not a replacement for Codex's built-in multi-agent runtime.

## Roles

| Agent type | Model | Effort | Profile default | Purpose |
|---|---|---:|---|---|
| `Explorer` | `gpt-5.6-luna` | Medium | read-only | Gather current evidence from web sources, documents, datasets, code, logs, APIs, schemas, and configuration. |
| `Executor` | `gpt-5.6-luna` | High | workspace-write | Complete clear, bounded, independently verifiable implementation after decisions and ownership are fixed. |
| `Reviewer` | `gpt-5.6-terra` | Medium | read-only | Review one concrete unresolved risk from fresh context without editing. |
| `default` | `gpt-5.6-terra` | Low | read-only | Reject omitted or forbidden default routing and ask the parent to select a working role. |

The parent task's live permission mode can override Profile sandbox defaults. Treat read-only roles as both configuration and behavioral boundaries, then verify effective runtime permissions from traces when isolation matters.

## When To Use It

Good fits include:

- exploring independent parts of a large codebase;
- investigating code, logs, configuration, and tests in parallel;
- splitting implementation across modules with disjoint ownership;
- checking a stable change for code quality, performance, reuse, or regression risk;
- researching multiple primary-source evidence slices;
- auditing documents, datasets, reports, or knowledge bases;
- coordinating content, media, or artifact production with clear ownership and checks.

Keep simple lookups, one-line edits, tightly coupled single-file work, unresolved product decisions, and shared-session interactive work in the main thread.

Each subagent consumes its own tokens and tool time. Delegate only when parallelism, context isolation, lower-cost bounded work, or independent judgment exceeds briefing and inspection cost.

## How Routing Works

Every working spawn must explicitly select one of:

```text
agent_type = Explorer | Executor | Reviewer
```

`task_name` is only a label and never selects a Profile.

Every dispatch packet contains:

```text
Outcome:
Benefit:
Sources:
Scope:
Checks:
Stop when:
Return:
```

A Reviewer packet additionally contains `Unresolved risk`, `Evidence`, `Checks already passed`, and `Do not repeat`.

The Skill uses fresh child context by default, keeps one writer per mutable target, prevents child fan-out, inspects real artifacts before acceptance, and retries a transient failure at most once when no usable result exists.

## Install

### 1. Install the Skill

Direct installation:

```bash
npx skills add i-YOLO/jimu-codex-team
```

This installs the Skill instructions only. The custom Agent Profiles are a separate Codex configuration surface.

For a maintainable source checkout:

```bash
git clone https://github.com/i-YOLO/jimu-codex-team.git ~/.local/share/jimu-codex-team
npx skills add ~/.local/share/jimu-codex-team
```

### 2. Install The Three Working Profiles

Create the personal Agent directory, then link the three working Profiles from the checkout:

```bash
mkdir -p ~/.codex/agents
ln -s ~/.local/share/jimu-codex-team/assets/agent-profiles/Explorer.toml ~/.codex/agents/Explorer.toml
ln -s ~/.local/share/jimu-codex-team/assets/agent-profiles/Executor.toml ~/.codex/agents/Executor.toml
ln -s ~/.local/share/jimu-codex-team/assets/agent-profiles/Reviewer.toml ~/.codex/agents/Reviewer.toml
```

Add or merge this section in `~/.codex/config.toml`:

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
interrupt_message = true
```

Restart Codex or open a new task. Confirm that the model-visible `spawn_agent` schema can select `Explorer`, `Executor`, and `Reviewer` through `agent_type`, then run one no-side-effect probe for each role.

### 3. Enable The Optional Dispatch Guard

Only after all three working roles pass runtime verification:

```bash
ln -s ~/.local/share/jimu-codex-team/assets/agent-profiles/default.toml ~/.codex/agents/default.toml
```

Restart Codex again. A controlled spawn that omits `agent_type` must return:

```text
DISPATCH BLOCKED: the delegated task was not executed because agent_type was omitted or set to default. Respawn with agent_type=Explorer, Executor, or Reviewer.
```

The personal `default` Profile overrides Codex's built-in fallback for omitted/default spawns across personal Codex tasks. If `agent_type` is unavailable, do not enable the guard.

To disable only the guard without removing the three working roles:

```bash
mkdir -p ~/.codex/agents-disabled
mv ~/.codex/agents/default.toml ~/.codex/agents-disabled/default.toml
```

See [Agent Profile Setup](./references/agent-setup.md) for verification and customization boundaries.

## Use

Invoke the Skill explicitly:

```text
$jimu-codex-team investigate why this project fails to build. Check code, dependencies, and configuration in parallel, then fix and verify the confirmed cause.
```

```text
$jimu-codex-team review this branch with separate code-quality, performance, and reuse lenses. Validate the findings and return one severity-ordered report.
```

```text
$jimu-codex-team audit this knowledge base for duplicates, broken links, stale indexes, and sensitive content. Keep write ownership disjoint and verify every repair.
```

You do not need to choose every role yourself. The main thread selects the smallest useful team and may correctly choose no subagents for a simple task.

## Local Runtime Report

The bundled diagnostic reads retained local Codex traces and reports routing metadata, runtime model and effort, effective sandbox, terminal state, timing, and token counters. It never prints prompts or tool content and does not make network requests.

```bash
python3 scripts/inspect-team-runs.py --task-id current --by-session
python3 scripts/inspect-team-runs.py --task-id current --by-session --json
```

Local traces may omit ephemeral or unavailable sessions. A completion marker does not prove artifact correctness.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

The tests validate Profile parsing and role boundaries, explicit-only Skill metadata, dispatch contracts, trace task attribution, runtime metadata, terminal status, and token math.

## Repository Layout

```text
jimu-codex-team/
├── SKILL.md
├── agents/openai.yaml
├── assets/agent-profiles/
├── references/
├── scripts/inspect-team-runs.py
└── tests/
```

## License

[MIT](./LICENSE)
