# ReleaseGuard 0.1 Alpha: validation record

Date: 2026-10-20  
Local environment: Linux, Python 3.14.
This is a smoke/pretest record, not an independent QA report.

The fourteen CLI smoke tests and five packaging/preflight tests (19 total) pass locally on Linux with Python 3.14. The suite includes synthetic custom Steam library discovery, mocked Windows registry lookups for Steam and redirected Documents, GTA IV discovery through a redirected Documents folder, refusal to back up symlinked content, cleanup after an interrupted snapshot copy, rejection of a Windows drive-style snapshot name, checks that the tester ZIP includes its first-test guide but excludes personal fixtures and caches, verification that the ZIP runs after extraction, detection of a deliberately corrupted synthetic save after an unsafe interrupted write, safe handling of a failed package build, and preflight next-action reporting that does not expose remote URLs. The package workflow installs the wheel offline in an isolated environment and runs its CLI.

The latest GitHub Actions run [39514647069](https://github.com/Shadoww23/releaseguard/actions/runs/39514647069) passed on commit `e2ff8bd` on 2026-10-20: all four Linux/Windows and Python 3.10/3.14 smoke jobs passed, followed by the package build and artifact upload including `FIRST-TEST.md`. This establishes automated CI coverage on those runners; it is not a substitute for testing real game saves on a Windows player's PC.

## Passed

- Python compilation for the CLI and sample adapter.
- Built a wheel, installed it into a clean virtual environment, and ran its `--version` and `save --help` commands.
- Extracted the source ZIP into a fresh temporary directory, ran `--version`, and completed both synthetic save reliability scenarios.
- Save discovery found this machine's Shadow of Mordor Steam save and GTA IV Proton profile in an alternate Steam library.
- Added Windows Steam registry path discovery for nonstandard Steam installs and exercised the registry query using a mock; the real Windows API path awaits a native Windows run.
- Created separate snapshots of both real saves and verified the recorded hashes: one Shadow of Mordor file and five GTA IV profile files.
- Changed a disposable copy of a snapshot and confirmed verification rejected it.
- Confirmed interrupted snapshot copies leave no published partial snapshot, and linked save content is rejected rather than silently omitted.
- Confirmed restore's default dry run left its target unchanged.
- Restored disposable file and folder targets and confirmed each previous target was preserved as a sibling backup.
- Ran a negative scenario that intentionally corrupts a synthetic save, interrupts the process, and passes only when the harness detects the unreadable file.
- Ran a positive atomic-write scenario that interrupts a synthetic replacement and verifies the previous committed save stays readable.
- Ran the build scanner against a disposable build: it found identical files and a debug-symbol review candidate, then failed the configured growth gate when a file exceeded the budget.
- Confirmed the shareable ZIP does not contain personal save fixtures.
- Added `scripts/package.py` to build and verify the tester ZIP, wheel, and checksums in one command.
- Added `scripts/check_project.py` so a maintainer can compile, test, and package in one safe preflight; it stops before replacing release files if checks fail.
- Passed the first hosted CI matrix on Windows and Linux with Python 3.10 and 3.14; the package job built and uploaded the tester bundle with 14-day retention.
- Added a bundled developer first-test guide with Windows and Linux commands for both reliability scenarios and privacy guidance for feedback.
- Added automatic cancellation of stale same-branch workflows and a 15-minute cap per job to limit wasted CI time.
- Made the local preflight identify the next external gate from Git remote configuration without printing remote URLs.

## Not verified

- Manual testing on a Windows PC; Windows CI passed, but no real Windows game save has been loaded or restored.
- macOS execution or Python 3.11 compatibility.
- Loading either real save in its game, restoring over either real profile, or behavior during cloud sync.
- Detecting or repairing logical corruption in a commercial game's proprietary save format.
- A production Unity/Unreal adapter, CI integration in a real studio, or measurements against a shipped game build.

This evidence is enough for a focused developer-tool alpha: evaluators can run the synthetic interrupted-save checks and inspect reports. It is not proof of a commercial game's save reliability or a production engine integration.
