#!/usr/bin/env python3
"""ReleaseGuard: inspect packaged game builds for size and release-content risks.

This starter is intentionally read-only. It never edits the packaged game.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# These file types are common in development outputs. Their presence is only a
# review hint: some games intentionally ship symbols or text-based assets.
REVIEW_EXTENSIONS = {
    ".pdb": "debug symbols",
    ".ilk": "incremental linker data",
    ".obj": "compiler object file",
    ".o": "compiler object file",
    ".map": "linker map",
    ".log": "log file",
    ".tmp": "temporary file",
    ".cs": "C# source file",
    ".cpp": "C++ source file",
    ".h": "C/C++ header file",
    ".py": "Python source file",
}
VERSION = "0.1.0"


def iter_files(root: Path):
    """Yield regular files below root without following symlinks."""
    # os.walk lets us prune symlinked directories so a build cannot make the
    # scanner escape into unrelated parts of the user's filesystem.
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        dirnames[:] = [
            name for name in dirnames
            if not (current_path / name).is_symlink()
        ]
        for name in filenames:
            path = current_path / name
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                yield path
            except OSError:
                # A file may disappear while a build directory is being
                # replaced. The scan report records stable entries only.
                continue


def inventory_build(root: Path) -> dict[str, Any]:
    """Collect a lightweight, relative-path-to-size inventory."""
    files: dict[str, int] = {}
    for path in iter_files(root):
        try:
            relative = path.relative_to(root).as_posix()
            files[relative] = path.stat().st_size
        except (OSError, ValueError):
            continue

    extension_totals: dict[str, int] = defaultdict(int)
    extension_counts: dict[str, int] = defaultdict(int)
    review_files = []
    for relative, size in files.items():
        suffix = Path(relative).suffix.lower() or "[no extension]"
        extension_totals[suffix] += size
        extension_counts[suffix] += 1
        if suffix in REVIEW_EXTENSIONS:
            review_files.append({
                "path": relative,
                "size_bytes": size,
                "reason": REVIEW_EXTENSIONS[suffix],
            })

    largest = sorted(
        ({"path": path, "size_bytes": size} for path, size in files.items()),
        key=lambda item: (-item["size_bytes"], item["path"].casefold()),
    )[:20]

    return {
        "file_count": len(files),
        "total_size_bytes": sum(files.values()),
        "files": files,
        "largest_files": largest,
        "extension_totals": [
            {"extension": ext, "size_bytes": size, "file_count": extension_counts[ext]}
            for ext, size in sorted(extension_totals.items(), key=lambda pair: (-pair[1], pair[0]))
        ],
        "review_files": sorted(review_files, key=lambda item: (-item["size_bytes"], item["path"].casefold())),
    }


def find_duplicate_files(root: Path, files: dict[str, int]) -> dict[str, Any]:
    """Find exact byte-identical files, hashing only same-size candidates."""
    by_size: dict[int, list[str]] = defaultdict(list)
    for relative, size in files.items():
        # Empty files are technically duplicates too, but aren't meaningful
        # build bloat and tend to add noisy findings.
        if size > 0:
            by_size[size].append(relative)

    groups: dict[str, list[str]] = defaultdict(list)
    unreadable = []
    for size, candidates in by_size.items():
        if len(candidates) < 2:
            continue
        for relative in candidates:
            digest = hashlib.sha256()
            try:
                with (root / relative).open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(block)
                groups[f"{size}:{digest.hexdigest()}"].append(relative)
            except OSError as exc:
                unreadable.append({"path": relative, "error": str(exc)})

    duplicates = []
    for key, paths in groups.items():
        if len(paths) < 2:
            continue
        size_text, digest = key.split(":", 1)
        size = int(size_text)
        duplicates.append({
            "sha256": digest,
            "size_each_bytes": size,
            "paths": sorted(paths, key=str.casefold),
            "potentially_reclaimable_bytes": size * (len(paths) - 1),
        })
    duplicates.sort(key=lambda item: (-item["potentially_reclaimable_bytes"], item["paths"][0].casefold()))
    return {
        "groups": duplicates,
        "duplicate_file_count": sum(len(group["paths"]) for group in duplicates),
        "potentially_reclaimable_bytes": sum(group["potentially_reclaimable_bytes"] for group in duplicates),
        "unreadable_candidates": unreadable,
        "note": "Exact duplicates only; these files may still be required at multiple paths by the game.",
    }


def load_baseline(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read baseline {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise ValueError(f"baseline {path} has no valid 'files' inventory")
    return data


def compare(current: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any] | None:
    if baseline is None:
        return None

    old_files = baseline["files"]
    new_files = current["files"]
    added = sorted(set(new_files) - set(old_files), key=str.casefold)
    removed = sorted(set(old_files) - set(new_files), key=str.casefold)
    changed = []
    for path in set(old_files) & set(new_files):
        before, after = old_files[path], new_files[path]
        if before != after:
            changed.append({
                "path": path,
                "previous_size_bytes": before,
                "current_size_bytes": after,
                "delta_bytes": after - before,
            })
    changed.sort(key=lambda item: (-abs(item["delta_bytes"]), item["path"].casefold()))

    old_total = int(baseline.get("total_size_bytes", sum(old_files.values())))
    new_total = current["total_size_bytes"]
    return {
        "previous_total_size_bytes": old_total,
        "current_total_size_bytes": new_total,
        "delta_bytes": new_total - old_total,
        "delta_percent": round((new_total - old_total) * 100 / old_total, 2) if old_total else None,
        "added_files": [{"path": path, "size_bytes": new_files[path]} for path in added],
        "removed_files": [{"path": path, "size_bytes": old_files[path]} for path in removed],
        "changed_files": changed,
    }


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def hash_file(path: Path) -> str:
    """Return a streaming SHA-256 digest without loading a save into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def windows_steam_registry_paths(registry_module: Any | None = None) -> list[Path]:
    """Read Steam install locations recorded by Windows, without requiring winreg elsewhere."""
    if registry_module is None:
        if os.name != "nt":
            return []
        try:
            import winreg as registry_module
        except ImportError:
            return []

    locations: list[Path] = []
    # Steam's own registry key is the most reliable source when the user
    # installed Steam outside the usual Program Files folders.
    keys = (
        (registry_module.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
        (registry_module.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Valve\Steam"),
        (registry_module.HKEY_LOCAL_MACHINE, r"Software\Valve\Steam"),
    )
    for hive, subkey in keys:
        try:
            with registry_module.OpenKey(hive, subkey) as key:
                for value_name in ("SteamPath", "InstallPath"):
                    try:
                        value, _ = registry_module.QueryValueEx(key, value_name)
                    except OSError:
                        continue
                    if value:
                        locations.append(Path(value))
        except OSError:
            continue
    return locations


def windows_documents_paths(registry_module: Any | None = None) -> list[Path]:
    """Find a redirected Documents folder using Windows' user-shell setting."""
    if registry_module is None:
        if os.name != "nt":
            return []
        try:
            import winreg as registry_module
        except ImportError:
            return []

    try:
        with registry_module.OpenKey(
            registry_module.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            value, _ = registry_module.QueryValueEx(key, "Personal")
    except OSError:
        return []
    if not isinstance(value, str) or not value:
        return []
    return [Path(os.path.expandvars(value))]


def steam_library_roots() -> list[Path]:
    """Find standard Steam roots and libraries listed in libraryfolders.vdf."""
    home = Path.home()
    candidates = [
        home / ".steam/steam",
        home / ".local/share/Steam",
        home / ".steam/root",
        home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    ]
    if os.name == "nt":
        candidates.extend(windows_steam_registry_paths())
        for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
            value = os.environ.get(variable)
            if value:
                candidates.append(Path(value) / "Steam")

    roots: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            key = str(path.expanduser().resolve()).casefold()
            if key not in seen and (path / "steamapps").is_dir():
                seen.add(key)
                roots.append(path.expanduser().resolve())
        except OSError:
            return

    for candidate in candidates:
        add(candidate)
    for root in list(roots):
        vdf = root / "steamapps/libraryfolders.vdf"
        try:
            content = vdf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Steam's VDF uses quoted key/value pairs. Extract "path" entries so
        # numbered libraries are supported without another package dependency.
        for raw_path in re.findall(r'"path"\s+"((?:\\\\.|[^"\\])*)"', content):
            decoded = raw_path.replace("\\\\", "\\")
            add(Path(decoded))
    return roots


def child_dirs(path: Path) -> list[Path]:
    try:
        return sorted((p for p in path.iterdir() if p.is_dir() and not p.is_symlink()), key=lambda p: p.name.casefold())
    except OSError:
        return []


def nonempty_save_dirs(path: Path) -> list[Path]:
    """Return profile directories containing files, without opening file data."""
    matches = []
    for directory in child_dirs(path):
        try:
            if next(iter_files(directory), None) is not None:
                matches.append(directory)
        except OSError:
            continue
    return matches


def locate_game_saves(game: str) -> list[Path]:
    """Locate common save paths for the supported games without modifying them."""
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            canonical = path.resolve()
            key = str(canonical).casefold()
            if canonical.exists() and key not in seen:
                seen.add(key)
                found.append(canonical)
        except OSError:
            return

    roots = steam_library_roots()
    if game in {"shadow-of-mordor", "all"}:
        for root in roots:
            userdata = root / "userdata"
            try:
                for user in child_dirs(userdata):
                    remote = user / "241930/remote"
                    if not remote.is_dir():
                        continue
                    for path in remote.iterdir():
                        if path.is_file() and path.name.casefold() == "gamedata.sav":
                            add(path)
            except OSError:
                continue

    if game in {"gta-iv", "all"}:
        document_roots = [Path.home() / "Documents"]
        document_roots.extend(windows_documents_paths())
        for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            value = os.environ.get(variable)
            if value:
                document_roots.append(Path(value) / "Documents")
        if os.name == "nt":
            for variable in ("USERPROFILE",):
                value = os.environ.get(variable)
                if value:
                    document_roots.append(Path(value) / "Documents")

        prefix_users: list[Path] = []
        for root in roots:
            compatdata = root / "steamapps/compatdata/12210/pfx/drive_c/users"
            prefix_users.extend(child_dirs(compatdata))
        home = Path.home()
        prefix_bases = [
            home / ".wine",
            home / ".local/share/bottles/bottles",
            home / ".var/app/com.usebottles.bottles/data/bottles/bottles",
            home / "Games",
        ]
        for base in prefix_bases:
            if base.name == "bottles":
                prefixes = child_dirs(base)
            elif base == home / "Games":
                prefixes = [p for p in child_dirs(base) if (p / "drive_c/users").is_dir()]
            else:
                prefixes = [base] if (base / "drive_c/users").is_dir() else []
            for prefix in prefixes:
                prefix_users.extend(child_dirs(prefix / "drive_c/users"))

        documents = list(document_roots)
        documents.extend(user / "Documents" for user in prefix_users)
        local_appdata = [user / "AppData/Local" for user in prefix_users]
        local_appdata.append(Path.home() / ".local/share")

        for documents_dir in documents:
            gta_root = documents_dir / "Rockstar Games/GTA IV"
            profiles = gta_root / "Profiles"
            legacy = gta_root / "savegames"
            for profile in nonempty_save_dirs(profiles):
                add(profile)
            for profile in nonempty_save_dirs(legacy):
                add(profile)
            # Some older installs place saves directly in the savegames folder.
            if legacy.is_dir():
                try:
                    if any(p.is_file() for p in legacy.iterdir()):
                        add(legacy)
                except OSError:
                    pass
        for local_dir in local_appdata:
            legacy = local_dir / "Rockstar Games/GTA IV/savegames"
            for profile in nonempty_save_dirs(legacy):
                add(profile)
            if legacy.is_dir():
                try:
                    if any(p.is_file() for p in legacy.iterdir()):
                        add(legacy)
                except OSError:
                    pass

    return sorted(found, key=lambda path: str(path).casefold())


def locate_saves(args: argparse.Namespace) -> int:
    games = ["shadow-of-mordor", "gta-iv"] if args.game == "all" else [args.game]
    found_any = False
    for game in games:
        paths = locate_game_saves(game)
        print(f"{game}:")
        if paths:
            found_any = True
            for path in paths:
                print(f"  {path}")
        else:
            print("  no save found in the locations checked")
    if not found_any:
        print("No supported save found. Use 'save snapshot' with the save's folder path when you locate it.")
        return 1
    print("Save discovery only reads paths and directory entries; it does not open or modify saves.")
    return 0


def snapshot_files(source: Path) -> list[tuple[Path, str]]:
    """List source files and safe relative names; never follow symlinks."""
    if source.is_symlink():
        raise ValueError("source cannot be a symbolic link")
    if source.is_file():
        return [(source, source.name)]
    if not source.is_dir():
        raise ValueError(f"source is not a file or directory: {source}")

    entries = []

    def walk_error(error: OSError) -> None:
        raise error

    # For saves, silently skipping an unreadable file or linked directory
    # could create a snapshot that looks complete but is missing progress.
    for current, dirnames, filenames in os.walk(source, followlinks=False, onerror=walk_error):
        current_path = Path(current)
        linked_dirs = [name for name in dirnames if (current_path / name).is_symlink()]
        if linked_dirs:
            raise ValueError(f"save source contains a symbolic-link directory: {current_path / linked_dirs[0]}")
        dirnames.sort(key=str.casefold)
        for name in filenames:
            path = current_path / name
            try:
                if path.is_symlink():
                    raise ValueError(f"save source contains a symbolic-link file: {path}")
                if not path.is_file():
                    raise ValueError(f"save source contains a non-regular file: {path}")
                # Force a read-open now so a permission or filesystem error
                # cannot be silently deferred until a later backup attempt.
                with path.open("rb"):
                    pass
            except OSError as exc:
                raise OSError(f"cannot read save source file {path}: {exc}") from exc
            entries.append((path, path.relative_to(source).as_posix()))
    return sorted(entries, key=lambda item: item[1].casefold())


def create_save_snapshot(args: argparse.Namespace) -> int:
    """Copy a save file/folder to a new, immutable-by-default snapshot folder."""
    # Keep the final path component intact so a symlink input can be rejected.
    source = args.source.expanduser().absolute()
    try:
        entries = snapshot_files(source)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: cannot read save source: {exc}", file=sys.stderr)
        return 2

    output_root = args.output.expanduser().resolve()
    if source.is_dir() and (output_root == source.resolve() or source.resolve() in output_root.parents):
        print("error: snapshot output must be outside the source save folder", file=sys.stderr)
        return 2

    name = args.name or datetime.now(timezone.utc).strftime("snapshot-%Y%m%dT%H%M%S_%fZ")
    reserved_windows_names = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    }
    invalid_name = (
        not name
        or len(name) > 120
        or name in {".", ".."}
        or any(char in '<>:"/\\|?*' or ord(char) < 32 for char in name)
        or name.endswith((" ", "."))
        or name.split(".", 1)[0].upper() in reserved_windows_names
    )
    if invalid_name:
        print("error: snapshot name must be a single folder name", file=sys.stderr)
        return 2
    snapshot_dir = output_root / name
    if snapshot_dir.exists():
        print(f"error: snapshot already exists; refusing to overwrite: {snapshot_dir}", file=sys.stderr)
        return 2

    staging_dir: Path | None = None
    manifest_files: dict[str, dict[str, Any]] = {}
    try:
        output_root.mkdir(parents=True, exist_ok=True)
        if snapshot_dir.exists():
            print(f"error: snapshot already exists; refusing to overwrite: {snapshot_dir}", file=sys.stderr)
            return 2
        staging_dir = Path(tempfile.mkdtemp(prefix=f".{name}.releaseguard-staging-", dir=output_root))
        data_dir = staging_dir / "data"
        data_dir.mkdir(parents=True)
        for source_file, relative in entries:
            destination = data_dir / Path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            before = source_file.stat()
            shutil.copyfile(source_file, destination)
            after = source_file.stat()
            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                raise OSError(f"source changed while being copied: {relative}")
            shutil.copystat(source_file, destination, follow_symlinks=False)
            manifest_files[relative] = {
                "size_bytes": destination.stat().st_size,
                "sha256": hash_file(destination),
            }
        manifest = {
            "snapshot_version": 1,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "source_kind": "file" if source.is_file() else "directory",
            "file_count": len(manifest_files),
            "total_size_bytes": sum(item["size_bytes"] for item in manifest_files.values()),
            "files": manifest_files,
        }
        write_json(staging_dir / "manifest.json", manifest)
        # Publish the completed snapshot with one same-filesystem rename. A
        # crash during copying leaves only a hidden staging directory, never a
        # final-looking snapshot without its manifest.
        if snapshot_dir.exists():
            raise FileExistsError(f"snapshot already exists; refusing to overwrite: {snapshot_dir}")
        staging_dir.rename(snapshot_dir)
        staging_dir = None
    except (OSError, ValueError) as exc:
        if staging_dir is not None:
            try:
                shutil.rmtree(staging_dir)
            except OSError:
                pass
        print(f"error: snapshot could not be completed: {exc}", file=sys.stderr)
        return 2

    print(f"Snapshot: {snapshot_dir}")
    print(f"Files: {len(manifest_files):,}    Total: {human_size(manifest['total_size_bytes'])}")
    print(f"Manifest: {snapshot_dir / 'manifest.json'}")
    return 0


def verify_save_snapshot(args: argparse.Namespace) -> int:
    """Check every saved snapshot file against its recorded size and digest."""
    snapshot_dir = args.snapshot.expanduser().resolve()
    manifest_path = snapshot_dir / "manifest.json"
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read snapshot manifest: {exc}", file=sys.stderr)
        return 2
    if not isinstance(manifest, dict) or manifest.get("snapshot_version") != 1:
        print("error: unsupported or invalid snapshot manifest", file=sys.stderr)
        return 2
    files = manifest.get("files")
    if not isinstance(files, dict):
        print("error: snapshot manifest has no valid files map", file=sys.stderr)
        return 2
    if manifest.get("source_kind") not in {"file", "directory"}:
        print("error: snapshot manifest has no supported source_kind", file=sys.stderr)
        return 2
    if manifest.get("source_kind") == "file" and len(files) != 1:
        print("error: file snapshot must contain exactly one file", file=sys.stderr)
        return 2
    if (isinstance(manifest.get("file_count"), bool)
            or manifest.get("file_count") != len(files)):
        print("error: snapshot manifest file_count does not match its files map", file=sys.stderr)
        return 2
    declared_total = manifest.get("total_size_bytes")
    if isinstance(declared_total, bool) or not isinstance(declared_total, int) or declared_total < 0:
        print("error: snapshot manifest has an invalid total_size_bytes", file=sys.stderr)
        return 2

    data_dir = snapshot_dir / "data"
    if data_dir.is_symlink() or not data_dir.is_dir():
        print("FAIL: snapshot data directory is missing or unsafe", file=sys.stderr)
        return 1
    failures = []
    expected_paths: set[str] = set()
    calculated_total = 0
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, dict):
            failures.append(f"invalid manifest entry: {relative!r}")
            continue
        relative_path = Path(relative)
        if (relative_path.is_absolute() or ".." in relative_path.parts
                or not relative_path.parts or "\\" in relative):
            failures.append(f"unsafe path in manifest: {relative!r}")
            continue
        normalized = relative_path.as_posix()
        if normalized in expected_paths:
            failures.append(f"duplicate path in manifest: {normalized}")
            continue
        expected_paths.add(normalized)
        target = data_dir / relative_path
        try:
            if (target.is_symlink()
                    or not target.resolve().is_relative_to(data_dir.resolve())
                    or not target.is_file()):
                failures.append(f"missing or unsafe file: {normalized}")
                continue
            size = target.stat().st_size
            expected_size = expected.get("size_bytes")
            expected_hash = expected.get("sha256")
            if (isinstance(expected_size, bool) or not isinstance(expected_size, int)
                    or expected_size < 0 or not isinstance(expected_hash, str)
                    or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None):
                failures.append(f"invalid metadata: {normalized}")
                continue
            calculated_total += expected_size
            if size != expected_size:
                failures.append(f"size mismatch: {normalized}")
                continue
            if hash_file(target) != expected_hash:
                failures.append(f"checksum mismatch: {normalized}")
        except OSError as exc:
            failures.append(f"cannot read {normalized}: {exc}")

    actual_paths = {
        path.relative_to(data_dir).as_posix()
        for path in iter_files(data_dir)
    } if data_dir.is_dir() else set()
    if calculated_total != declared_total:
        failures.append("total_size_bytes does not match the files map")
    for extra in sorted(actual_paths - expected_paths, key=str.casefold):
        failures.append(f"unexpected file: {extra}")

    if failures:
        print(f"FAIL: snapshot integrity check found {len(failures)} problem(s)")
        for failure in failures[:20]:
            print(f"  {failure}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")
        return 1
    print(f"PASS: {len(files):,} snapshot file(s) match their recorded SHA-256 hashes")
    print(f"Snapshot: {snapshot_dir}")
    return 0


def restore_save_snapshot(args: argparse.Namespace) -> int:
    """Restore a verified snapshot, preserving any current target as a backup."""
    snapshot_dir = args.snapshot.expanduser().resolve()
    target = args.target.expanduser().absolute()
    if verify_save_snapshot(argparse.Namespace(snapshot=snapshot_dir)) != 0:
        print("error: refusing to restore an invalid snapshot", file=sys.stderr)
        return 2
    try:
        manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read snapshot manifest: {exc}", file=sys.stderr)
        return 2

    data_dir = snapshot_dir / "data"
    kind = manifest.get("source_kind")
    if kind not in {"file", "directory"}:
        print("error: snapshot has no supported source_kind", file=sys.stderr)
        return 2
    files = manifest["files"]
    if kind == "file" and len(files) != 1:
        print("error: file snapshot must contain exactly one file", file=sys.stderr)
        return 2
    if target.is_symlink():
        print("error: refusing to replace a symbolic link", file=sys.stderr)
        return 2
    parent = target.parent
    if not parent.is_dir():
        print(f"error: target parent directory does not exist: {parent}", file=sys.stderr)
        return 2
    try:
        target_resolved = target.resolve()
        if (target_resolved == snapshot_dir or snapshot_dir in target_resolved.parents
                or target_resolved in snapshot_dir.parents):
            print("error: restore target cannot overlap the snapshot folder", file=sys.stderr)
            return 2
    except OSError as exc:
        print(f"error: cannot resolve restore target: {exc}", file=sys.stderr)
        return 2

    if target.exists() and ((kind == "file" and not target.is_file())
                            or (kind == "directory" and not target.is_dir())):
        print("error: restore target exists but has the wrong file/directory type", file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    backup = parent / f"{target.name}.releaseguard-backup-{stamp}"
    staging = parent / f".{target.name}.releaseguard-staging-{stamp}"
    if backup.exists() or staging.exists():
        print("error: restore staging or backup path already exists", file=sys.stderr)
        return 2

    print(f"Snapshot: {snapshot_dir}")
    print(f"Restore target: {target}")
    print(f"Current target backup: {backup if target.exists() else '(none; target does not exist)'}")
    if not args.apply:
        print("DRY RUN: no files changed. Re-run with --apply to restore this snapshot.")
        return 0

    try:
        if kind == "file":
            relative = next(iter(files))
            source_file = data_dir / relative
            staged_file = parent / f".{target.name}.releaseguard-staging-{stamp}"
            shutil.copy2(source_file, staged_file)
            if target.exists():
                shutil.copy2(target, backup)
            os.replace(staged_file, target)
        else:
            staging.mkdir()
            for relative in files:
                source_file = data_dir / relative
                destination = staging / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, destination)
            if target.exists():
                os.replace(target, backup)
            try:
                os.replace(staging, target)
            except OSError:
                if backup.exists() and not target.exists():
                    os.replace(backup, target)
                raise
    except OSError as exc:
        try:
            if staging.is_dir():
                shutil.rmtree(staging)
            elif staging.exists():
                staging.unlink()
        except OSError:
            pass
        print(f"error: restore failed: {exc}", file=sys.stderr)
        return 2

    print("PASS: snapshot restored")
    if backup.exists():
        print(f"Previous target preserved at: {backup}")
    return 0


def analyze(args: argparse.Namespace) -> int:
    root = args.build.resolve()
    if not root.is_dir():
        print(f"error: build directory does not exist: {root}", file=sys.stderr)
        return 2

    try:
        baseline = load_baseline(args.baseline)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    inventory = inventory_build(root)
    duplicate_report = find_duplicate_files(root, inventory["files"]) if args.find_duplicates else None
    budget_bytes = args.max_size_mib * 1024 * 1024 if args.max_size_mib is not None else None
    growth_budget_bytes = args.max_growth_mib * 1024 * 1024 if args.max_growth_mib is not None else None
    comparison = compare(inventory, baseline)
    growth_exceeded = (
        growth_budget_bytes is not None
        and comparison is not None
        and comparison["delta_bytes"] > growth_budget_bytes
    )
    report: dict[str, Any] = {
        "tool": "ReleaseGuard",
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "build_root": str(root),
        "summary": {
            "file_count": inventory["file_count"],
            "total_size_bytes": inventory["total_size_bytes"],
            "total_size_human": human_size(inventory["total_size_bytes"]),
            "max_size_bytes": budget_bytes,
            "budget_exceeded": budget_bytes is not None and inventory["total_size_bytes"] > budget_bytes,
            "max_growth_bytes": growth_budget_bytes,
            "growth_budget_exceeded": growth_exceeded,
        },
        "largest_files": inventory["largest_files"],
        "extension_totals": inventory["extension_totals"],
        "review_files": inventory["review_files"],
        "comparison": comparison,
        "exact_duplicates": duplicate_report,
    }

    if args.write_baseline:
        baseline_data = {
            "baseline_version": 1,
            "created_utc": report["created_utc"],
            "files": inventory["files"],
            "total_size_bytes": inventory["total_size_bytes"],
        }
        write_json(args.write_baseline, baseline_data)
        report["baseline_written"] = str(args.write_baseline.resolve())

    if args.report:
        write_json(args.report, report)

    print(f"Build: {root}")
    print(f"Files: {inventory['file_count']:,}    Total: {human_size(inventory['total_size_bytes'])}")
    if report["comparison"] is not None:
        delta = report["comparison"]["delta_bytes"]
        sign = "+" if delta > 0 else ""
        print(f"Vs baseline: {sign}{human_size(delta)} ({report['comparison']['delta_percent']}%)")
        biggest_changes = report["comparison"]["changed_files"][:5]
        biggest_additions = sorted(
            report["comparison"]["added_files"],
            key=lambda item: (-item["size_bytes"], item["path"].casefold()),
        )[:5]
        for item in biggest_changes:
            d = item["delta_bytes"]
            print(f"  changed {item['path']}: {'+' if d > 0 else ''}{human_size(d)}")
        for item in biggest_additions:
            print(f"  added   {item['path']}: {human_size(item['size_bytes'])}")

    print("Largest files:")
    for item in inventory["largest_files"][:10]:
        print(f"  {human_size(item['size_bytes']):>10}  {item['path']}")

    if inventory["review_files"]:
        print(f"Review candidates ({len(inventory['review_files'])}):")
        for item in inventory["review_files"][:10]:
            print(f"  {item['path']} — {item['reason']}")
        if len(inventory["review_files"]) > 10:
            print(f"  ... and {len(inventory['review_files']) - 10} more (see JSON report)")

    if duplicate_report is not None:
        print(
            f"Exact duplicate files: {duplicate_report['duplicate_file_count']:,}; "
            f"potential size reduction: {human_size(duplicate_report['potentially_reclaimable_bytes'])}"
        )
        for group in duplicate_report["groups"][:10]:
            print(f"  {human_size(group['size_each_bytes'])} × {len(group['paths'])}: " + " | ".join(group["paths"][:3]))

    if args.report:
        print(f"Report: {args.report.resolve()}")
    if args.write_baseline:
        print(f"Baseline: {args.write_baseline.resolve()}")

    if report["summary"]["budget_exceeded"]:
        print(f"FAIL: build is over the {args.max_size_mib:g} MiB size budget")
        return 1
    if growth_exceeded:
        print(f"FAIL: build grew by more than the {args.max_growth_mib:g} MiB regression budget")
        return 1
    print("PASS: no configured size budget was exceeded")
    return 0


def replace_tokens(value: str, tokens: dict[str, str]) -> str:
    """Replace only documented path tokens; do not invoke a shell."""
    for token, replacement in tokens.items():
        value = value.replace("{" + token + "}", replacement)
    return value


def load_scenario(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            scenario = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read scenario {path}: {exc}") from exc
    if not isinstance(scenario, dict) or scenario.get("scenario_version") != 1:
        raise ValueError("scenario must be a JSON object with scenario_version: 1")
    steps = scenario.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("scenario must contain a non-empty 'steps' array")
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"step {index + 1} must be an object")
        command = step.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(arg, str) for arg in command):
            raise ValueError(f"step {index + 1} needs a non-empty string-array 'command'")
        timeout = step.get("timeout_seconds", 120)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError(f"step {index + 1} timeout_seconds must be greater than zero")
        max_duration = step.get("max_duration_seconds")
        if max_duration is not None and (not isinstance(max_duration, (int, float)) or max_duration <= 0):
            raise ValueError(f"step {index + 1} max_duration_seconds must be greater than zero")
        kill_after = step.get("kill_after_seconds")
        if kill_after is not None and (not isinstance(kill_after, (int, float)) or kill_after <= 0):
            raise ValueError(f"step {index + 1} kill_after_seconds must be greater than zero")
        expected = step.get("expected_exit_codes", [0])
        if not isinstance(expected, list) or not expected or not all(isinstance(code, int) for code in expected):
            raise ValueError(f"step {index + 1} expected_exit_codes must be a non-empty integer array")
        if "continue_on_failure" in step and not isinstance(step["continue_on_failure"], bool):
            raise ValueError(f"step {index + 1} continue_on_failure must be true or false")
        env = step.get("env", {})
        if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
            raise ValueError(f"step {index + 1} env must be an object of string keys and values")
        for field in ("stdout_contains", "stderr_contains"):
            if field in step and (not isinstance(step[field], list) or not all(isinstance(v, str) for v in step[field])):
                raise ValueError(f"step {index + 1} {field} must be a string array")
    return scenario


