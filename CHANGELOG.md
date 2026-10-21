# Changelog

## 0.1.0-alpha — 2026-10-21

Initial public alpha.

- `release-check` combines packaged-build review and trusted scenarios in one
  pass/fail gate with a combined JSON report.
- Scenario steps support duration budgets, log collection, interrupted-process
  testing, and save recovery checks.
- `analyze` inventories packaged builds and enforces size and growth limits.
- `save` can locate a small set of common saves and create, verify, and restore
  local snapshots.
- Synthetic save-corruption and atomic-replacement demonstrations are included.
- Automated tests pass on Windows and Linux with Python 3.10 and 3.14.
