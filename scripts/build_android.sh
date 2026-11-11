#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== LedFx AutoConnect Android build ==="

VENV="$PWD/.venv"
CMAKE="$VENV/bin/cmake"

# uv is installed as a user-level tool, not necessarily inside .venv.
UV="$(command -v uv || true)"

if [ -z "$UV" ]; then
    echo "ERROR: uv is not installed or is missing from PATH"
    exit 1
fi

# Recreate the pinned Python environment on a fresh checkout.
if [ ! -x "$VENV/bin/buildozer" ]; then
    echo "=== Creating pinned Buildozer environment ==="
    "$UV" sync --frozen

    test -x "$VENV/bin/buildozer" || {
        echo "ERROR: Buildozer environment setup failed"
        exit 1
    }
fi

# Install the verified CMake version when necessary.
VERSION="$("$CMAKE" --version 2>/dev/null | head -n 1 || true)"

if [ "$VERSION" != "cmake version 4.4.4" ]; then
    "$UV" pip install \
        --python "$VENV/bin/python" \
        "cmake==4.4.4"
fi

# MESON_NUMPY_CHECK: Ensure Meson's Python can import NumPy.
echo "=== Preparing Meson Python environment ==="

if ! "$VENV/bin/python" -c 'import numpy; assert numpy.__version__ == "2.3.0"' 2>/dev/null; then
    echo "Installing verified NumPy 2.3.0 into project environment"
    "$UV" pip install --python "$VENV/bin/python" "numpy==2.3.0"
fi

"$VENV/bin/python" - <<'PYNUMPYCHECK'
import sys
import numpy

assert numpy.__version__ == "2.3.0", "Unexpected NumPy version"
print("PASS: Meson Python:", sys.executable)
print("PASS: NumPy:", numpy.__version__)
PYNUMPYCHECK

# Keep the correct CMake in PATH throughout the build.
export VIRTUAL_ENV="$VENV"
export PATH="$VENV/bin:$PATH"

echo "Using $(cmake --version | head -n 1)"

# Prepare pinned Python-for-Android and Android manifest.
./scripts/prepare_android_build.sh

# Synchronize Android receiver compatibility fixes into cached builds.
python3 scripts/sync_android_receiver.py

# Repair conflicting setuptools metadata in the p4a host Python.
# The Pillow recipe installs setuptools 84.2.1 when needed.
HOSTPY_SITE="$PWD/.buildozer/android/platform/build-armeabi-v7a_arm64-v8a/build/other_builds/hostpython3/desktop/hostpython3/native-build/Lib/site-packages"

python3 - "$HOSTPY_SITE" <<'PYSETUP'
from pathlib import Path
import sys

site = Path(sys.argv[1])
current = site / "setuptools-84.2.1.dist-info"

if not site.is_dir():
    print("INFO: Host Python not built yet")
elif not current.is_dir():
    print("INFO: setuptools 84.2.1 will be prepared by the Pillow recipe")
else:
    stale = list(site.glob("setuptools-*.egg-info"))
    stale += [
        p for p in site.glob("setuptools-*.dist-info")
        if p != current
    ]

    backup = site.parent / "setuptools-metadata-backup"

    for item in stale:
        destination = backup / item.name
        if destination.exists():
            print(f"WARNING: Obsolete setuptools metadata returned: {item.name}")

        number = 1
        while destination.exists():
            destination = backup / f"{item.name}.repeat-{number}"
            number += 1

        backup.mkdir(exist_ok=True)
        item.rename(destination)
        print(f"PASS: Quarantined obsolete metadata: {item.name}")

    print("PASS: setuptools 84.2.1 metadata verified")
PYSETUP

# Verify setuptools using the actual p4a host Python 3.11.
HOSTPY_HOME="$(dirname "$(dirname "$HOSTPY_SITE")")"

if [ -x "$HOSTPY_HOME/python3" ]; then
    PYTHONPATH="$HOSTPY_HOME/Lib:$HOSTPY_SITE:$HOSTPY_HOME/build/lib.linux-x86_64-3.11" \
    "$HOSTPY_HOME/python3" - <<'PYHOSTCHECK'
import sys
from importlib.metadata import version
import setuptools

assert sys.version_info[:2] == (3, 11), "Incorrect host Python version"
assert version("setuptools") == "84.2.1", "Incorrect setuptools metadata"
assert setuptools.__version__ == "84.2.1", "Incorrect imported setuptools"

print("PASS: Host Python 3.11 recognizes setuptools 84.2.1")
PYHOSTCHECK
else
    echo "INFO: Host Python not built yet; verification deferred"
fi

# Verify host Python modules required by native package builds.
echo "=== Checking host Python build dependencies ==="

if [ -x "$HOSTPY_HOME/python3" ]; then
    PYTHONPATH="$HOSTPY_HOME/Lib:$HOSTPY_SITE:$HOSTPY_HOME/build/lib.linux-x86_64-3.11" \
    "$HOSTPY_HOME/python3" - <<'PYMODULECHECK'
from importlib import import_module
from importlib.metadata import version

requirements = {
    "build": "build",
    "Cython": "Cython",
    "meson-python": "mesonpy",
    "ninja": "ninja",
    "numpy": "numpy",
    "setuptools": "setuptools",
    "wheel": "wheel",
    "packaging": "packaging",
    "pyproject_hooks": "pyproject_hooks",
}

