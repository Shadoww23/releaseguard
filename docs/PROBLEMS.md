# ReleaseGuard: common game release problems

ReleaseGuard is a local/CI release-readiness gate for game builds. These are
the problems it is built to expose before players do.

## How do I test whether an interrupted save write corrupts a save?

Run the bundled synthetic demonstration:

```sh
python3 releaseguard.py scenario examples/save-corruption-detection.json --output results
```

The scenario starts a disposable save write, interrupts it at a requested
point, and passes only if the harness detects an unreadable save. The adapter is
synthetic; a real game needs an adapter for its own save format.

## How do I prove an atomic save keeps the previous committed progress?

```sh
python3 releaseguard.py scenario examples/save-recovery.json --output results
```

This interrupts an atomic replacement and verifies that the previous committed
save is still readable. It tests the harness and a reference adapter, not an
arbitrary commercial game.

## How do I add save-integrity checks to CI?

Use `release-check` with your own trusted scenario manifest:

```sh
python3 releaseguard.py release-check ./build \
  --scenario my-save-test.json \
  --max-size-mib 2048 \
  --output release-results
```

The command exits nonzero when a check fails, so a CI job can block the release.
See `TESTING.md` for the report layout and `FIRST-TEST.md` for a synthetic first
run.

## How do I catch oversized game builds and development leftovers?

```sh
python3 releaseguard.py analyze ./build \
  --find-duplicates \
  --baseline releaseguard-baseline.json \
  --max-growth-mib 100 \
  --report build-report.json
```

It inventories packaged builds and flags size growth, duplicate files, large
files, and likely development leftovers. Findings are review hints, not
automatic deletion advice.

## How do I check a save snapshot before restoring it?

`releaseguard save verify` checks a snapshot. `releaseguard save restore`
validates first and keeps the existing target as a timestamped backup. Add
`--apply` only after checking the reported target path. Cloud sync can replace
local files later, so confirm the launcher has finished syncing.

## Does ReleaseGuard work with Unity, Unreal, or Godot?

Not as a plugin. It is engine-agnostic: your manifest supplies commands for the
test build, stability scenarios, and a game-specific save validator. It does not
infer whether a proprietary save is logically valid, profile frame times, or
optimize assets.

## Windows and Linux support

The test matrix runs on Windows and Linux with Python 3.10 and 3.14. The
included scenarios use synthetic files and can run without a game engine.

## What ReleaseGuard is not

- Not a crash reporter or telemetry service.
- Not a GPU or frame-time profiler.
- Not a replacement for playtesting.
- Not a tool for repairing arbitrary corrupted saves.

Search terms this workflow is meant to answer: game save corruption test,
interrupted save write, release checklist automation, CI gate for game builds,
packaged build size budget, duplicate asset detection.
