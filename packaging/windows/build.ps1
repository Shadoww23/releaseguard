param([string]$Label = "alpha")

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $root

$dist = Join-Path $root "packaging\windows\dist"
$work = Join-Path $root "packaging\windows\build"
$version = (Select-String -Path (Join-Path $root "releaseguard.py") -Pattern '^VERSION = "([^"]+)"' -List).Matches[0].Groups[1].Value
$packageVersion = if ($Label) { "$version-$Label" } else { $version }
$stageName = "ReleaseGuard-$packageVersion-win64"
$stage = Join-Path $dist $stageName
$zip = Join-Path $dist "$stageName.zip"
$sums = Join-Path $dist "SHA256SUMS.txt"

New-Item -ItemType Directory -Force -Path $dist | Out-Null
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $stage, $zip, $sums

python -m pip install --disable-pip-version-check --no-cache-dir "pyinstaller==6.11.1"
python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --name ReleaseGuard `
    --icon (Join-Path $root "packaging\windows\releaseguard.ico") `
    --distpath $dist `
    --workpath $work `
    --specpath (Join-Path $root "packaging\windows") `
    --paths $root `
    --hidden-import releaseguard `
    (Join-Path $root "packaging\windows\entry.py")

$exe = Join-Path $dist "ReleaseGuard.exe"
if (-not (Test-Path $exe)) { throw "PyInstaller did not produce ReleaseGuard.exe" }

& $exe --version
if ($LASTEXITCODE -ne 0) { throw "ReleaseGuard.exe --version failed" }

$smokeBuild = Join-Path $env:RUNNER_TEMP "releaseguard-smoke-build"
New-Item -ItemType Directory -Force -Path $smokeBuild | Out-Null
Set-Content -Path (Join-Path $smokeBuild "content.pak") -Value "smoke" -NoNewline
$smokeReport = Join-Path $env:RUNNER_TEMP "releaseguard-smoke-report.json"
& $exe analyze $smokeBuild --report $smokeReport
if ($LASTEXITCODE -ne 0) { throw "ReleaseGuard.exe analyze failed" }
if (-not (Test-Path $smokeReport)) { throw "The smoke report was not written" }

New-Item -ItemType Directory -Force -Path $stage | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $stage "examples") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $stage "docs") | Out-Null
Copy-Item $exe $stage
Copy-Item (Join-Path $root "README.md") $stage
Copy-Item (Join-Path $root "LICENSE") $stage
Copy-Item (Join-Path $root "FIRST-TEST.md") $stage
Copy-Item (Join-Path $root "RELEASE-NOTES.md") $stage
Copy-Item (Join-Path $root "docs\PROBLEMS.md") (Join-Path $stage "docs")
Copy-Item (Join-Path $root "examples\save_adapter.py") (Join-Path $stage "examples")
Copy-Item (Join-Path $root "examples\save-corruption-detection.json") (Join-Path $stage "examples")
Copy-Item (Join-Path $root "examples\save-recovery.json") (Join-Path $stage "examples")

Push-Location $dist
Compress-Archive -Path $stageName -DestinationPath $zip -Force
Pop-Location

$exeHash = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
"$exeHash  $stageName/ReleaseGuard.exe" | Out-File -Encoding ascii $sums
"$zipHash  $stageName.zip" | Out-File -Encoding ascii -Append $sums
Write-Output $zip
Write-Output $sums
