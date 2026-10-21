# ReleaseGuard 0.1 Alpha

ReleaseGuard is an early developer-tool prototype for combining game-authored
save, stability, timing, and packaged-build checks into one local/CI
release-readiness gate. It runs without a hosted service or runtime
dependencies.

## Included demonstrations

- `examples/save-corruption-detection.json` deliberately interrupts an unsafe
  synthetic save write and passes only when the harness detects the unreadable
  save.
- `examples/save-recovery.json` interrupts an atomic replacement and checks
  that the previous committed synthetic save remains readable.
- `releaseguard analyze` inventories packaged builds and can enforce size and
  growth limits.
- `releaseguard release-check` runs build review and one or more trusted test
  scenarios together, then emits a combined pass/fail JSON report. Scenario
  steps can enforce duration budgets; this is not a frame-time or GPU profiler.
- `releaseguard save` can locate a small set of common game saves and create,
  verify, or restore local snapshots. This is an experimental player utility.

## Requirements

- Windows or Linux
- Python 3.10 or newer

The automated test matrix passes on Windows and Linux with Python 3.10 and
3.14. See `FIRST-TEST.md` for a short synthetic-data test.

## Limits

This alpha is not a Unity/Unreal plugin and has not been integrated with a
commercial game. A game team must provide commands for its test build,
representative stability/performance scenarios, and a game-specific save
validator. ReleaseGuard cannot infer whether an arbitrary proprietary save is
logically valid, diagnose all crashes, profile GPU/frame performance, or
automatically optimize the game. Inspect scenario manifests before running
them; they execute the commands listed in the manifest.

When reporting a problem, share redacted logs only. Do not attach save files,
snapshots, unreleased builds, credentials, or reports containing private paths.
