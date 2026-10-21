# ReleaseGuard 0.1 Alpha — Game Save Reliability Checks

ReleaseGuard is a local-first CLI prototype for game teams testing save reliability and reviewing release builds. It can run a game-authored scenario, interrupt a test process, check whether a save remains valid, and return a CI-friendly pass or failure. It has no account, hosted service, telemetry, or runtime dependencies. Python 3.10 or newer is required.

## What works in this alpha

- **Test save reliability:** execute trusted game-authored commands from a JSON manifest, interrupt a test process, capture logs, and report failed recovery checks. The bundled examples demonstrate detection of a synthetic corrupt save and survival of an interrupted atomic write; they are not tests of a commercial game.
- **Review packaged builds:** report build size, large files, duplicate files, likely development leftovers, and size changes against a baseline. It does not modify or optimize the build.
- **Protect selected player saves:** locate common Shadow of Mordor and GTA IV save paths, including Windows Steam installs and redirected Documents folders; copy a selected file or folder into a hashed snapshot, verify it, and restore it with a dry run and preserved pre-restore backup.

This is an early alpha, not a drop-in engine plugin. Game teams must provide commands that launch their test build and validate game-specific save contents. ReleaseGuard cannot determine whether an arbitrary proprietary save is logically valid without that game-specific validator, and it does not repair save formats.

## Quick start

Extract the folder and open a terminal in it. Run both included reliability scenarios:

**Windows PowerShell**

```powershell
py -3 releaseguard.py --version
py -3 releaseguard.py scenario examples/save-corruption-detection.json --output "$HOME\ReleaseGuard-results"
py -3 releaseguard.py scenario examples/save-recovery.json --output "$HOME\ReleaseGuard-results"
```

**Linux**

```sh
python3 releaseguard.py --version
python3 releaseguard.py scenario examples/save-corruption-detection.json --output "$HOME/ReleaseGuard-results"
python3 releaseguard.py scenario examples/save-recovery.json --output "$HOME/ReleaseGuard-results"
```

For a guided first run and feedback checklist, follow [FIRST-TEST.md](FIRST-TEST.md). See [RELEASE-NOTES.md](RELEASE-NOTES.md) for scope and alpha limits. Both examples use disposable synthetic files. The first intentionally detects an unreadable save after an unsafe interrupted write; the second confirms an atomic-write pattern keeps the previous committed save readable.

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
