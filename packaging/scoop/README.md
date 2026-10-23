# Scoop manifest

`releaseguard.json` is ready for a Scoop bucket. It extracts the official
portable ZIP, exposes `releaseguard`, and creates a Start Menu shortcut.

## Published bucket

Live at <https://github.com/Shadoww23/scoop-brlinkin>. Install with:

```powershell
scoop bucket add brlinkin https://github.com/Shadoww23/scoop-brlinkin
scoop install brlinkin/releaseguard
```

Update the manifest in both this repository and the bucket for each release.

## Validate locally

```powershell
scoop install scoop-search
scoop lint bucket/releaseguard.json
```

Or install from a local bucket:

```powershell
scoop bucket add local-brlinkin (Resolve-Path .)
scoop install local-brlinkin/releaseguard
```

For each release, update `version`, `url`, `hash`, and `extract_dir`.
