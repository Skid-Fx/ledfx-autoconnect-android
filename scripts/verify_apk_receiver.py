#!/usr/bin/env python3
"""Verify Android receiver bytecode inside the final APK."""

import io
import marshal
import sys
import tarfile
import types
import zipfile
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("Usage: verify_apk_receiver.py APK_PATH")

apk = Path(sys.argv[1])

if not apk.is_file():
    raise SystemExit(f"ERROR: APK not found: {apk}")

def all_names(code):
    yield from code.co_names
    for item in code.co_consts:
        if isinstance(item, types.CodeType):
            yield from all_names(item)

with zipfile.ZipFile(apk) as package:
    for arch in ("armeabi-v7a", "arm64-v8a"):
        bundle_name = f"lib/{arch}/libpybundle.so"

        try:
            bundle = package.read(bundle_name)
        except KeyError:
            raise SystemExit(f"FAIL: Missing {bundle_name}")

        with tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz") as archive:
            member = archive.extractfile(
                "_python_bundle/site-packages/android/broadcast.pyc"
            )

            if member is None:
                raise SystemExit(f"FAIL: Receiver missing for {arch}")

            data = member.read()

        if data[:4] != bytes.fromhex("a70d0d0a"):
            raise SystemExit(f"FAIL: Incorrect Python bytecode version: {arch}")

        code = marshal.loads(data[16:])

        if "RECEIVER_NOT_EXPORTED" not in set(all_names(code)):
            raise SystemExit(f"FAIL: Outdated receiver in APK: {arch}")

        print(f"PASS: {arch} receiver fix verified inside APK")

print("PASS: Both APK receiver bundles verified")
