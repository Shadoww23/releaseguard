"""Packaging checks use only temporary files and never include player saves."""

from __future__ import annotations

import tempfile
import subprocess
import sys
import unittest
import zipfile
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import check_project, package


class ReleaseGuardPackagingTests(unittest.TestCase):
    def test_project_versions_match(self) -> None:
        self.assertRegex(package.project_version(), r"^\d+\.\d+\.\d+")

    def test_preflight_reports_missing_remote_without_exposing_remote_urls(self) -> None:
        with patch.object(
            check_project.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=1, stdout=""),
        ):
            self.assertIn("Connect this checkout to GitHub", check_project.next_action())

        secret_remote = "https://user:fake-token@example.invalid/project.git"
        with patch.object(
            check_project.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout=secret_remote),
        ):
            message = check_project.next_action()
        self.assertIn("latest Windows CI", message)
        self.assertNotIn("fake-token", message)

    def test_source_allowlist_excludes_local_data_and_caches(self) -> None:
        names = {
            path.relative_to(Path(__file__).resolve().parents[1]).as_posix()
            for path in package.package_sources()
        }
        self.assertIn("releaseguard.py", names)
        self.assertIn("FIRST-TEST.md", names)
        self.assertIn("RELEASE-NOTES.md", names)
        self.assertIn("scripts/package.py", names)
        self.assertIn("tests/test_cli.py", names)
        self.assertFalse(any("test-fixtures" in Path(name).parts for name in names))
        self.assertFalse(any("__pycache__" in Path(name).parts for name in names))
        self.assertFalse(any(name.endswith(".pyc") for name in names))

    def test_source_zip_is_readable_and_excludes_player_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "releaseguard-first.zip"
            second_path = Path(directory) / "releaseguard-second.zip"
            package.create_source_archive(first_path)
            package.create_source_archive(second_path)
            with zipfile.ZipFile(first_path) as archive:
                self.assertIsNone(archive.testzip())
                names = set(archive.namelist())
                extracted = Path(directory) / "extracted"
                archive.extractall(extracted)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            result = subprocess.run(
                [sys.executable, str(extracted / "releaseguard.py"), "--version"],
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), f"releaseguard {package.project_version()}")

        self.assertIn("releaseguard.py", names)
        self.assertIn("FIRST-TEST.md", names)
        self.assertIn("RELEASE-NOTES.md", names)
        self.assertIn("scripts/package.py", names)
        self.assertFalse(any("test-fixtures" in Path(name).parts for name in names))

    def test_failed_build_keeps_previous_tester_bundle_intact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            previous = {
                "ReleaseGuard-0.1.0-alpha.zip": b"previous zip",
                "releaseguard_local-0.1.0-py3-none-any.whl": b"previous wheel",
                "ReleaseGuard-0.1.0-alpha-SHA256SUMS.txt": b"previous checksums",
            }
            for name, contents in previous.items():
                (output / name).write_bytes(contents)

            with (
                patch.object(package, "build_wheel", side_effect=RuntimeError("simulated wheel failure")),
                redirect_stderr(StringIO()),
            ):
                result = package.main(["--output-dir", directory])

            self.assertEqual(result, 1)
            for name, contents in previous.items():
                self.assertEqual((output / name).read_bytes(), contents)
            self.assertEqual(set(output.iterdir()), {output / name for name in previous})


if __name__ == "__main__":
    unittest.main()
