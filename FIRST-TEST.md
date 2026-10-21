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

## Run the two save reliability scenarios

First, run a controlled unsafe-write example. The scenario intentionally
interrupts a synthetic save while it is overwriting the only committed file.
Its final check is expected to detect that the save is unreadable, so the whole
scenario should report `PASS` when ReleaseGuard catches the fault.

**Windows PowerShell**

```powershell
py -3 releaseguard.py scenario examples/save-corruption-detection.json --output "$HOME\ReleaseGuard-results"
```

**Linux**

```sh
python3 releaseguard.py scenario examples/save-corruption-detection.json --output "$HOME/ReleaseGuard-results"
```

Then run the atomic-write example. It interrupts a synthetic replacement that
is being written to a temporary file and checks that the previous committed
save remains readable.

**Windows PowerShell**

```powershell
py -3 releaseguard.py scenario examples/save-recovery.json --output "$HOME\ReleaseGuard-results"
```

**Linux**

```sh
python3 releaseguard.py scenario examples/save-recovery.json --output "$HOME/ReleaseGuard-results"
```

Each invocation should end with `PASS: all scenario steps passed`. ReleaseGuard
prints the report directory. The reports show the command results and timing.

## Report back

Please share only:

- Operating system and Python version
- Whether both scenarios passed
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
