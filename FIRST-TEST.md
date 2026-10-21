# ReleaseGuard first developer test

This alpha test uses only synthetic files in a temporary workspace. It does not
open a game, alter a real save, or require you to share game data.

## Requirements

- Windows or Linux
- Python 3.10 or newer
- A terminal opened in the extracted ReleaseGuard folder

Check Python:

**Windows PowerShell**

```powershell
py -3 --version
```

**Linux**

```sh
python3 --version
```

## Run the first check

Start with a packaged-build review. This needs no manifest setup. To try the
full bundled demo as a second step, add the two sample scenario options shown
below; those run only against synthetic disposable save files.

**Windows PowerShell**

```powershell
New-Item -ItemType Directory -Force "$HOME\ReleaseGuard-test-build" | Out-Null
Set-Content -NoNewline "$HOME\ReleaseGuard-test-build\game.bin" "synthetic build"
py -3 releaseguard.py release-check "$HOME\ReleaseGuard-test-build" `
  --max-size-mib 1 --output "$HOME\ReleaseGuard-results"
```

**Linux**

```sh
mkdir -p "$HOME/ReleaseGuard-test-build"
printf 'synthetic build' > "$HOME/ReleaseGuard-test-build/game.bin"
python3 releaseguard.py release-check "$HOME/ReleaseGuard-test-build" \
  --max-size-mib 1 --output "$HOME/ReleaseGuard-results"
```

Expect `PASS: all release checks passed`. ReleaseGuard prints the path to one
combined JSON report; detailed build and scenario logs are beside it. The
sample includes a duration measurement for each test step, but it does not
profile frame rate or GPU performance.

To run the included save-reliability demonstrations too, repeat the command
with these additional options:

```text
--scenario examples/save-corruption-detection.json --scenario examples/save-recovery.json
```

## Report back

Please share only:

- Operating system and Python version
- Whether the build check passed; if you also ran the examples, whether both scenarios passed
- Any error text, with usernames and private paths removed
- Game engine and CI system, if you are evaluating it for a development team

Do not send real save files, snapshots, unreleased builds, or unredacted reports.
Scenario manifests run the exact commands they contain; inspect and trust a
manifest before running it.

## Try it with a game test build

The examples establish the harness flow with a small adapter. A game team can
replace the adapter commands with its own disposable test build and save-format
validator. The `scenario` command provides `{build}`, `{workspace}`, and
`{step_dir}` path tokens, kills a process at a configured point, records stdout
and stderr, and returns a failing status when an expectation is violated. Start
with an isolated test slot and a build that cannot access player profiles.
