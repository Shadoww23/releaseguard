# ReleaseGuard 0.1 Alpha

ReleaseGuard is a local CLI for game teams and PC players who need safer saves and clearer release checks. It has no account, hosted service, telemetry, or third-party runtime dependencies. Python 3.10 or newer is required.

## What works in this alpha

- **Find and protect saves:** locate common Shadow of Mordor and GTA IV save paths, copy any selected file/folder into a hashed snapshot, verify that snapshot, and restore it with a dry run and preserved pre-restore backup.
- **Review packaged builds:** report build size, large files, duplicate files, likely development leftovers, and size changes against a baseline. It does not modify or optimize the build.
- **Run reliability scenarios:** execute trusted game-authored commands from a JSON manifest, capture logs, and report timeouts or failed checks. The included interrupted-save example is a demonstration adapter, not a test of a commercial game.

The project is an early alpha. Generic save snapshots protect known-good copies; they cannot determine whether an arbitrary game's save is logically valid or repair a corrupt save without game-specific knowledge.

## Quick start

Extract the folder and open a terminal in it. On Windows, use `py -3` if `python` is not available.

```sh
python releaseguard.py --version
python releaseguard.py save locate --game all
python releaseguard.py scenario examples/save-recovery.json --output releaseguard-results
```

On Linux, use `python3` if that is the installed Python command. The project is designed to run on Windows and Linux, but this alpha has only been run locally on Linux so far; the Windows CI workflow must pass before we claim Windows validation. Core commands work offline. A scenario runs the exact local commands declared in its manifest, so only run scenarios you trust.

## Where files are stored

ReleaseGuard does not keep a central database or copy saves automatically. It reads source saves in place. A snapshot is written only to the folder you pass with `--output`; reports and scenario logs go to the paths you pass on the command line. If you choose a removable drive as the output, the backup stays there. The extracted program folder can live anywhere and contains no user profile data by default.

This development copy is in `/home/kasean/Downloads/releaseguard`. The portable alpha ZIP and Python wheel are in `/home/kasean/Downloads`; the sample fixtures in `test-fixtures/` are disposable copies and are excluded from distribution. Do not include personal save files when sharing feedback.

For resilience, keep the project source in a private GitHub repository with CI, but keep player saves out of source control. A robust save-backup setup should let the player choose two destinations (for example, an external drive plus a cloud-synced folder) and encrypt backups before they leave the PC. This alpha does not yet encrypt snapshots or upload them; do not place its unencrypted save snapshots in a shared or third-party cloud folder.

Run the repeatable smoke suite from the extracted project folder with `python -m unittest discover -s tests -v`.

## Protect a real save

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

Tell us your OS, the command you ran, and its output. Do not send personal save files. Review JSON reports before sharing because they can contain local file paths.
