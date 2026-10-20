#!/usr/bin/env python3
"""Run the local release checks and package only if every check passes."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NO_REMOTE_NEXT_ACTION = (
    "Connect this checkout to a private GitHub repository to run native Windows CI "
    "and keep an off-device source backup."
)


def run_step(label: str, command: list[str]) -> bool:
    print(f"\n== {label} ==", flush=True)
    try:
        completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    except OSError as exc:
        print(f"FAILED to start {label}: {exc}", file=sys.stderr)
        return False
    if completed.returncode != 0:
        print(f"FAILED: {label} exited with status {completed.returncode}", file=sys.stderr)
        return False
    print(f"PASS: {label}")
    return True


def next_action() -> str:
    """Report the next external gate without exposing the configured remote URL."""
    try:
        remote = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return NO_REMOTE_NEXT_ACTION
    if remote.returncode != 0:
        return NO_REMOTE_NEXT_ACTION
    return "Review the latest Windows CI result, then put the alpha in front of the first tester."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "dist",
        help="destination for validated tester packages (default: project dist/)",
    )
    args = parser.parse_args(argv)

    checks = [
        (
            "Python syntax compilation",
            [sys.executable, "-m", "compileall", "-q", "releaseguard.py", "examples", "scripts", "tests"],
        ),
        (
            "CLI and packaging tests",
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        ),
    ]
    for label, command in checks:
        if not run_step(label, command):
            print("Tester packages were not changed because a check failed.", file=sys.stderr)
            return 1

    package_command = [
        sys.executable,
        "scripts/package.py",
        "--output-dir",
        str(args.output_dir.expanduser().resolve()),
    ]
    if not run_step("Tester package build and integrity checks", package_command):
        print("Tester packages were not published successfully.", file=sys.stderr)
        return 1
    print("\nPASS: project preflight complete")
    print(f"NEXT: {next_action()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
