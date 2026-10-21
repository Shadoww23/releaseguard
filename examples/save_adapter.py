#!/usr/bin/env python3
"""Tiny example adapter showing the save-safety scenario contract.

This is not a game save implementation. It demonstrates how a game's test
build or engine adapter can seed a known-good slot, get interrupted during a
write, and then verify that the prior committed slot is still loadable.
"""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path


def atomic_save(slot: Path, data: dict) -> None:
    """Write a complete new save and atomically replace the old slot."""
    slot.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=slot.name + ".", suffix=".pending", dir=slot.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, slot)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("seed", "interrupt-unsafe", "interrupt-atomic", "verify"),
    )
    parser.add_argument("slot", type=Path)
    args = parser.parse_args()

    if args.action == "seed":
        atomic_save(args.slot, {"format": 1, "coins": 125, "checkpoint": "harbor"})
        print("seeded known-good save")
        return 0

    if args.action == "interrupt-unsafe":
        # Model a game that truncates its only good save before writing the
        # replacement. The harness kills this process after the partial bytes
        # reach disk, leaving an unreadable live save behind.
        args.slot.parent.mkdir(parents=True, exist_ok=True)
        with args.slot.open("w", encoding="utf-8") as handle:
            handle.write('{"format":1,"coins":999')
            handle.flush()
            os.fsync(handle.fileno())
        print("partial data replaced the live save; waiting to be terminated")
        time.sleep(300)
        return 2  # Reaching this means the harness failed to interrupt it.

    if args.action == "interrupt-atomic":
        # Simulate a crash while writing a replacement to a sibling temporary
        # file. The previous committed slot stays intact until os.replace.
        args.slot.parent.mkdir(parents=True, exist_ok=True)
        pending = args.slot.with_name(args.slot.name + ".pending")
        with pending.open("w", encoding="utf-8") as handle:
            handle.write('{"format":1,"coins":999')
            handle.flush()
            os.fsync(handle.fileno())
        print("partial replacement staged separately; waiting to be terminated")
        time.sleep(300)
        return 2  # Reaching this means the harness failed to interrupt it.

    try:
        data = json.loads(args.slot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"save is unreadable: {exc}")
        return 1
    if data.get("format") != 1 or data.get("coins") != 125 or data.get("checkpoint") != "harbor":
        print(f"known-good save contents changed unexpectedly: {data}")
        return 1
    print("previous committed save is intact and loadable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
