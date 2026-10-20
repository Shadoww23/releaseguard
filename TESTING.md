# ReleaseGuard 0.1 Alpha: validation record

Date: 2026-10-20  
Environment: Linux, Python 3.14.  
This is a manual smoke/pretest record, not an independent QA report.

The eight standard-library CLI smoke tests in `tests/test_cli.py` all passed locally on this environment (Linux, Python 3.14). The suite includes synthetic custom Steam library discovery and a mocked Windows registry lookup. The included GitHub Actions workflow is set to run it on Linux and Windows with Python 3.10 and 3.14 when the project is pushed to GitHub; those remote matrix runs have not happened yet.

## Passed

- Python compilation for the CLI and sample adapter.
- Built a wheel, installed it into a clean virtual environment, and ran its `--version` and `save --help` commands.
- Extracted the source ZIP into a fresh temporary directory, ran `--version`, and completed the sample interrupted-save scenario.
- Save discovery found this machine's Shadow of Mordor Steam save and GTA IV Proton profile in an alternate Steam library.
- Added Windows Steam registry path discovery for nonstandard Steam installs and exercised the registry query using a mock; the real Windows API path awaits a native Windows run.
- Created separate snapshots of both real saves and verified the recorded hashes: one Shadow of Mordor file and five GTA IV profile files.
- Changed a disposable copy of a snapshot and confirmed verification rejected it.
- Confirmed restore's default dry run left its target unchanged.
- Restored disposable file and folder targets and confirmed each previous target was preserved as a sibling backup.
- Ran the sample scenario successfully through seed, interrupted write, and recovery verification.
- Ran the build scanner against a disposable build: it found identical files and a debug-symbol review candidate, then failed the configured growth gate when a file exceeded the budget.
- Confirmed the shareable ZIP does not contain personal save fixtures.

## Not verified

- Native Windows or macOS execution, or compatibility on Python 3.10/3.11 specifically.
- Loading either real save in its game, restoring over either real profile, or behavior during cloud sync.
- Detecting or repairing logical corruption in a commercial game's proprietary save format.
- A production Unity/Unreal adapter, CI integration in a real studio, or measurements against a shipped game build.

This evidence is enough for a focused alpha: testers can exercise local discovery, snapshot, verification, restore on disposable data, and build diagnostics. It is not a production-readiness or cross-platform compatibility claim.
