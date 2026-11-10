"""LedFx Android packaging hooks."""

from pathlib import Path
import subprocess


def before_apk_build(toolchain):
    """Refresh receiver bytecode before creating libpybundle.so."""

    project = Path(__file__).resolve().parent.parent

    hostpython = (
        project
        / ".buildozer/android/platform/"
          "build-armeabi-v7a_arm64-v8a/build/other_builds/"
          "hostpython3/desktop/hostpython3/native-build/python3"
    )

    compiler = project / "scripts/compile_android_receiver.py"

    if not hostpython.is_file():
        raise RuntimeError("Android host Python 3.11 is missing")

    print("=== Refreshing Android receiver before APK packaging ===", flush=True)

    subprocess.run(
        [str(hostpython), str(compiler)],
        cwd=project,
        check=True,
    )

    print("PASS: Android receiver packaging hook completed", flush=True)
