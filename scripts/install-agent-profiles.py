#!/usr/bin/env python3
"""Install ordinary Codex Profile files without following destination symlinks.

Python 3.11+ standard library only. Does not edit config.toml, start agents,
or access the network. The guard is excluded unless explicitly selected.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


ROLES = ("Explorer", "Executor", "Reviewer", "default")
WORKING_ROLES = ROLES[:3]
TEMPLATES = Path(__file__).resolve().parents[1] / "assets" / "agent-profiles"


class InstallError(Exception):
    """A conflict or failed operation that must not be silently ignored."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def absolute(path: Path) -> Path:
    # Do not resolve the last component: it may be the symlink being migrated.
    return Path(os.path.abspath(path.expanduser()))


def fingerprint(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns)


def file_stat(path: Path, dir_fd: int | None = None) -> os.stat_result:
    return os.stat(path.name if dir_fd is not None else path,
                   dir_fd=dir_fd, follow_symlinks=False)


def read_regular(path: Path, dir_fd: int | None = None) -> bytes:
    before = file_stat(path, dir_fd)
    if not stat.S_ISREG(before.st_mode):
        raise InstallError(f"Not an ordinary file: {path}")
    fd = os.open(path.name if dir_fd is not None else path,
                 os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=dir_fd)
    with os.fdopen(fd, "rb") as stream:
        if fingerprint(os.fstat(stream.fileno())) != fingerprint(before):
            raise InstallError(f"File changed while opening: {path}")
        data = stream.read()
        if fingerprint(os.fstat(stream.fileno())) != fingerprint(before):
            raise InstallError(f"File changed while reading: {path}")
    if fingerprint(file_stat(path, dir_fd)) != fingerprint(before):
        raise InstallError(f"File changed after reading: {path}")
    return data


def validate_template(path: Path, role: str) -> bytes:
    data = read_regular(path)
    try:
        config = tomllib.loads(data.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise InstallError(f"Invalid template {path}: {exc}") from exc
    for key in ("name", "description", "developer_instructions", "model",
                "model_reasoning_effort", "sandbox_mode"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise InstallError(f"Template {path} requires nonempty {key}")
    if config["name"] != role:
        raise InstallError(f"Template name differs from selected role: {path}")
    return data


def validate_destination_dir(agents_dir: Path, templates: Path) -> None:
    if agents_dir == agents_dir.parent:
        raise InstallError("A filesystem root is not an Agent directory")
    if agents_dir.is_symlink():
        raise InstallError(f"Agent directory itself is a symlink: {agents_dir}")
    if agents_dir.exists() and not agents_dir.is_dir():
        raise InstallError(f"Agent directory is not a directory: {agents_dir}")
    resolved = agents_dir.resolve()
    if resolved == templates.resolve() or resolved.is_relative_to(templates.resolve()):
        raise InstallError("Do not install over the canonical templates")


def snapshot(path: Path, template: Path, dir_fd: int | None = None) -> dict:
    try:
        info = file_stat(path, dir_fd)
    except FileNotFoundError:
        return {"kind": "missing", "fingerprint": None, "sha256": None}
    result = {"fingerprint": fingerprint(info), "sha256": None}
    if stat.S_ISLNK(info.st_mode):
        link = os.readlink(path.name if dir_fd is not None else path, dir_fd=dir_fd)
        result.update(kind="symlink", link_target=link, known_link=False)
        try:
            linked_path = Path(link) if os.path.isabs(link) else path.parent / link
            result["known_link"] = linked_path.resolve(strict=True) == template.resolve(strict=True)
        except (OSError, RuntimeError):
            pass
        # Never open an unknown link target, which may contain private data.
    elif stat.S_ISREG(info.st_mode):
        result.update(kind="regular", sha256=digest(read_regular(path, dir_fd)))
    else:
        result.update(kind="unsupported")
    return result


def prepare(agents_dir: Path, roles: tuple[str, ...], templates: Path) -> list[dict]:
    if not roles or len(set(roles)) != len(roles) or any(role not in ROLES for role in roles):
        raise InstallError("Select unique, supported roles")
    validate_destination_dir(agents_dir, templates)
    result = []
    for role in roles:
        source = templates / f"{role}.toml"
        data = validate_template(source, role)
        target = agents_dir / f"{role}.toml"
        current = snapshot(target, source)
        result.append({"role": role, "source": source, "data": data,
                       "source_sha256": digest(data), "target": target,
                       "before": current})
    return result


def check_profiles(agents_dir: Path, roles: tuple[str, ...] = WORKING_ROLES,
                   templates: Path = TEMPLATES) -> list[dict]:
    entries = prepare(absolute(agents_dir), roles, templates)
    for entry in entries:
        state = entry["before"]
        entry["ok"] = state["kind"] == "regular" and state["sha256"] == entry["source_sha256"]
        entry["status"] = "ok" if entry["ok"] else (
            "content differs" if state["kind"] == "regular" else state["kind"]
        )
    return entries


def directory_flags() -> int:
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise InstallError("Safe installation requires POSIX directory-fd and O_NOFOLLOW support")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def verify_directory_binding(path: Path, dir_fd: int) -> None:
    now, held = path.lstat(), os.fstat(dir_fd)
    if not stat.S_ISDIR(now.st_mode) or (now.st_dev, now.st_ino) != (held.st_dev, held.st_ino):
        raise InstallError(f"Agent directory changed during installation: {path}")


def create_backup_dir(agents_dir: Path, parent_fd: int) -> tuple[Path, int]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    parts = (f"{agents_dir.name}-backups", "jimu-codex-team", f"{stamp}-{uuid4().hex[:8]}")
    held = os.dup(parent_fd)
    try:
        for index, name in enumerate(parts):
            try:
                os.mkdir(name, mode=0o700, dir_fd=held)
            except FileExistsError:
                if index == len(parts) - 1:
                    raise
            child = os.open(name, directory_flags(), dir_fd=held)
            os.close(held)
            held = child
        return agents_dir.parent.joinpath(*parts), held
    except BaseException:
        os.close(held)
        raise


def stage_file(agents_dir: Path, role: str, data: bytes, *, dir_fd: int) -> Path:
    name = f".jimu-{role}-{uuid4().hex}.tmp"
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o644, dir_fd=dir_fd)
    staged = agents_dir / name
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o644)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if read_regular(staged, dir_fd) != data:
            raise InstallError(f"Staged copy differs from template: {role}")
        return staged
    except BaseException:
        os.unlink(name, dir_fd=dir_fd)
        raise


