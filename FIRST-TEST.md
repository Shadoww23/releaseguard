# ReleaseGuard first test

Thanks for trying this early alpha. This short first run checks save discovery and creates/verifies a backup; it does not modify your game save.

## 1. Open the extracted folder in a terminal

You need Python 3.10 or newer. Check the version:

**Windows PowerShell**

```powershell
py -3 --version
```

**Linux**

```sh
python3 --version
```

## 2. Check that ReleaseGuard starts

Run this command from the extracted ReleaseGuard folder:

**Windows PowerShell**

```powershell
py -3 releaseguard.py --version
```

**Linux**

```sh
python3 releaseguard.py --version
```

It should print `releaseguard 0.1.0`.

## 3. Find a supported game save

This alpha recognizes common save locations for Shadow of Mordor and GTA IV. Close the game first, then run:

**Windows PowerShell**

```powershell
py -3 releaseguard.py save locate --game all
```

**Linux**

```sh
python3 releaseguard.py save locate --game all
```

If your save is found, copy one reported path. If it is not found, report the game and launcher; do not move or rename the save to make discovery work.

## 4. Snapshot and verify the save

Use the reported file or folder path as `SAVE_PATH`. Keep the backup outside the game save folder.

**Windows PowerShell**

```powershell
py -3 releaseguard.py save snapshot "SAVE_PATH" --output "$HOME\ReleaseGuard-saves" --name first-test
py -3 releaseguard.py save verify "$HOME\ReleaseGuard-saves\first-test"
```

**Linux**

```sh
python3 releaseguard.py save snapshot "SAVE_PATH" --output "$HOME/ReleaseGuard-saves" --name first-test
python3 releaseguard.py save verify "$HOME/ReleaseGuard-saves/first-test"
```

Replace `SAVE_PATH`, including the quotes, with the path printed by `save locate`. A successful verify should report that the snapshot passes. If you get an error, keep the original save untouched and include the command and error in your report.

## 5. Send feedback without save data

Please report:

- Operating system and Python version.
- Game and launcher.
- Whether discovery found the save.
- Whether snapshot creation and verification passed.
- The command and error text if anything failed.

Remove your Windows/Linux account name and other private folders from copied paths. **Do not send save files, snapshots, or the contents of your backup.** For this first test, do not run `save restore --apply` against a real game profile.
