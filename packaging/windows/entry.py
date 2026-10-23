"""Windows entry point.

Double-clicked with no arguments: ask for a build folder and run release-check.
Launched from a terminal with arguments: behave like the normal CLI.
"""
from __future__ import annotations

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    source_root = Path(__file__).resolve().parents[2]
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))


def guided() -> int:
    import releaseguard

    print("ReleaseGuard {} - local release readiness checks".format(releaseguard.VERSION))
    print("No Python install is needed. This window runs the normal CLI for you.")
    print()
    raw = input("Path to the packaged game folder (or press Enter for help): ").strip().strip('"')
    if not raw:
        print()
        print("Run ReleaseGuard.exe --help to see every command.")
        print("Examples: analyze, scenario, release-check, save.")
        input("Press Enter to close...")
        return 0
    build = Path(raw).expanduser()
    if not build.is_dir():
        print("That folder was not found: {}".format(build))
        input("Press Enter to close...")
        return 1
    output = Path.home() / "ReleaseGuard-results"
    sys.argv = [
        "ReleaseGuard",
        "release-check",
        str(build),
        "--output",
        str(output),
    ]
    code = releaseguard.main()
    print()
    print("Reports were written under: {}".format(output))
    input("Press Enter to close...")
    return code


if __name__ == "__main__":
    if len(sys.argv) == 1 and sys.stdout.isatty():
        raise SystemExit(guided())
    from releaseguard import main

    raise SystemExit(main())
