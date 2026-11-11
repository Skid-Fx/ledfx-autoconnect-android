#!/usr/bin/env python3
"""Synchronize the WLED discovery API into cached Android distributions."""

from pathlib import Path
import py_compile
import shutil

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "deps/ledfx/ledfx/api/wled_scan.py"
DIST = (
    ROOT / ".buildozer/android/platform/"
    "build-armeabi-v7a_arm64-v8a/dists/ledfxautoconnect"
)

if not SOURCE.is_file():
    raise SystemExit("ERROR: WLED scan API source is missing")

py_compile.compile(str(SOURCE), doraise=True)
print("PASS: WLED scan API syntax")

for arch in ("armeabi-v7a", "arm64-v8a"):
    api_dir = (
        DIST / f"_python_bundle__{arch}"
        / "_python_bundle/site-packages/ledfx/api"
    )

    if not api_dir.is_dir():
        print(f"INFO: {arch} API cache not generated yet")
        continue

    destination = api_dir / "wled_scan.py"

    if destination.is_file() and destination.read_bytes() == SOURCE.read_bytes():
        print(f"PASS: {arch} WLED API already current")
        continue

    shutil.copy2(SOURCE, destination)

    if destination.read_bytes() != SOURCE.read_bytes():
        raise SystemExit(f"ERROR: {arch} WLED API verification failed")

    print(f"PASS: {arch} WLED API synchronized")

print("PASS: WLED API synchronization completed")
