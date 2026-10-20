"""End-user CLI smoke tests; all save data here is synthetic and disposable."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

import releaseguard


PROJECT = Path(__file__).resolve().parents[1]
CLI = PROJECT / "releaseguard.py"


class ReleaseGuardCliTests(unittest.TestCase):
    def run_cli(self, *args: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *(str(arg) for arg in args)],
            cwd=PROJECT,
            text=True,
            capture_output=True,
            timeout=30,
        )

    def test_version_and_help(self) -> None:
        version = self.run_cli("--version")
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertIn("0.1.0", version.stdout)
        help_result = self.run_cli("save", "--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("restore", help_result.stdout)

    def test_snapshot_detects_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "save.sav"
            source.write_bytes(b"known-good-save")
            snapshot_root = root / "snapshots"
            made = self.run_cli("save", "snapshot", source, "--output", snapshot_root, "--name", "before")
            self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
            checked = self.run_cli("save", "verify", snapshot_root / "before")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

            copied_save = snapshot_root / "before/data/save.sav"
            copied_save.write_bytes(b"changed-save")
            changed = self.run_cli("save", "verify", snapshot_root / "before")
            self.assertEqual(changed.returncode, 1, changed.stdout + changed.stderr)
            self.assertIn("FAIL", changed.stdout)

    def test_folder_restore_is_dry_run_first_and_keeps_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "slot.sav").write_bytes(b"snapshot-progress")
            snapshot_root = root / "snapshots"
            made = self.run_cli("save", "snapshot", source, "--output", snapshot_root, "--name", "good")
            self.assertEqual(made.returncode, 0, made.stdout + made.stderr)

            target = root / "live-save"
            target.mkdir()
            (target / "slot.sav").write_bytes(b"newer-or-damaged")
            dry_run = self.run_cli("save", "restore", snapshot_root / "good", target)
            self.assertEqual(dry_run.returncode, 0, dry_run.stdout + dry_run.stderr)
            self.assertIn("DRY RUN", dry_run.stdout)
            self.assertEqual((target / "slot.sav").read_bytes(), b"newer-or-damaged")

            applied = self.run_cli("save", "restore", snapshot_root / "good", target, "--apply")
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            self.assertEqual((target / "slot.sav").read_bytes(), b"snapshot-progress")
            backups = list(root.glob("live-save.releaseguard-backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "slot.sav").read_bytes(), b"newer-or-damaged")

    def test_file_restore_preserves_previous_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "good.sav"
            source.write_bytes(b"good")
            snapshot_root = root / "snapshots"
            made = self.run_cli("save", "snapshot", source, "--output", snapshot_root, "--name", "good")
            self.assertEqual(made.returncode, 0, made.stdout + made.stderr)

            target = root / "live.sav"
            target.write_bytes(b"old")
            applied = self.run_cli("save", "restore", snapshot_root / "good", target, "--apply")
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            self.assertEqual(target.read_bytes(), b"good")
            backups = list(root.glob("live.sav.releaseguard-backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), b"old")

    def test_build_size_report_and_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / "build"
            build.mkdir()
            (build / "debug.pdb").write_bytes(b"symbols")
            (build / "copy-a.dat").write_bytes(b"same bytes")
            (build / "copy-b.dat").write_bytes(b"same bytes")
            baseline = root / "baseline.json"
            report = self.run_cli(
                "analyze", build, "--find-duplicates", "--write-baseline", baseline,
                "--report", root / "first.json",
            )
            self.assertEqual(report.returncode, 0, report.stdout + report.stderr)
            self.assertIn("Exact duplicate files: 2", report.stdout)
            self.assertIn("debug symbols", report.stdout)

            (build / "large.asset").write_bytes(b"x" * (2 * 1024 * 1024))
            gated = self.run_cli(
                "analyze", build, "--baseline", baseline, "--max-growth-mib", "1",
                "--report", root / "second.json",
            )
            self.assertEqual(gated.returncode, 1, gated.stdout + gated.stderr)
            self.assertIn("FAIL: build grew", gated.stdout)

    def test_sample_interrupted_save_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli(
                "scenario", PROJECT / "examples/save-recovery.json",
                "--output", Path(directory) / "results",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS: all scenario steps passed", result.stdout)

    def test_steam_save_discovery_reads_custom_library_vdf(self) -> None:
        # Uses a synthetic Steam layout so the test never reads or changes a
        # real player's saves. Forward slashes are valid in Steam's VDF on Windows.
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            steam = home / ".steam/steam"
            (steam / "steamapps").mkdir(parents=True)
            library = home / "External Games Library"
            (library / "steamapps").mkdir(parents=True)
            vdf_path = library.as_posix().replace("\\", "\\\\")
            (steam / "steamapps/libraryfolders.vdf").write_text(
                '"libraryfolders" { "0" { "path" "' + vdf_path + '" } }',
                encoding="utf-8",
            )

            with patch.object(releaseguard.Path, "home", return_value=home):
                found = releaseguard.steam_library_roots()

            self.assertIn(library.resolve(), found)

    def test_windows_steam_registry_lookup_checks_supported_keys(self) -> None:
        # Exercise the Windows registry lookup deterministically on any host.
        key_values = {
            ("HKCU", r"Software\Valve\Steam", "SteamPath"): r"D:\Games\Steam",
            ("HKLM", r"Software\WOW6432Node\Valve\Steam", "InstallPath"): r"E:\Steam",
        }
        registry = SimpleNamespace(
            HKEY_CURRENT_USER="HKCU",
            HKEY_LOCAL_MACHINE="HKLM",
            OpenKey=lambda hive, key: _FakeRegistryKey((hive, key)),
        )

        def query_value(reg_key: tuple[str, str], name: str) -> tuple[str, int]:
            try:
                return key_values[(reg_key[0], reg_key[1], name)], 1
            except KeyError as error:
                raise OSError("registry value missing") from error

        registry.QueryValueEx = query_value
        paths = releaseguard.windows_steam_registry_paths(registry)

        self.assertEqual(
            paths,
            [Path(r"D:\Games\Steam"), Path(r"E:\Steam")],
        )


class _FakeRegistryKey:
    def __init__(self, key: tuple[str, str]) -> None:
        self.key = key

    def __enter__(self) -> tuple[str, str]:
        return self.key

    def __exit__(self, *args: object) -> None:
        return None


if __name__ == "__main__":
    unittest.main()
