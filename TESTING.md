# ReleaseGuard 0.1 Alpha: validation record

Date: 2026-10-20  
Environment: Linux, Python 3.14.  
This is a manual smoke/pretest record, not an independent QA report.

The thirteen CLI smoke tests and five packaging/preflight tests (18 total) pass locally on this environment (Linux, Python 3.14). The suite includes synthetic custom Steam library discovery, mocked Windows registry lookups for Steam and redirected Documents, GTA IV discovery through a redirected Documents folder, refusal to back up symlinked content, cleanup after an interrupted snapshot copy, rejection of a Windows drive-style snapshot name, checks that the tester ZIP excludes personal fixtures and caches, verification that the ZIP runs after extraction, safe handling of a failed package build, and preflight next-action reporting that does not expose remote URLs. The package workflow also installs the wheel offline in an isolated environment and runs its CLI. GitHub Actions is set to run the suite on Linux and Windows with Python 3.10 and 3.14, then build a tester bundle after successful pushes or manual runs. Those remote matrix runs have not happened yet.

## Passed

- Python compilation for the CLI and sample adapter.
- Built a wheel, installed it into a clean virtual environment, and ran its `--version` and `save --help` commands.
- Extracted the source ZIP into a fresh temporary directory, ran `--version`, and completed the sample interrupted-save scenario.
- Save discovery found this machine's Shadow of Mordor Steam save and GTA IV Proton profile in an alternate Steam library.
- Added Windows Steam registry path discovery for nonstandard Steam installs and exercised the registry query using a mock; the real Windows API path awaits a native Windows run.
- Created separate snapshots of both real saves and verified the recorded hashes: one Shadow of Mordor file and five GTA IV profile files.
- Changed a disposable copy of a snapshot and confirmed verification rejected it.
- Confirmed interrupted snapshot copies leave no published partial snapshot, and linked save content is rejected rather than silently omitted.
- Confirmed restore's default dry run left its target unchanged.
- Restored disposable file and folder targets and confirmed each previous target was preserved as a sibling backup.
- Ran the sample scenario successfully through seed, interrupted write, and recovery verification.
- Ran the build scanner against a disposable build: it found identical files and a debug-symbol review candidate, then failed the configured growth gate when a file exceeded the budget.
- Confirmed the shareable ZIP does not contain personal save fixtures.
- Added `scripts/package.py` to build and verify the tester ZIP, wheel, and checksums in one command.
- Added `scripts/check_project.py` so a maintainer can compile, test, and package in one safe preflight; it stops before replacing release files if checks fail.
- Added CI packaging after the full cross-platform test matrix, with a 14-day downloadable artifact.
- Added automatic cancellation of stale same-branch workflows and a 15-minute cap per job to limit wasted CI time.
- Made the local preflight identify the next external gate from Git remote configuration without printing remote URLs.

## Not verified

- Native Windows or macOS execution, or compatibility on Python 3.10/3.11 specifically.
- Loading either real save in its game, restoring over either real profile, or behavior during cloud sync.
- Detecting or repairing logical corruption in a commercial game's proprietary save format.
- A production Unity/Unreal adapter, CI integration in a real studio, or measurements against a shipped game build.

This evidence is enough for a focused alpha: testers can exercise local discovery, snapshot, verification, restore on disposable data, and build diagnostics. It is not a production-readiness or cross-platform compatibility claim.
