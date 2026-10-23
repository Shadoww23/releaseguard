# ReleaseGuard for Windows

The Windows build is a self-contained `ReleaseGuard.exe` built with PyInstaller. It
needs no Python installation. The ZIP also contains the README, examples, docs, and
license.

## For testers

1. Download `ReleaseGuard-<version>-win64.zip` and extract it.
2. Double-click `ReleaseGuard.exe` to run a guided check, or open PowerShell in the
   extracted folder for the full CLI:

   ```powershell
   .\ReleaseGuard.exe --help
   .\ReleaseGuard.exe release-check "D:\Builds\MyGame" --output "$HOME\ReleaseGuard-results"
   ```

The executable is unsigned, so Windows SmartScreen may show a warning. Choose
**More info** → **Run anyway** only if the ZIP hash matches `SHA256SUMS.txt` from the
same GitHub release.

The guided mode writes reports to `%USERPROFILE%\ReleaseGuard-results`. It runs the
same `release-check` command as the CLI; no extra work is done for you.

## Build

Build on Windows with Python 3.12+:

```powershell
.\packaging\windows\build.ps1
```

Output: `packaging/windows/dist/ReleaseGuard-<version>-win64.zip` and
`ReleaseGuard-<version>-win64-SHA256SUMS.txt`. The `windows-exe` workflow builds and smoke-tests the same artifact.

## Signing

The build signs the executable when `WINDOWS_SIGN_PFX_BASE64` (a base64
PKCS#12 file) and `WINDOWS_SIGN_PFX_PASSWORD` are present, then verifies it
with `signtool`. Add both as repository secrets to sign release builds. Without
them the alpha stays unsigned and SmartScreen may warn.

After a new build, update the SHA-256 in the Flow manifest, the Scoop manifest,
and the Winget installer manifest. Signing changes the executable hash.
