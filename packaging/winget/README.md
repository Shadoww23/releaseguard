# Winget manifest

`Brlinkin.ReleaseGuard` installs the portable Windows app from the official
release ZIP. Winget extracts it to its package directory and exposes a
`releaseguard` command; it does not bundle or mirror the app.

The directory layout follows the winget-pkgs repository:

```text
manifests/b/Brlinkin/ReleaseGuard/0.1.0-alpha/
  Brlinkin.ReleaseGuard.yaml
  Brlinkin.ReleaseGuard.installer.yaml
  Brlinkin.ReleaseGuard.locale.en-US.yaml
```

## Validate on Windows

```powershell
winget validate --manifest .\packaging\winget\Brlinkin\ReleaseGuard\0.1.0-alpha
winget install --manifest .\packaging\winget\Brlinkin\ReleaseGuard\0.1.0-alpha
```

## Submit

1. Fork `microsoft/winget-pkgs`.
2. Copy `Brlinkin/ReleaseGuard/0.1.0-alpha` to `manifests/b/Brlinkin/ReleaseGuard/`.
3. Open a pull request using the repository template.

Do not submit a new version until its ZIP is published and the hash in
`installer.yaml` is updated. The alpha version string is intentional; the app
reports `0.1.0` internally.

## Updates

For each release:

1. Build the win64 ZIP with `packaging/windows/build.ps1`.
2. Update `PackageVersion`, the ZIP file name, `ReleaseDate`, and
   `InstallerSha256`.
3. Rename the three files and the version directory to match.
4. Submit the new version directory; keep the old one unchanged.