failures = []

for package, module in requirements.items():
    try:
        import_module(module)
        print(f"PASS: {package} {version(package)}")
    except Exception as exc:
        print(f"ERROR: {package}: {exc}")
        failures.append(package)

if failures:
    raise SystemExit("ERROR: Host Python dependencies need repair")
PYMODULECHECK
else
    echo "INFO: Host Python not built yet; module checks deferred"
fi

python3 scripts/audit_build_interpreters.py

# Verify the recovered cross-compilation fixes.
test -s recipes/Pillow/setup.py.patch || {
    echo "ERROR: Missing Pillow patch"
    exit 1
}

test -s recipes/aubio-ledfx/android-cross-python.patch || {
    echo "ERROR: Missing aubio patch"
    exit 1
}

grep -Fq 'patches = ["setup.py.patch"]' recipes/Pillow/__init__.py || {
    echo "ERROR: Pillow patch is not registered"
    exit 1
}

grep -Fq 'patches = ["android-cross-python.patch"]' recipes/aubio-ledfx/__init__.py || {
    echo "ERROR: Aubio patch is not registered"
    exit 1
}

# ISOLATIONCHECK: Verify previously recovered non-isolated recipes.
echo "=== Checking Python build isolation settings ==="

for recipe in \
    numpy Pillow vnoise aubio-ledfx samplerate-ledfx \
    pyjnius android aubio ledfx pybase64 requests \
    samplerate uvloop zeroconf
do
    file="recipes/$recipe/__init__.py"

    if [ ! -f "$file" ]; then
        echo "ERROR: Missing recipe: $recipe"
        exit 1
    fi

    if ! grep -Fq -- '--no-isolation' "$file"; then
        echo "ERROR: Missing --no-isolation in $recipe"
        exit 1
    fi

    echo "PASS: $recipe isolation setting present"
done

python3 scripts/prepare_aubio.py

# AUBIOCHECK: Inspect active aubio source and generated build.
echo "=== Checking aubio Android cross-compilation ==="

python3 - <<'PYAUBIOCHECK'
from pathlib import Path

base = Path(".buildozer/android/platform/build-armeabi-v7a_arm64-v8a/build/other_builds/aubio-ledfx")

problems = []

for arch in ("armeabi-v7a", "arm64-v8a"):
    root = base / f"{arch}__ndk_target_24/aubio-ledfx"
    source = root / "python/meson.build"
    ninja = root / "p4a_android_build/build.ninja"

    print(f"--- {arch} ---")

    if not source.exists():
        print("INFO: Source not extracted yet")
        continue

    content = source.read_text()

    for line in content.splitlines():
        if any(x in line for x in (
            "shared_module(",
            "py.extension_module(",
            "py.dependency("
        )):
            print("SOURCE:", line.strip())

    if "py.extension_module(" in content or "py.dependency(" in content:
        problems.append(f"{arch}: Original host-Python Meson configuration remains")

    if ninja.exists():
        generated = ninja.read_text()
        host_paths = [
            "/include/python3.12",
            "/usr/local/include/python3.11",
        ]
        found = [x for x in host_paths if x in generated]

        if found:
            print("ERROR: Generated compiler flags contain:", ", ".join(found))
            problems.append(f"{arch}: Generated Meson build uses host Python headers")
        else:
            print("PASS: No known host Python headers in generated flags")
    else:
        print("INFO: Meson build not generated yet")

if problems:
    for problem in problems:
        print("ERROR:", problem)
    raise SystemExit("Aubio cross-compilation verification failed")

print("PASS: Aubio cross-compilation checks completed")
PYAUBIOCHECK

if [ "${1:-}" = "--prepare-only" ]; then
    ./scripts/prepare_frontend.sh --prepare-only
    echo "PASS: Environment preparation checks completed"
    echo "No Android compilation started"
    exit 0
fi

if [ "$#" -ne 0 ]; then
    echo "Usage: $0 [--prepare-only]"
    exit 2
fi

# Prepare and package the current React frontend before Android compilation.
./scripts/prepare_frontend.sh
python3 scripts/sync_wled_scan_api.py

# Refresh Android receiver bytecode using Python 3.11.
# Cached distributions may otherwise package outdated receiver code.
HOSTPY="$PWD/.buildozer/android/platform/build-armeabi-v7a_arm64-v8a/build/other_builds/hostpython3/desktop/hostpython3/native-build/python3"

if [ -x "$HOSTPY" ]; then
    "$HOSTPY" scripts/compile_android_receiver.py
else
    echo "INFO: Android host Python not built yet; normal build will generate it"
fi

# Run Buildozer with its existing compilation cache.
"$VENV/bin/buildozer" android debug \
    2>&1 | tee icon-fix-build.log

# Verify the generated Android manifest after successful compilation.
MANIFEST="$PWD/.buildozer/android/platform/build-armeabi-v7a_arm64-v8a/dists/ledfxautoconnect/src/main/AndroidManifest.xml"

python3 scripts/verify_android_manifest.py "$MANIFEST"

# Verify the receiver bytecode inside the actual packaged APK.
APK="$PWD/bin/ledfxautoconnect-2.1.5-armeabi-v7a_arm64-v8a-debug.apk"

python3 scripts/verify_apk_receiver.py "$APK"
