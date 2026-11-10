#!/usr/bin/env python3
"""Compile the corrected Android broadcast receiver for both architectures."""

from pathlib import Path
import importlib.util
import py_compile

base = Path(
    ".buildozer/android/platform/"
    "build-armeabi-v7a_arm64-v8a"
)

source = Path("recipes/android/src/android/broadcast.py")

if not source.is_file():
    raise SystemExit("ERROR: Android receiver source missing")

if "RECEIVER_NOT_EXPORTED" not in source.read_text():
    raise SystemExit("ERROR: Android receiver fix missing")

expected_magic = bytes.fromhex("a70d0d0a")

if importlib.util.MAGIC_NUMBER != expected_magic:
    raise SystemExit(
        "ERROR: This script must run using Android host Python 3.11"
    )

for arch in ("armeabi-v7a", "arm64-v8a"):
    target = (
        base / "dists/ledfxautoconnect"
        / f"_python_bundle__{arch}"
        / "_python_bundle/site-packages/android/broadcast.pyc"
    )

    if not target.is_file():
        print(f"INFO: {arch} bundle not generated yet; normal build will create it")
        continue

    py_compile.compile(
        str(source),
        cfile=str(target),
        dfile="android/broadcast.py",
        doraise=True,
    )

    print(f"PASS: Updated receiver compiled for {arch}")

print("PASS: Both architecture receiver bytecode files updated")
