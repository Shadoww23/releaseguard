# itch.io page draft — ReleaseGuard 0.1 Alpha

## Title

ReleaseGuard: local save protection and game release checks

## Short description

A small, offline-first CLI for snapshotting and restoring PC game saves, reviewing packaged build size, and running game-authored reliability scenarios.

## Page description

ReleaseGuard is an early alpha for PC players and game developers. It has no account, cloud save service, or telemetry. Save discovery and backups run locally on your computer.

### Try in this alpha

- Find common Shadow of Mordor and GTA IV save locations on Windows and Linux/Proton.
- Create a SHA-256-checked snapshot of a save file or folder.
- Verify a snapshot and restore it with a dry run and a preserved backup of the current target.
- Scan packaged builds for size changes, duplicate files, large files, and likely development leftovers.
- Run a sample interrupted-save scenario and inspect its report.

### Requirements

- Python 3.10 or newer.
- Windows or Linux/Proton. The validation record currently covers Linux only; Windows has not yet been natively tested.

### Limits

This alpha does not repair arbitrary corrupted saves, validate a proprietary save by itself, or optimize packaged assets automatically. Real game validation needs a game-specific adapter. The included save/crash scenario is a demonstration, not a test of a commercial game.

## Suggested itch.io setup

- Project type: downloadable software/tool; use the closest available tool/development classification.
- Price: free download with optional tips during feedback gathering; reconsider pricing after testers show value.
- Upload: `ReleaseGuard-0.1.0-alpha.zip`; optionally include the wheel for users comfortable with Python packaging.
- Platforms: mark only platforms actually verified. The current validation is Linux-only; add Windows after a native Windows smoke run.
- Tags: command-line, developer-tools, game-development, utility (use only tags the project page actually offers and that fit).
- Link a feedback channel and ask for OS, command, and output. Tell testers not to send their save files; reports may include local paths.
