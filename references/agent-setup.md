# Agent Profile Setup

Read only for installation, repair, runtime verification, guard enablement, disablement, or model customization. Do not scan configuration again during ordinary task routing.

## Canonical Templates And Runtime Copies

The canonical templates live under `assets/agent-profiles/`. The Skill directory may be a symlink; active personal Profile files under `~/.codex/agents/` must be ordinary TOML copies for this installation method. Do not link those six files.

On 2026-08-30, Desktop `0.151.0-alpha.7.1` failed to apply linked Profiles with `Too many levels of symbolic links (os error 62)`, then exposed only `agent type is currently not available`. Ordinary reading and TOML parsing still succeeded. Prior probes on CLI `0.145.0` did not establish Desktop compatibility. This is an observed version-specific failure, not a claim that every Codex release rejects symlinks.

## Installer

From the Skill source directory, use Python 3.11+ on macOS or Linux (standard library only). Installation requires POSIX directory-fd and no-follow support; unsupported platforms stop rather than silently weakening these protections:

```bash
python3 scripts/install-agent-profiles.py
python3 scripts/install-agent-profiles.py --check
```

Default selection is `Explorer`, `Executor`, `Frontend`, `FrontendFast`, and `Reviewer`. The installer does not modify `config.toml`, start agents, or access the network. It installs exact template bytes as ordinary files and leaves matching copies unchanged.

Options:

- `--check`: read-only file-type and template consistency check; exits nonzero for missing, linked, invalid, or differing files.
- `--roles Explorer Executor Frontend FrontendFast Reviewer default`: explicit subset; `default` is never selected implicitly.
- `--agents-dir PATH`: override the installation directory; defaults to `$CODEX_HOME/agents`, or `~/.codex/agents`.
- `--migrate-links`: migrate only links resolving to the corresponding template in this checkout.
- `--replace`: explicitly replace inspected custom files or unknown links, preserving originals in a backup first.

Different files and unknown links are conflicts by default. Directories, devices, sockets, FIFOs, and a symlinked Agent directory are rejected. The installer resolves all conflicts before writes; each file is staged and atomically replaced through a held directory descriptor, preventing a later directory-link swap from redirecting writes. If installation fails, it restores earlier entries when they have not been concurrently modified, otherwise it reports the retained backup for manual recovery. This handles reported I/O failures; it does not promise full transaction durability during a crash or power loss.

Backups are timestamped under the sibling `agents-backups/jimu-codex-team/` directory, outside active Profiles. Symlinks are backed up as links; their targets are never overwritten. Repeated installation is idempotent. There is no background synchronization: after changing a template, inspect the difference, then explicitly sync it with `--replace` if intended.

## Migrate An Existing Linked Installation

1. Run `--check --roles Explorer Executor Frontend FrontendFast Reviewer default`; record existing file types, link targets, and canonical template hashes.
2. Move any active guard to a unique backup directory before migration. For the personal default path:

   ```bash
   mkdir -p ~/.codex/agents-disabled
   if [ -e ~/.codex/agents/default.toml ] || [ -L ~/.codex/agents/default.toml ]; then
     guard_backup=$(mktemp -d ~/.codex/agents-disabled/jimu-guard.XXXXXX)
     mv ~/.codex/agents/default.toml "$guard_backup/default.toml"
   fi
   ```

3. Run `python3 scripts/install-agent-profiles.py --migrate-links`, then `--check`.
4. Verify the five working roles in the affected Desktop task before reinstalling the guard.

Do not copy directly over an existing symlink: that may overwrite its canonical target without replacing the link. If an old checkout owns the links, inspect it and explicitly authorize `--replace`; do not bypass the conflict silently.

## Personal Codex Configuration

Preserve unrelated settings and use:

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
interrupt_message = true
```

The cap excludes the primary thread. Jimu Codex Team still uses the smallest useful team. Repairing Profile file types does not require changing these settings.

## Runtime Verification

Record the actual Desktop executable and version. On this Mac the executable is `/Applications/ChatGPT.app/Contents/Resources/codex`; do not assume `codex` on PATH is the same build. On other installations discover the running app's executable rather than copying this path blindly.

1. In the affected task, confirm `spawn_agent` accepts exact custom `agent_type` values. A visible role name alone does not prove the Profile can be loaded.
2. Send one bounded no-tool probe to each working role with `fork_turns="none"` and a complete dispatch packet. Do not continue interrupted business work or mutate the project as part of the probe.
3. Inspect actual traces for role, model, effort, terminal status, effective sandbox, and any child tool calls. Do not rely on self-reported role names.
4. If the task needs configuration reload, coordinate a restart/resume; never close a running app or interrupt unrelated work automatically.
5. Only after all five working roles pass, run `python3 scripts/install-agent-profiles.py --roles default` and check all six Profiles.
6. Run exactly one controlled omission probe. This authorized setup self-test is the only exception to the Skill's explicit-role rule. The child must call no tools and return the exact `DISPATCH BLOCKED` line in the guard template. `subagent/unknown` is expected for this one omitted-role trace.
7. Run an explicit `Explorer` probe after the guard test, and a simple explicitly invoked Skill task that should use no children.

If routing remains unavailable, distinguish a missing `agent_type` parameter, an unregistered role, and a Profile loading error from available underlying evidence. Keep the guard disabled; do not substitute generic agents, change models, upgrade Codex, or toggle experimental flags automatically.

The parent task's live permission mode can override Profile defaults. Record effective permissions; do not claim OS-enforced read-only isolation unless it was actually established.

## Disable, Restore, And Customize

Disable the guard by moving its ordinary file to a unique backup location as above. The five working Profiles remain installed. Restore it using the installer only after working-role checks pass; do not restore the known-incompatible symlink as the normal recovery path.

Keep the backed-up links/files for recovery. Report backup locations and any rollback gaps; never delete a user's customized Profile. Customize the canonical template, inspect changes, then synchronize explicitly. Preserve read-only Explorer/Reviewer roles, workspace-write Executor/Frontend/FrontendFast ownership, shallow fan-out, fresh review, user authority, and main-thread final acceptance.
