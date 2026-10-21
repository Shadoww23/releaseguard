# ReleaseGuard 0.1 Alpha

ReleaseGuard is an early developer-tool prototype for testing save reliability
and reviewing packaged game builds. It runs locally and in CI without a hosted
service or runtime dependencies.

## Included demonstrations

- `examples/save-corruption-detection.json` deliberately interrupts an unsafe
  synthetic save write and passes only when the harness detects the unreadable
  save.
- `examples/save-recovery.json` interrupts an atomic replacement and checks
  that the previous committed synthetic save remains readable.
- `releaseguard analyze` inventories packaged builds and can enforce size and
  growth limits.
- `releaseguard save` can locate a small set of common game saves and create,
  verify, or restore local snapshots. This is an experimental player utility.

## Requirements

- Windows or Linux
- Python 3.10 or newer

The automated test matrix passes on Windows and Linux with Python 3.10 and
3.14. See `FIRST-TEST.md` for a short synthetic-data test.

## Limits

This alpha is not a Unity/Unreal plugin and has not been integrated with a
commercial game. A game team must provide commands for its test build and a
game-specific save validator. ReleaseGuard cannot infer whether an arbitrary
proprietary save is logically valid or repair it. Inspect scenario manifests
before running them; they execute the commands listed in the manifest.

When reporting a problem, share redacted logs only. Do not attach save files,
snapshots, unreleased builds, credentials, or reports containing private paths.
