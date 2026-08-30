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

### 2. Install Ordinary Working Profiles

Use Python 3.11+ on macOS or Linux; the installer uses only the standard library. Keep the templates as the source of truth and install ordinary TOML runtime copies. The Skill directory may be symlinked, but do not symlink active Profile files.

```bash
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --check
```

Default selection is the three working roles. Matching files are unchanged. Custom files and unknown links are conflicts unless you inspect them and explicitly use `--replace`. Directories, devices, FIFOs, sockets, and a symlinked Agent directory are rejected.

Add or merge this section in `~/.codex/config.toml` only if needed:

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
interrupt_message = true
```

Use `--agents-dir <project>/.codex/agents` for project-scoped copies.

#### Migrate The Previous Symlink Installation

Inspect all four entries first:

```bash
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --check --roles Explorer Executor Reviewer default
```

Move the guard itself into a unique backup directory, then migrate working roles:

```bash
mkdir -p ~/.codex/agents-disabled
if [ -e ~/.codex/agents/default.toml ] || [ -L ~/.codex/agents/default.toml ]; then
  guard_backup=$(mktemp -d ~/.codex/agents-disabled/jimu-guard.XXXXXX)
  mv ~/.codex/agents/default.toml "$guard_backup/default.toml"
fi
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --migrate-links
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --check
```

`--migrate-links` accepts only links to the matching templates in this checkout. Inspect links owned by another checkout before authorizing `--replace`. Do not copy over an existing symlink: that may overwrite its source without replacing the link.

This failure was reproduced on Desktop `0.151.0-alpha.7.1`: linked Profiles caused `os error 62`, surfaced as `agent type is currently not available`, despite earlier successful CLI `0.145.0` probes. This is an observed compatibility issue, not a claim about all Codex versions.

### 3. Verify Desktop Routing, Then Enable The Guard

Test all three working roles in the affected Desktop task and record its actual executable and version. Another `codex` build selected from PATH is not equivalent evidence. Coordinate restart/resume only if configuration reload is needed; do not interrupt unrelated work.

Inspect actual child traces for role, model, effort, completion, tool calls, and effective permissions. Neither a visible role name nor a child's self-report is sufficient.

Only after all three pass:

```bash
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --roles default
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --check --roles Explorer Executor Reviewer default
```

Run one authorized no-tool omission probe. It must return:

```text
DISPATCH BLOCKED: the delegated task was not executed because agent_type was omitted or set to default. Respawn with agent_type=Explorer, Executor, or Reviewer.
```

Then confirm an explicit `Explorer` still runs. This installation self-test is the sole exception to the normal explicit-role rule.

The personal guard replaces Codex's omitted/default fallback across personal tasks. Keep it disabled if routing still fails. To disable it, move it into a unique backup location as above. Restore through the installer after checks pass, not by restoring a known-incompatible link.

### 4. Updates And Recovery

Updates to templates do not silently change runtime copies. Run `--check`, inspect differences, then explicitly synchronize with `--replace` when intended. Originals are preserved under a timestamped sibling `agents-backups/jimu-codex-team/` directory; symlinks are backed up as links. Writes use staged files, directory-bound operations, and rollback on failure. Other Profiles are untouched.

The installer does not edit `config.toml`, start agents, or access the network. File installation is not runtime acceptance. See [Agent Profile Setup](./references/agent-setup.md) for conflict handling and verification details.

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

The tests cover real file installation, symlink migration, O_NOFOLLOW, idempotence, conflicts, backups, rollback, and directory-swap races, as well as Profile contracts, explicit invocation, trace attribution, and token math.

## Repository Layout

```text
jimu-codex-team/
├── SKILL.md
├── agents/openai.yaml
├── assets/agent-profiles/
├── references/
├── scripts/                  # Profile installer and trace report
└── tests/
```

## License

[MIT](./LICENSE)
