# itch.io page draft — ReleaseGuard 0.1 Alpha

## Title

ReleaseGuard: one release-readiness gate for game builds

## Short description

A local CLI prototype combining game-authored save, stability, timing, and packaged-build checks before release.

## Page description

ReleaseGuard is an early developer-tool alpha. Run `release-check` to review a packaged build and execute trusted game-authored scenarios under one pass/fail gate. Scenarios can interrupt a test process, collect logs, validate save recovery, and enforce step-duration budgets. It works locally and in CI without an account, hosted service, telemetry, or runtime dependencies.

### Try in this alpha

- Run a controlled scenario that interrupts a synthetic unsafe save write and confirms the harness detects the unreadable save.
- Run a second scenario that interrupts an atomic replacement and confirms the previous committed save remains readable.
- Inspect captured step logs and a machine-readable JSON report.
- Combine build size/content budgets and multiple scenarios in one release check with a summary JSON report.
- Scan packaged builds for size changes, duplicate files, large files, and likely development leftovers.
- Snapshot and verify selected player save files from supported locations.

### Requirements

- Python 3.10 or newer.
- Windows or Linux. Automated CI passes on Windows and Linux with Python 3.10 and 3.14. The included scenarios use synthetic test data; they have not been integrated with a commercial game or engine.

### Limits

This alpha is not a Unity or Unreal plugin. Teams must provide commands for their test build, representative stability/timing scenarios, and a game-specific save validator. Step duration budgets are not frame-time or GPU profiling. It does not repair arbitrary corrupted saves, diagnose every crash, or automatically optimize packaged assets. The bundled scenarios demonstrate the harness using a small adapter, not a commercial game.

## Suggested itch.io setup

- Project type: downloadable software/tool; use the closest available tool/development classification.
- Price: free during the first developer evaluation. Decide on pricing only after real teams confirm the workflow solves a release problem.
- Upload: `ReleaseGuard-0.1.0-alpha.zip`; optionally include the wheel for users comfortable with Python packaging.
- Platforms: mark Windows and Linux; CI passes on both.
- Tags: command-line, developer-tools, game-development, utility (use only tags the project page actually offers and that fit).
- Ask developers for OS, Python version, engine, CI provider, which scenario passed, and redacted error text. Tell them not to send save files, unreleased builds, or unredacted reports.
