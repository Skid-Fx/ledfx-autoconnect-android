#!/usr/bin/env python3
from pathlib import Path
import os
import subprocess
import sys

project = Path(__file__).resolve().parent.parent
build = project / ".buildozer/android/platform/build-armeabi-v7a_arm64-v8a/build/other_builds"

host = build / "hostpython3/desktop/hostpython3/native-build"
site = host / "Lib/site-packages"

pythonpath = os.pathsep.join(map(str, (
    host / "Lib",
    site,
    host / "build/lib.linux-x86_64-3.11",
)))

probe = r'''
import sys
from pathlib import Path
from importlib import metadata

print("Executable:", sys.executable)

try:
    version = metadata.version("setuptools")
    print("Setuptools metadata version:", version)
except Exception as exc:
    version = None
    print("Setuptools metadata error:", exc)

try:
    import setuptools
    print("Setuptools imported version:", setuptools.__version__)
    print("Setuptools module:", setuptools.__file__)
except Exception as exc:
    print("Setuptools import error:", exc)

for dist in metadata.distributions():
    if (dist.metadata.get("Name") or "").lower() == "setuptools":
        print("Metadata candidate:", dist.version, getattr(dist, "_path", "?"))

if version is None or tuple(map(int, version.split(".")[:2])) < (80, 0):
    sys.exit(2)
'''

failures = []

for arch in ("armeabi-v7a", "arm64-v8a"):
    executable = (
        build / "python3" / f"{arch}__ndk_target_24" /
        "python3/android-build/python3"
    )

    print(f"\n=== {arch} ===", flush=True)

    if not executable.is_file():
        print("DEFERRED: Android build Python not created yet")
        continue

    for mode in ("inherited environment", "host Python path"):
        env = os.environ.copy()

        if mode == "host Python path":
            env["PYTHONPATH"] = pythonpath

        result = subprocess.run(
            [str(executable), "-c", probe],
            cwd=project,
            env=env,
            text=True,
            capture_output=True,
        )

        print(f"\n--- {mode} ---")
        print(result.stdout.strip())

        if result.stderr.strip():
            print("STDERR:", result.stderr.strip()[-800:])

        if result.returncode:
            if mode == "inherited environment":
                print("INFO: Inherited environment needs recipe PYTHONPATH")
            else:
                failures.append(f"{arch}: {mode}")

print("\n=== Samplerate recipe environment configuration ===")
recipe = project / "recipes/samplerate-ledfx/__init__.py"
lines = recipe.read_text().splitlines()

for index, line in enumerate(lines):
    if "def get_recipe_env(" in line:
        print("\n".join(
            f"{number + 1}: {lines[number]}"
            for number in range(index, min(index + 35, len(lines)))
        ))

if "AUTO_HOSTPY_PYTHONPATH" not in recipe.read_text():
    failures.append("samplerate recipe missing automatic Python path")

if failures:
    print("\nERROR: Python environment discrepancies detected:")
    for failure in failures:
        print(" -", failure)
    sys.exit(1)

print("\nPASS: Both Android build interpreters recognize setuptools >=80")
