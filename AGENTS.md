# ReleaseGuard contributor and coding-agent guide

## Product goal

ReleaseGuard is a local-first game reliability utility. Help game teams and PC players protect saves and catch release-build problems with practical, explainable checks. Treat it as an early alpha: do not claim generic corruption repair, production readiness, or platform validation that the evidence does not support.

The project owner has limited time and wants to focus on product direction. Take routine implementation, investigation, documentation, and verification forward independently. Make reversible, low-risk decisions without asking. Ask only when a choice changes product direction, creates external costs, publishes data, or risks user data.

## Safety and privacy

- Never add personal save files, `test-fixtures/`, machine-specific paths, credentials, or tokens to source control or release packages.
- Preserve the local-first design: no account, telemetry, upload, or hosted service unless the owner explicitly changes that direction.
- Treat save restore and destructive filesystem actions as high risk. Keep dry-run defaults and backups; do not run restore against real saves as an automated check.
- Scenarios execute commands from their manifest. Keep examples disposable and clearly mark manifests as trusted code.
- Do not claim a test passed unless it was run and its output supports that claim.

## Working in this repository

- Read `README.md` for product behavior and `TESTING.md` for verified status before changing claims or workflows.
- Keep the program dependency-free at runtime and compatible with Python 3.10+ on Windows and Linux.
- Prefer standard-library implementations, explicit paths, clear errors, and safe failure over silently skipping data.
- Keep packages on the explicit allowlist in `scripts/package.py`; add tests for package inclusion/exclusion when changing it.
- Keep test fixtures synthetic or disposable. Never point restore tests at a user's actual game profile.
- Avoid unrelated refactors and new maintenance services.

## Verification and next work

- After code changes, run `python scripts/check_project.py` (or `py -3 scripts/check_project.py` on Windows). It compiles, runs the suite, and creates validated local packages only after checks pass.
- For documentation-only changes, inspect the diff and check referenced commands/paths; do not rebuild artifacts without need.
- The GitHub Actions matrix is the authoritative native Windows/Python-version check. Report clearly when it has not run.
- Find the next useful task from open issues if available, otherwise the alpha gaps in `TESTING.md`; prioritize fixes that improve real player safety or make a focused external test easier.
- Do not publish a release or upload user data without explicit authorization.
