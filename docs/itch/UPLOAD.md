# Publishing checklist — ReleaseGuard

## Files

- `dist/ReleaseGuard-0.1.0-alpha.zip` — itch.io upload and portable source.
- `dist/releaseguard_local-0.1.0-py3-none-any.whl` — optional wheel.
- `dist/ReleaseGuard-0.1.0-alpha-SHA256SUMS.txt` — publish beside downloads.
- `docs/itch/cover.png`, `icon.png`, `release-check.png` — storefront assets.

## GitHub

Repository: `Shadoww23/releaseguard`. Release `v0.1.0-alpha` is published with
the ZIP, wheel, and checksums. Pushing a new `v*` tag runs
`.github/workflows/release.yml` and creates the release automatically.

## itch.io

1. Create a downloadable project named **ReleaseGuard**.
2. Classify it as a development tool; platforms Windows and Linux.
3. Price free during evaluation, with donations enabled.
4. Upload `ReleaseGuard-0.1.0-alpha.zip`; mark Windows and Linux. Optionally add
   the wheel as a second file.
5. Paste the page copy from `ITCH-PAGE-DRAFT.md`.
6. Upload `cover.png` (630×500), `icon.png` (512×512), and
   `release-check.png` (1280×720).
7. Add the proprietary-freeware/license note and the synthetic-data limits.
8. Test the download and first-test instructions, then publish.

Butler alternative:

```sh
butler push dist/ReleaseGuard-0.1.0-alpha.zip <user>/releaseguard:windows --userversion 0.1.0-alpha
butler push dist/ReleaseGuard-0.1.0-alpha.zip <user>/releaseguard:linux --userversion 0.1.0-alpha
```

## Before each release

- Run `python3 scripts/check_project.py`.
- Run `python3 scripts/package.py`.
- Confirm the ZIP contains `LICENSE`, `CHANGELOG.md`, and no marketing drafts.
- Verify `sha256sum -c ReleaseGuard-0.1.0-alpha-SHA256SUMS.txt`.
- Confirm `releaseguard.py` and `pyproject.toml` versions match the tag.
- Review the latest Windows and Linux CI runs.
