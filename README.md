# ReleaseGuard 0.1 Alpha — Game Release Readiness Checks

ReleaseGuard is a local-first CLI prototype for game teams to run save, crash/stability, timing, and packaged-build checks together before release. Its `release-check` command combines game-authored scenarios with build size/content review into one CI-friendly pass or failure report. It has no account, hosted service, telemetry, or runtime dependencies. The Windows build is a self-contained executable; the Linux archive needs Python 3.10 or newer.

ReleaseGuard is part of [Brlinkin](https://shadoww23.github.io/brlinkin/), a small suite of local-first tools for Linux gaming and game releases.

## Common problems this solves

- Testing whether an interrupted save write corrupts player progress.
- Adding save-integrity checks to a game's CI pipeline.
- Gating a release on build size, duplicate assets, and development leftovers.
- Turning game-authored stability and timing scenarios into one pass/fail report.

See [docs/PROBLEMS.md](docs/PROBLEMS.md) for commands and limits.

## What works in this alpha

- **Test save reliability:** execute trusted game-authored commands from a JSON manifest, interrupt a test process, capture logs, and report failed recovery checks. The bundled examples demonstrate detection of a synthetic corrupt save and survival of an interrupted atomic write; they are not tests of a commercial game.
- **Gate repeatable stability and timing checks:** scenarios can launch a test build, capture output, enforce exit-code expectations, interrupt a process, and fail when a configured step duration is exceeded. These are test hooks and budgets, not an automatic crash diagnosis system or a performance profiler.
- **Review packaged builds:** report build size, large files, duplicate files, likely development leftovers, and size changes against a baseline. It does not modify or optimize the build.
- **Protect selected player saves:** locate common Shadow of Mordor and GTA IV save paths, including Windows Steam installs and redirected Documents folders; copy a selected file or folder into a hashed snapshot, verify it, and restore it with a dry run and preserved pre-restore backup.

This is an early alpha, not a drop-in engine plugin. Game teams must provide commands that launch their test build, validate game-specific save contents, and exercise representative gameplay for stability or timing checks. ReleaseGuard cannot determine whether an arbitrary proprietary save is logically valid without that game-specific validator, diagnose every crash, or automatically optimize a game.

## Quick start

Download the win64 zip [from the alpha release](https://github.com/Shadoww23/releaseguard/releases/tag/v0.1.0-alpha), extract it, and double-click `ReleaseGuard.exe`. Paste the path to a packaged game build; the guided check writes reports to `%USERPROFILE%\ReleaseGuard-results`. The alpha executable is unsigned, so Windows SmartScreen may ask you to choose **More info** then **Run anyway** after you verify the SHA-256 from the same release.

For the full CLI, open PowerShell in the extracted folder:

```powershell
.\ReleaseGuard.exe --version
.\ReleaseGuard.exe release-check "D:\Builds\MyGame" --output "$HOME\ReleaseGuard-results"
```

The Python archive still works for development and CI:

```powershell
py -3 releaseguard.py --version
py -3 releaseguard.py release-check "D:\Builds\MyGame" --output "$HOME\ReleaseGuard-results"
```

**Linux**

```sh
python3 releaseguard.py --version
python3 releaseguard.py release-check "$HOME/builds/MyGame" --output "$HOME/ReleaseGuard-results"
```

ReleaseGuard writes a JSON report and points out how to add game-specific checks. To include the two synthetic save demonstrations in the same release check, add the `--scenario examples/save-corruption-detection.json --scenario examples/save-recovery.json` options. They use disposable synthetic files, not your game's save format. For the guided test and feedback checklist, follow [FIRST-TEST.md](FIRST-TEST.md). See [RELEASE-NOTES.md](RELEASE-NOTES.md) for scope and alpha limits.

## Run the unified release gate

Run the packaged-build review and both sample reliability scenarios as one command:

```sh
python releaseguard.py release-check ./path/to/packaged-build \
  --max-size-mib 2048 \
  --output ./releaseguard-results
```

PowerShell uses the same options with `py -3 releaseguard.py`. The command writes a build report and `release-check-report.json`. Add scenarios with repeated `--scenario path/to/check.json` options. Add a previous inventory with `--baseline build-baseline.json --max-growth-mib 100`; establish the inventory with `--write-baseline build-baseline.json`. A scenario can set `max_duration_seconds` on representative test steps to enforce a runtime budget. That measures the step duration only; it does not profile frame time, GPU usage, or explain a regression.

The automated CI suite runs on Windows and Linux with Python 3.10 and 3.14. The examples do not validate a commercial game or engine. Core commands work offline. A scenario runs the exact local commands declared in its manifest, so only run scenarios you trust.

## Where files are stored

ReleaseGuard does not keep a central database or copy saves automatically. It reads source saves in place. A snapshot is written only to the folder you pass with `--output`; reports and scenario logs go to the paths you pass on the command line. If you choose a removable drive as the output, the backup stays there. The extracted program folder can live anywhere and contains no user profile data by default.

The project keeps no user data in its program folder by default. Sample fixtures used for development are excluded from the portable package. Do not include personal save files when sharing feedback.

The project repository and CI do not receive player save data. Keep snapshots in the destination you choose. This alpha does not encrypt snapshots or upload them; do not place unencrypted save snapshots in a shared or third-party cloud folder.

Run the repeatable smoke suite from the extracted project folder with `python -m unittest discover -s tests -v`.

## Build a tester bundle

Project maintainers can run the full local preflight with one command. It compiles the project, runs all tests, and only then builds the alpha ZIP, Python wheel, and SHA-256 checksum file:

```sh
python scripts/check_project.py
```

The command writes to `dist/`, checks the archive and wheel, installs the wheel in an isolated offline environment, and excludes local save fixtures and caches. The source ZIP includes `FIRST-TEST.md` for new testers. It also reports the next external release gate without printing any configured remote URL. `scripts/package.py` is available for CI after its test matrix has passed. GitHub Actions runs that matrix on Windows and Linux, then builds a downloadable bundle for successful pushes or manual workflow runs. It cancels stale runs on the same branch and caps job duration to avoid wasting runner time.

## Protect a player save

Use the path printed by `save locate`, or provide a path you found yourself:

```sh
python releaseguard.py save snapshot "/path/to/save/folder" --output "$HOME/ReleaseGuard-saves" --name gta4-before
python releaseguard.py save verify "$HOME/ReleaseGuard-saves/gta4-before"
```

For Windows PowerShell, replace `$HOME` with a quoted folder such as `"D:\GameBackups"`. Snapshot output must be outside the source save folder. Existing snapshots are never overwritten. If a save folder contains symlinks or unreadable files, snapshot creation fails instead of silently omitting them. A snapshot is published only after its copy and manifest are complete.

To roll back, first close the game. Preview the action (this changes nothing):

```sh
python releaseguard.py save restore "$HOME/ReleaseGuard-saves/gta4-before" "/path/to/save/folder"
```

After checking the target path, add `--apply` to perform the restore. ReleaseGuard validates the snapshot first and keeps any existing target as a timestamped sibling backup. Cloud sync may later replace local files, so confirm the game or launcher has finished syncing before checking the result.

## Review a packaged build

```sh
python releaseguard.py analyze "/path/to/packaged/game" --find-duplicates --write-baseline releaseguard-baseline.json --report releaseguard-report.json
python releaseguard.py analyze "/path/to/new/build" --baseline releaseguard-baseline.json --max-growth-mib 100 --report next-build-report.json
```

The first command records an inventory; the second compares a later build and exits with status 1 if size growth exceeds the budget. Duplicate and development-file findings are review hints, not automatic deletion recommendations.

## Try the reliability demo

```sh
python releaseguard.py scenario examples/save-recovery.json --output releaseguard-results
```

The included adapter creates a disposable known-good save, stages a partial replacement, gets interrupted by the harness, and checks the known-good data remains readable. Real game coverage needs an adapter that opens the game's actual save format and checks expected progress in an isolated test slot.

## Share feedback safely

Use the [GitHub issue tracker](https://github.com/Shadoww23/releaseguard/issues) to report a problem. Include your OS, Python version, scenario name, and redacted error text. Do not attach save files, snapshots, unreleased builds, or unredacted reports; reports may contain local file paths.

## License and price

ReleaseGuard 0.1 is free to download and evaluate under the proprietary
freeware terms in [LICENSE](LICENSE): no redistribution, modification, or
resale. Donations are optional. The alpha is provided as-is; see the license
for the warranty and liability terms.


More tools: [Brlinkin](https://shadoww23.github.io/brlinkin/) · [Proton Picker](https://github.com/Shadoww23/proton-picker).
