# Publishing checklist — ReleaseGuard

## Files

- `dist/ReleaseGuard-0.1.0-alpha.zip` — itch.io upload and portable source.
- `dist/ReleaseGuard-0.1.0-alpha-win64.zip` — self-contained Windows app (no Python).
- `dist/releaseguard_local-0.1.0-py3-none-any.whl` — optional wheel.
- `dist/ReleaseGuard-0.1.0-alpha-SHA256SUMS.txt` — publish beside downloads.
- `dist/ReleaseGuard-0.1.0-alpha-win64-SHA256SUMS.txt` — Windows app checksums.
- `docs/itch/cover.png`, `icon.png`, `release-check.png` — storefront assets.

## GitHub

Repository: `Shadoww23/releaseguard`. Release `v0.1.0-alpha` is published with
the ZIP, wheel, and checksums. Pushing a new `v*` tag runs
`.github/workflows/release.yml` and creates the release automatically.

## itch.io

Live: <https://brlinkin.itch.io/releaseguard> (Windows + Linux, free with donations).

Build channels pushed:

```sh
# Windows: push the extracted win64 package so ReleaseGuard.exe is at the root.
butler push path/to/ReleaseGuard-0.1.0-alpha-win64 Brlinkin/releaseguard:windows --userversion 0.1.0-alpha

# Linux: the source archive stays the Linux channel.
butler push dist/ReleaseGuard-0.1.0-alpha.zip Brlinkin/releaseguard:linux --userversion 0.1.0-alpha
```

Published with classification Tool, page copy, the Brlinkin suite link,
cover/icon/screenshot, the proprietary-freeware note, and the synthetic-data
limits.

## Before each release

- Run `python3 scripts/check_project.py`.
- Run `python3 scripts/package.py`.
- Confirm the ZIP contains `LICENSE`, `CHANGELOG.md`, and no marketing drafts.
- Verify `sha256sum -c ReleaseGuard-0.1.0-alpha-SHA256SUMS.txt`.
- Confirm `releaseguard.py` and `pyproject.toml` versions match the tag.
- Review the latest Windows and Linux CI runs.
