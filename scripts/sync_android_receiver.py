#!/usr/bin/env python3
"""Synchronize Android receiver fixes into cached p4a builds."""

from pathlib import Path

source = Path("recipes/android/src/android/broadcast.py")

if not source.is_file():
    raise SystemExit(f"ERROR: Receiver source missing: {source}")

content = source.read_bytes()

if b"RECEIVER_NOT_EXPORTED" not in content:
    raise SystemExit("ERROR: Receiver security fix missing from source")

base = Path(
    ".buildozer/android/platform/"
    "build-armeabi-v7a_arm64-v8a"
)

targets = []

for arch in ("armeabi-v7a", "arm64-v8a"):
    recipe = (
        base / "build/other_builds/android-genericndkbuild"
        / f"{arch}__ndk_target_24/android"
    )

    installed = (
        base / "build/python-installs/ledfxautoconnect"
        / arch / "android"
    )

    targets.extend([
        recipe / "android/broadcast.py",
        recipe / "build/lib.linux-x86_64-cpython-311/android/broadcast.py",
        installed / "broadcast.py",
    ])

updated = 0

for target in targets:
    if not target.is_file():
        continue

    if target.read_bytes() != content:
        target.write_bytes(content)
        updated += 1
        print(f"UPDATED: {target}")
    else:
        print(f"PASS: {target}")

    bytecode = target.with_suffix(".pyc")

    if bytecode.exists():
        bytecode.unlink()
        print(f"REMOVED STALE BYTECODE: {bytecode}")

for arch in ("armeabi-v7a", "arm64-v8a"):
    installed = (
        base / "build/python-installs/ledfxautoconnect"
        / arch / "android/broadcast.py"
    )

    if installed.is_file() and installed.read_bytes() != content:
        raise SystemExit(f"ERROR: Receiver mismatch: {arch}")

print(f"PASS: Receiver synchronized; {updated} files updated")
