#!/usr/bin/env python3
"""Build ReleaseGuard's tester ZIP, universal wheel, and SHA-256 file."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILES = (
    ".gitignore",
    "ITCH-PAGE-DRAFT.md",
    "README.md",
    "TESTING.md",
    "pyproject.toml",
    "releaseguard.py",
)
PACKAGE_DIRECTORIES = ("examples", "scripts", "tests", ".github/workflows")
EXCLUDED_PARTS = {"__pycache__", ".git", "test-fixtures", "build", "dist"}


def project_version() -> str:
    """Read the version from both source and project metadata; fail on drift."""
    metadata = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    source = (PROJECT_ROOT / "releaseguard.py").read_text(encoding="utf-8")
    project_match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', metadata)
    source_match = re.search(r'(?m)^VERSION\s*=\s*"([^"]+)"\s*$', source)
    if project_match is None or source_match is None:
        raise ValueError("could not determine the package version")
    if project_match.group(1) != source_match.group(1):
        raise ValueError(
            "version mismatch: pyproject.toml says "
            f"{project_match.group(1)}, releaseguard.py says {source_match.group(1)}"
        )
    return project_match.group(1)


def package_sources() -> list[Path]:
    """Return a deterministic allowlist of source files, excluding local data."""
    paths = [PROJECT_ROOT / name for name in PACKAGE_FILES]
    for directory_name in PACKAGE_DIRECTORIES:
        directory = PROJECT_ROOT / directory_name
        if not directory.is_dir():
            raise FileNotFoundError(f"required package directory is missing: {directory}")
        for path in directory.rglob("*"):
            relative_parts = path.relative_to(PROJECT_ROOT).parts
            if any(part in EXCLUDED_PARTS for part in relative_parts):
                continue
            if path.is_symlink():
                raise ValueError(f"refusing to package a symbolic link: {path}")
            if path.is_file() and path.suffix != ".pyc":
                paths.append(path)

    for path in paths:
        if path.is_symlink():
            raise ValueError(f"refusing to package a symbolic link: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"required package file is missing: {path}")
    unique = {path.relative_to(PROJECT_ROOT).as_posix(): path for path in paths}
    return [unique[name] for name in sorted(unique, key=str.casefold)]


def create_source_archive(destination: Path) -> None:
    """Write and verify the portable source ZIP without local saves or caches."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    sources = package_sources()
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for source in sources:
                info = zipfile.ZipInfo(source.relative_to(PROJECT_ROOT).as_posix())
                info.date_time = (1980, 1, 1, 0, 0, 0)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        with zipfile.ZipFile(temporary) as archive:
            damaged = archive.testzip()
            if damaged is not None:
                raise OSError(f"created source archive failed its CRC check: {damaged}")
            names = archive.namelist()
            if any(any(part in EXCLUDED_PARTS for part in Path(name).parts) for name in names):
                raise OSError("created source archive contains excluded local or generated data")
        temporary.chmod(0o644)
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_wheel(output_dir: Path) -> Path:
    """Build the universal wheel with the project's declared setuptools backend."""
    try:
        from setuptools.build_meta import build_wheel as setuptools_build_wheel
    except ImportError as exc:
        raise RuntimeError(
            "setuptools is required to build the wheel; install the project's build requirement first"
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    previous_directory = Path.cwd()
    try:
        os.chdir(PROJECT_ROOT)
        filename = setuptools_build_wheel(str(output_dir))
    finally:
        os.chdir(previous_directory)
    wheel = output_dir / filename
    if not wheel.is_file():
        raise OSError(f"wheel builder did not create the expected file: {wheel}")
    with zipfile.ZipFile(wheel) as archive:
        damaged = archive.testzip()
        if damaged is not None:
            raise OSError(f"created wheel failed its CRC check: {damaged}")
    return wheel


def write_checksums(paths: list[Path], destination: Path) -> None:
    lines = []
    for path in sorted(paths, key=lambda item: item.name.casefold()):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        lines.append(f"{digest.hexdigest()}  {path.name}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", prefix=f".{destination.name}.",
            suffix=".tmp", dir=destination.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write("\n".join(lines) + "\n")
        temporary.chmod(0o644)
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "dist",
        help="destination for the ZIP, wheel, and checksums (default: project dist/)",
    )
    args = parser.parse_args(argv)

    try:
        version = project_version()
        output_dir = args.output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        archive_name = f"ReleaseGuard-{version}-alpha.zip"
        checksums_name = f"ReleaseGuard-{version}-alpha-SHA256SUMS.txt"
        with tempfile.TemporaryDirectory(prefix=".releaseguard-package-", dir=output_dir) as temporary_dir:
            staging_dir = Path(temporary_dir)
            staged_archive = staging_dir / archive_name
            create_source_archive(staged_archive)
            staged_wheel = build_wheel(staging_dir)
            staged_checksums = staging_dir / checksums_name
            write_checksums([staged_archive, staged_wheel], staged_checksums)

            # Publish only after all outputs exist and pass their integrity checks.
            archive = output_dir / archive_name
            wheel = output_dir / staged_wheel.name
            checksums = output_dir / checksums_name
            for staged in (staged_archive, staged_wheel, staged_checksums):
                os.replace(staged, output_dir / staged.name)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: packaging failed: {exc}", file=sys.stderr)
        return 1

    print(f"Source ZIP: {archive}")
    print(f"Python wheel: {wheel}")
    print(f"Checksums: {checksums}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