def run_scenario(args: argparse.Namespace) -> int:
    """Run explicit, game-authored release checks without shell evaluation."""
    scenario_path = args.manifest.resolve()
    try:
        scenario = load_scenario(scenario_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    build = args.build.resolve() if args.build else Path.cwd().resolve()
    if args.build and not build.exists():
        print(f"error: build path does not exist: {build}", file=sys.stderr)
        return 2

    output_root = args.output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    report_dir = output_root / f"run-{run_stamp}"
    report_dir.mkdir()
    workspace = Path(tempfile.mkdtemp(prefix="workspace-", dir=report_dir))
    scenario_dir = scenario_path.parent
    results = []
    started_all = time.monotonic()
    failed = False

    print(f"Scenario: {scenario.get('name', scenario_path.stem)}")
    print(f"Build: {build}")
    for index, step in enumerate(scenario["steps"], start=1):
        step_started = time.monotonic()
        step_name = str(step.get("name", f"step-{index}"))
        if failed and not step.get("continue_on_failure", False):
            results.append({"name": step_name, "passed": None, "skipped": True, "reason": "a previous step failed"})
            print(f"SKIP {step_name}: a previous step failed")
            continue
        step_slug = "".join(c if c.isalnum() or c in "-_." else "_" for c in step_name)[:80]
        step_dir = report_dir / f"{index:02d}-{step_slug or 'step'}"
        step_dir.mkdir(parents=True, exist_ok=True)

        tokens = {
            "build": str(build),
            "scenario_dir": str(scenario_dir),
            "step_dir": str(step_dir),
            "workspace": str(workspace),
            "python": sys.executable,
        }
        command = [replace_tokens(arg, tokens) for arg in step["command"]]
        raw_cwd = step.get("cwd", "{scenario_dir}")
        cwd = Path(replace_tokens(str(raw_cwd), tokens)).expanduser().resolve()
        if not cwd.is_dir():
            results.append({"name": step_name, "passed": False, "error": f"working directory does not exist: {cwd}"})
            failed = True
            print(f"FAIL {step_name}: working directory does not exist: {cwd}")
            continue

        env = os.environ.copy()
        for key, value in step.get("env", {}).items():
            if not isinstance(key, str) or not isinstance(value, str):
                results.append({"name": step_name, "passed": False, "error": "env keys and values must be strings"})
                failed = True
                break
            env[key] = replace_tokens(value, tokens)
        else:
            # The caller supplies argv as a JSON array. No shell is involved,
            # so paths and arguments are not interpreted as shell code.
            try:
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace",
                )
            except OSError as exc:
                results.append({"name": step_name, "passed": False, "error": str(exc), "command": command})
                failed = True
                print(f"FAIL {step_name}: could not start command: {exc}")
                continue

            killed_by_harness = False
            timed_out = False
            kill_after = step.get("kill_after_seconds")
            wait_seconds = kill_after if kill_after is not None else step.get("timeout_seconds", 120)
            try:
                stdout, stderr = process.communicate(timeout=wait_seconds)
            except subprocess.TimeoutExpired:
                if kill_after is not None:
                    killed_by_harness = True
                else:
                    timed_out = True
                process.kill()
                stdout, stderr = process.communicate()

            expected_codes = step.get("expected_exit_codes", [0])
            stdout_needles = step.get("stdout_contains", [])
            stderr_needles = step.get("stderr_contains", [])
            missing_stdout = [needle for needle in stdout_needles if needle not in stdout]
            missing_stderr = [needle for needle in stderr_needles if needle not in stderr]
            elapsed = round(time.monotonic() - step_started, 3)
            max_duration = step.get("max_duration_seconds")
            duration_exceeded = max_duration is not None and elapsed > max_duration
            # A kill-after step passes only when the harness actually had to
            # terminate a still-running process. This makes it useful for
            # interruption tests followed by a separate recovery step.
            passed = (
                not timed_out
                and (killed_by_harness if kill_after is not None else process.returncode in expected_codes)
                and not missing_stdout
                and not missing_stderr
                and not duration_exceeded
            )

            stdout_path = step_dir / "stdout.txt"
            stderr_path = step_dir / "stderr.txt"
            stdout_path.write_text(stdout, encoding="utf-8")
            stderr_path.write_text(stderr, encoding="utf-8")
            result = {
                "name": step_name,
                "passed": passed,
                "command": command,
                "working_directory": str(cwd),
                "return_code": process.returncode,
                "killed_by_harness": killed_by_harness,
                "timed_out": timed_out,
                "elapsed_seconds": elapsed,
                "max_duration_seconds": max_duration,
                "duration_budget_exceeded": duration_exceeded,
                "stdout_file": str(stdout_path),
                "stderr_file": str(stderr_path),
                "missing_stdout_expectations": missing_stdout,
                "missing_stderr_expectations": missing_stderr,
            }
            results.append(result)
            status = "PASS" if passed else "FAIL"
            detail = " (terminated at requested point)" if killed_by_harness else ""
            if timed_out:
                detail = " (timed out)"
            elif duration_exceeded:
                detail = f" (exceeded {max_duration:g}s duration budget)"
            print(f"{status} {step_name}{detail} [{elapsed:.1f}s]")
            if not passed:
                failed = True

    report = {
        "tool": "ReleaseGuard",
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scenario": str(scenario_path),
        "scenario_name": scenario.get("name", scenario_path.stem),
        "build": str(build),
        "workspace": str(workspace),
        "passed": not failed,
        "elapsed_seconds": round(time.monotonic() - started_all, 3),
        "steps": results,
    }
    report_path = args.report.resolve() if args.report else report_dir / "scenario-report.json"
    write_json(report_path, report)
    print(f"Report: {report_path}")
    print("FAIL: scenario had failed steps" if failed else "PASS: all scenario steps passed")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="releaseguard",
        description="Local save protection and game release reliability tools.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("analyze", help="inspect a packaged game build")
    scan.add_argument("build", type=Path, help="root directory of the packaged build")
    scan.add_argument("--baseline", type=Path, help="previous baseline JSON to compare against")
    scan.add_argument("--write-baseline", type=Path, help="write/update a size inventory baseline")
    scan.add_argument("--report", type=Path, help="write the full report as JSON")
    scan.add_argument(
        "--find-duplicates",
        action="store_true",
        help="hash same-size files to identify byte-identical copies (can read large files)",
    )
    scan.add_argument(
        "--max-size-mib",
        type=float,
        help="fail with exit code 1 when total packaged size exceeds this MiB budget",
    )
    scan.add_argument(
        "--max-growth-mib",
        type=float,
        help="fail when total size grew by more than this many MiB versus --baseline",
    )
    scan.set_defaults(handler=analyze)

    scenario = subparsers.add_parser("scenario", help="run game-authored release checks")
    scenario.add_argument("manifest", type=Path, help="JSON scenario manifest")
    scenario.add_argument("--build", type=Path, help="packaged build path, exposed as {build}")
    scenario.add_argument(
        "--output",
        type=Path,
        default=Path("releaseguard-results"),
        help="parent directory for a unique run folder containing logs and JSON report",
    )
    scenario.add_argument("--report", type=Path, help="write JSON report to this path")
    scenario.set_defaults(handler=run_scenario)

    saves = subparsers.add_parser("save", help="make and verify local save snapshots")
    save_commands = saves.add_subparsers(dest="save_command", required=True)
    locate = save_commands.add_parser("locate", help="find common save folders for supported games")
    locate.add_argument("--game", choices=("shadow-of-mordor", "gta-iv", "all"), default="all")
    locate.set_defaults(handler=locate_saves)
    snapshot = save_commands.add_parser("snapshot", help="copy a save file/folder into a hashed snapshot")
    snapshot.add_argument("source", type=Path, help="save file or folder to copy; source is never modified")
    snapshot.add_argument("--output", type=Path, default=Path("releaseguard-saves"), help="folder for snapshots")
    snapshot.add_argument("--name", help="new snapshot folder name; existing snapshots are never overwritten")
    snapshot.set_defaults(handler=create_save_snapshot)
    verify = save_commands.add_parser("verify", help="check a snapshot against its SHA-256 manifest")
    verify.add_argument("snapshot", type=Path, help="snapshot folder containing manifest.json and data/")
    verify.set_defaults(handler=verify_save_snapshot)
    restore = save_commands.add_parser("restore", help="restore a verified snapshot (dry run unless --apply)")
    restore.add_argument("snapshot", type=Path, help="snapshot folder containing manifest.json and data/")
    restore.add_argument("target", type=Path, help="original save file or folder to replace")
    restore.add_argument("--apply", action="store_true", help="perform restore after validating the snapshot")
    restore.set_defaults(handler=restore_save_snapshot)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    max_size_mib = getattr(args, "max_size_mib", None)
    if max_size_mib is not None and max_size_mib <= 0:
        parser.error("--max-size-mib must be greater than zero")
    max_growth_mib = getattr(args, "max_growth_mib", None)
    if max_growth_mib is not None and max_growth_mib < 0:
        parser.error("--max-growth-mib cannot be negative")
    if max_growth_mib is not None and getattr(args, "baseline", None) is None:
        parser.error("--max-growth-mib requires --baseline")
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
