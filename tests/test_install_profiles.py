from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("install_agent_profiles", ROOT / "scripts/install-agent-profiles.py")
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallProfilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.agents = self.root / "agents"
        self.templates = self.root / "templates"
        self.templates.mkdir()
        for role in installer.ROLES:
            (self.templates / f"{role}.toml").write_bytes((installer.TEMPLATES / f"{role}.toml").read_bytes())

    def install(self, roles=installer.WORKING_ROLES, **kwargs):
        return installer.install_profiles(self.agents, roles, templates=self.templates, **kwargs)

    def links(self, roles=installer.WORKING_ROLES) -> None:
        self.agents.mkdir(exist_ok=True)
        for role in roles:
            (self.agents / f"{role}.toml").symlink_to(self.templates / f"{role}.toml")

    def test_first_install_creates_regular_exact_files_without_guard(self) -> None:
        entries, backup = self.install()
        self.assertIsNone(backup)
        self.assertEqual({entry["action"] for entry in entries}, {"installed"})
        for role in installer.WORKING_ROLES:
            path = self.agents / f"{role}.toml"
            self.assertFalse(path.is_symlink())
            self.assertEqual(path.read_bytes(), (self.templates / path.name).read_bytes())
        self.assertFalse((self.agents / "default.toml").exists())

    def test_repeat_install_preserves_inode_mtime_and_creates_no_backup(self) -> None:
        self.install()
        before = {p.name: installer.fingerprint(p.stat()) for p in self.agents.iterdir()}
        entries, backup = self.install()
        self.assertEqual({entry["action"] for entry in entries}, {"unchanged"})
        self.assertIsNone(backup)
        self.assertEqual(before, {p.name: installer.fingerprint(p.stat()) for p in self.agents.iterdir()})
        self.assertFalse((self.root / "agents-backups").exists())

    def test_known_links_need_explicit_migration(self) -> None:
        self.links()
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertTrue((self.agents / "Explorer.toml").is_symlink())
        self.assertFalse((self.root / "agents-backups").exists())

    def test_migrate_links_preserves_templates_and_backs_up_links(self) -> None:
        self.links()
        original = {p.name: p.read_bytes() for p in self.templates.iterdir()}
        entries, backup = self.install(migrate_links=True)
        self.assertEqual({e["action"] for e in entries}, {"migrated"})
        self.assertIsNotNone(backup)
        self.assertFalse(backup.is_relative_to(self.agents))
        for role in installer.WORKING_ROLES:
            path = self.agents / f"{role}.toml"
            self.assertFalse(path.is_symlink())
            self.assertTrue((backup / path.name).is_symlink())
            self.assertEqual(os.readlink(backup / path.name), str(self.templates / path.name))
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.templates.iterdir()})

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "OS has no O_NOFOLLOW")
    def test_nofollow_rejects_old_link_and_accepts_migrated_file(self) -> None:
        self.links(("Explorer",))
        path = self.agents / "Explorer.toml"
        with self.assertRaises(OSError):
            os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        self.install(("Explorer",), migrate_links=True)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        os.close(fd)

    def test_unknown_link_not_followed_or_migrated_by_known_link_flag(self) -> None:
        self.agents.mkdir()
        private = self.root / "private.toml"
        private.write_text("private content")
        (self.agents / "Explorer.toml").symlink_to(private)
        with self.assertRaises(installer.InstallError):
            self.install(migrate_links=True)
        self.assertEqual(private.read_text(), "private content")
        self.assertFalse((self.agents / "Executor.toml").exists())

    def test_explicit_replace_backs_up_unknown_link_without_touching_target(self) -> None:
        self.agents.mkdir()
        other = self.root / "other.toml"
        other.write_text("unchanged target")
        (self.agents / "Explorer.toml").symlink_to(other)
        _, backup = self.install(("Explorer",), replace=True)
        self.assertEqual(other.read_text(), "unchanged target")
        self.assertTrue((backup / "Explorer.toml").is_symlink())
        self.assertFalse((self.agents / "Explorer.toml").is_symlink())

    def test_dangling_and_cyclic_links_are_conflicts_without_hanging(self) -> None:
        self.agents.mkdir()
        path = self.agents / "Explorer.toml"
        for target in (self.root / "missing.toml", path):
            with self.subTest(target=target):
                path.symlink_to(target)
                with self.assertRaises(installer.InstallError):
                    self.install(("Explorer",), migrate_links=True)
                path.unlink()

    def test_different_ordinary_file_is_preserved_without_replace(self) -> None:
        self.agents.mkdir()
        target = self.agents / "Reviewer.toml"
        target.write_text("user customization")
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual(target.read_text(), "user customization")
        self.assertFalse((self.agents / "Explorer.toml").exists())

    def test_replace_regular_file_keeps_original_backup(self) -> None:
        self.agents.mkdir()
        target = self.agents / "Explorer.toml"
        target.write_text("user customization")
        _, backup = self.install(("Explorer",), replace=True)
        self.assertEqual((backup / target.name).read_text(), "user customization")
        self.assertEqual(target.read_bytes(), (self.templates / target.name).read_bytes())

    def test_directory_target_rejected_even_with_replace(self) -> None:
        self.agents.mkdir()
        (self.agents / "Reviewer.toml").mkdir()
        with self.assertRaises(installer.InstallError):
            self.install(replace=True)
        self.assertFalse((self.agents / "Explorer.toml").exists())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unsupported")
    def test_fifo_target_rejected_without_opening(self) -> None:
        self.agents.mkdir()
        os.mkfifo(self.agents / "Explorer.toml")
        with self.assertRaises(installer.InstallError):
            self.install(replace=True)

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Unix sockets unsupported")
    def test_socket_target_rejected(self) -> None:
        self.agents.mkdir()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(self.agents / "Explorer.toml"))
            with self.assertRaises(installer.InstallError):
                self.install(replace=True)

    def test_symlink_agent_directory_rejected(self) -> None:
        other = self.root / "other"
        other.mkdir()
        self.agents.symlink_to(other, target_is_directory=True)
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual(list(other.iterdir()), [])

    def test_invalid_template_stops_before_any_write(self) -> None:
        (self.templates / "Reviewer.toml").write_text("invalid = [")
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertFalse(self.agents.exists())

    def test_check_is_read_only_for_missing_linked_different_and_valid_files(self) -> None:
        results = installer.check_profiles(self.agents, templates=self.templates)
        self.assertFalse(self.agents.exists())
        self.assertTrue(all(r["status"] == "missing" for r in results))
        self.links()
        results = installer.check_profiles(self.agents, templates=self.templates)
        self.assertTrue(all(r["status"] == "symlink" for r in results))
        self.install(migrate_links=True)
        target = self.agents / "Explorer.toml"
        target.write_text("user customization")
        before = installer.fingerprint(target.stat())
        results = installer.check_profiles(self.agents, templates=self.templates)
        self.assertEqual([r["status"] for r in results], ["content differs", "ok", "ok"])
        self.assertEqual(before, installer.fingerprint(target.stat()))

    def test_check_exit_code_and_default_roles(self) -> None:
        self.assertEqual(installer.parse_args([]).roles, list(installer.WORKING_ROLES))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(["--check", "--agents-dir", str(self.agents)]), 1)
            installer.install_profiles(self.agents)
            self.assertEqual(installer.main(["--check", "--agents-dir", str(self.agents)]), 0)

    def test_guard_requires_explicit_selection(self) -> None:
        self.install()
        self.assertFalse((self.agents / "default.toml").exists())
        self.install(("default",))
        path = self.agents / "default.toml"
        self.assertFalse(path.is_symlink())
        self.assertEqual(path.read_bytes(), (self.templates / path.name).read_bytes())

    def test_write_failure_restores_all_original_links_and_leaves_no_partial_files(self) -> None:
        self.links()
        original_replace = os.replace

        def fail_second_install(source, target, **kwargs):
            if str(source).endswith(".tmp") and Path(target).name == "Executor.toml":
                raise OSError("injected replace failure")
            return original_replace(source, target, **kwargs)

        with mock.patch.object(installer.os, "replace", side_effect=fail_second_install):
            with self.assertRaisesRegex(installer.InstallError, "Prior Profile entries restored"):
                self.install(migrate_links=True)
        for role in installer.WORKING_ROLES:
            self.assertTrue((self.agents / f"{role}.toml").is_symlink())
        self.assertEqual(list(self.agents.glob("*.tmp")), [])

    def test_new_install_failure_removes_only_our_new_files(self) -> None:
        original_stage = installer.stage_file

        def fail_second_stage(directory, role, data, **kwargs):
            if role == "Executor":
                raise OSError("injected staging failure")
            return original_stage(directory, role, data, **kwargs)

        with mock.patch.object(installer, "stage_file", side_effect=fail_second_stage):
            with self.assertRaises(installer.InstallError):
                self.install()
        self.assertEqual(list(self.agents.iterdir()), [])

    def test_source_directory_cannot_be_install_target(self) -> None:
        with self.assertRaises(installer.InstallError):
            installer.install_profiles(self.templates, templates=self.templates, replace=True)

    def test_directory_swap_cannot_redirect_installation_to_templates(self) -> None:
        self.links(("Explorer",))
        original_templates = {p.name: p.read_bytes() for p in self.templates.iterdir()}
        moved = self.root / "original-agents"
        original_replace = os.replace
        swapped = False

        def swap_directory_before_commit(source, target, **kwargs):
            nonlocal swapped
            if str(source).endswith(".tmp") and not swapped:
                swapped = True
                self.agents.rename(moved)
                self.agents.symlink_to(self.templates, target_is_directory=True)
            return original_replace(source, target, **kwargs)

        with mock.patch.object(installer.os, "replace", side_effect=swap_directory_before_commit):
            with self.assertRaisesRegex(installer.InstallError, "directory changed"):
                self.install(("Explorer",), migrate_links=True)
        self.assertEqual(original_templates, {p.name: p.read_bytes() for p in self.templates.iterdir()})
        self.assertTrue((moved / "Explorer.toml").is_symlink())
        self.assertEqual(list(moved.glob("*.tmp")), [])

    def test_staging_write_failure_removes_temporary_file(self) -> None:
        with mock.patch.object(installer.os, "fsync", side_effect=OSError("injected flush failure")):
            with self.assertRaises(installer.InstallError):
                self.install()
        self.assertEqual(list(self.agents.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
