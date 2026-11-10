#!/usr/bin/env python3
from pathlib import Path
import subprocess

patch = Path("recipes/aubio-ledfx/android-cross-python.patch")
assert patch.is_file(), "Aubio patch missing"

base = Path(
    ".buildozer/android/platform/"
    "build-armeabi-v7a_arm64-v8a/build/other_builds/aubio-ledfx"
)

for arch in ("armeabi-v7a", "arm64-v8a"):
    root = base / f"{arch}__ndk_target_24/aubio-ledfx"
    source = root / "python/meson.build"

    if not source.is_file():
        print(f"INFO: {arch}: source not extracted yet")
        continue

    content = source.read_text()

    if "py.extension_module(" in content or "py.dependency()" in content:
        result = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-d", str(root)],
            input=patch.read_text(),
            text=True,
            capture_output=True
        )

        if result.returncode:
            raise SystemExit(
                f"ERROR: {arch}: patch failed\\n"
                + result.stdout + result.stderr
            )

        print(f"PASS: {arch}: aubio patch applied")

    content = source.read_text()

    if "shared_module('_aubio'," not in content:
        raise SystemExit(f"ERROR: {arch}: shared_module missing")

    if "py.dependency()" in content or "py.extension_module(" in content:
        raise SystemExit(f"ERROR: {arch}: host Python dependency remains")

    print(f"PASS: {arch}: source uses Android-compatible module")

    build = root / "p4a_android_build"
    ninja = build / "build.ninja"

    if ninja.is_file():
        generated = ninja.read_text()

        bad = any(x in generated for x in (
            "/include/python3.12",
            "/usr/local/include/python3.11",
            "cpython-311-x86_64-linux-gnu.so"
        ))

        if bad:
            number = 1
            while (root / f"p4a_android_build.bad-{number}").exists():
                number += 1

            backup = root / f"p4a_android_build.bad-{number}"
            build.rename(backup)

            print(f"PASS: {arch}: invalid Meson configuration backed up")

print("PASS: Automated aubio preparation complete")