def restore_change(change: dict, agents_fd: int, backup_fd: int | None) -> None:
    target, backup = change["target"], change["backup"]
    current = snapshot(target, change["source"], agents_fd)
    if current["kind"] != "missing":
        if current["kind"] != "regular" or current["sha256"] != change["sha256"]:
            raise InstallError(f"Concurrent edit; restore manually from {backup}: {target}")
    if backup is not None:
        os.replace(backup.name, target.name, src_dir_fd=backup_fd, dst_dir_fd=agents_fd)
    elif current["kind"] != "missing":
        os.unlink(target.name, dir_fd=agents_fd)  # Only remove the exact newly installed bytes.


def install_profiles(agents_dir: Path, roles: tuple[str, ...] = WORKING_ROLES,
                     *, migrate_links: bool = False, replace: bool = False,
                     templates: Path = TEMPLATES) -> tuple[list[dict], Path | None]:
    agents_dir = absolute(agents_dir)
    entries = prepare(agents_dir, roles, templates)
    # Resolve all conflicts before creating directories, backups, or files.
    for entry in entries:
        state = entry["before"]
        if state["kind"] == "unsupported":
            raise InstallError(f"Unsupported destination: {entry['target']}")
        if state["kind"] == "regular":
            if state["sha256"] == entry["source_sha256"]:
                entry["action"] = "unchanged"
                continue
            if not replace:
                raise InstallError(f"Custom content preserved; inspect before --replace: {entry['target']}")
        if state["kind"] == "symlink" and not (replace or (migrate_links and state["known_link"])):
            hint = "--migrate-links" if state["known_link"] else "explicit --replace after inspection"
            raise InstallError(f"Symlink preserved; requires {hint}: {entry['target']}")
        entry["action"] = "migrated" if state["kind"] == "symlink" else (
            "installed" if state["kind"] == "missing" else "replaced"
        )
    if all(entry["action"] == "unchanged" for entry in entries):
        return entries, None

    directory_flags()  # Fail before writes on unsupported platforms.
    agents_dir.parent.mkdir(parents=True, exist_ok=True)
    parent_fd = os.open(agents_dir.parent, directory_flags())
    agents_fd = None
    backup_fd = None
    backup_dir = None
    changes: list[dict] = []
    try:
        try:
            os.mkdir(agents_dir.name, dir_fd=parent_fd)
        except FileExistsError:
            pass
        agents_fd = os.open(agents_dir.name, directory_flags(), dir_fd=parent_fd)
        validate_destination_dir(agents_dir, templates)
        verify_directory_binding(agents_dir, agents_fd)
        for entry in entries:
            if entry["action"] == "unchanged":
                continue
            verify_directory_binding(agents_dir, agents_fd)
            staged = stage_file(agents_dir, entry["role"], entry["data"], dir_fd=agents_fd)
            try:
                if snapshot(entry["target"], entry["source"], agents_fd) != entry["before"]:
                    raise InstallError(f"Destination changed after preflight: {entry['target']}")
                backup = None
                if entry["before"]["kind"] != "missing":
                    if backup_dir is None:
                        backup_dir, backup_fd = create_backup_dir(agents_dir, parent_fd)
                    backup = backup_dir / entry["target"].name
                    os.replace(entry["target"].name, backup.name,
                               src_dir_fd=agents_fd, dst_dir_fd=backup_fd)
                changes.append({"target": entry["target"], "backup": backup,
                                "source": entry["source"], "sha256": entry["source_sha256"]})
                os.replace(staged.name, entry["target"].name,
                           src_dir_fd=agents_fd, dst_dir_fd=agents_fd)
                if read_regular(entry["target"], agents_fd) != entry["data"]:
                    raise InstallError(f"Installed bytes differ: {entry['target']}")
                verify_directory_binding(agents_dir, agents_fd)
            finally:
                try:
                    os.unlink(staged.name, dir_fd=agents_fd)
                except FileNotFoundError:
                    pass
    except (OSError, InstallError) as exc:
        failures = []
        for change in reversed(changes):
            try:
                restore_change(change, agents_fd, backup_fd)
            except (OSError, InstallError) as rollback_exc:
                failures.append(str(rollback_exc))
        detail = " Rollback issues: " + "; ".join(failures) if failures else " Prior Profile entries restored."
        raise InstallError(f"Installation failed: {exc}.{detail} Backup: {backup_dir}") from exc
    finally:
        for fd in (backup_fd, agents_fd, parent_fd):
            if fd is not None:
                os.close(fd)
    return entries, backup_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only; exit 1 for missing, linked, or differing files.")
    parser.add_argument("--roles", nargs="+", choices=ROLES, default=list(WORKING_ROLES))
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    parser.add_argument("--agents-dir", type=Path, default=codex_home / "agents")
    parser.add_argument("--migrate-links", action="store_true", help="Migrate only links to this checkout's canonical templates.")
    parser.add_argument("--replace", action="store_true", help="Explicitly replace differing ordinary files or unknown links after backup.")
    args = parser.parse_args(argv)
    if args.check and (args.migrate_links or args.replace):
        parser.error("--check cannot be combined with write authorization flags")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.check:
            entries = check_profiles(args.agents_dir, tuple(args.roles))
            backup = None
        else:
            entries, backup = install_profiles(args.agents_dir, tuple(args.roles),
                                               migrate_links=args.migrate_links, replace=args.replace)
        for entry in entries:
            state = entry["before"]
            print(f"{entry['role']}: {entry.get('status', entry.get('action'))}; before={state['kind']}; "
                  f"source_sha256={entry['source_sha256']}; prior_sha256={state['sha256']}")
            if state["kind"] == "symlink":
                print(f"  prior_link_target={state['link_target']}")
        if backup is not None:
            print(f"Backup directory: {backup}")
        if not args.check:
            print("Files installed; runtime role routing is NOT yet verified by this command.")
            if "default" in args.roles:
                print("Guard installed: verify omitted dispatch is blocked AND an explicit working role still runs.")
        return 1 if args.check and not all(entry["ok"] for entry in entries) else 0
    except (InstallError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
