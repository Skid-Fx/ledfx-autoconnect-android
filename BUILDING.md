# Building LedFx AutoConnect for Android

These instructions explain how to build LedFx AutoConnect for Android from source.

The project is based on LedFx 2.1.5 and the Android port by broccoliboy.

## 1. Verified development environment

| Component | Version |
|---|---|
| Operating system | Ubuntu 22.04 under WSL |
| Python | 3.12.16 |
| uv | 0.13.7 |
| Buildozer | 1.6.1.dev0 |
| Java | OpenJDK 17 |
| Android SDK Platform | API 36 |
| Android Build Tools | 37.0.0 |
| Android NDK | r28c (28.2.13676358) |
| Python-for-Android | c02cf781a0d3d232eb4ffbeaf580cc82cf2bd65f |
| Architectures | armeabi-v7a, arm64-v8a |

The Python development environment is separate from the Python runtime packaged inside the Android application.

## 2. Get the source code

Clone the repository with its LedFx engine submodule:

    git clone --recurse-submodules https://github.com/Skid-Fx/ledfx-autoconnect-android.git
    cd ledfx-autoconnect-android

## 3. Prepare the build environment

Install Python 3.12, Java 17, Git, and the Android build prerequisites on Ubuntu 22.04 or WSL. The verified toolchain versions are listed above.

Create a Python environment and install the locked dependencies:

    python3.12 -m venv .venv
    .venv/bin/python -m pip install uv==0.13.7
    .venv/bin/uv sync --locked --no-dev

## 4. Prepare and build Android

    ./scripts/prepare_android_build.sh
    .venv/bin/buildozer android debug

Buildozer manages Android SDK/NDK downloads. Accept Android SDK licenses when requested. The APK should be generated in the bin directory.

## 5. Build verification

The existing working APK was tested on Android. A completely fresh source build has not yet been verified. Confirm the generated service manifest, Python service code, patched LedFx engine, and both ARM architectures before releasing a newly compiled APK.

## 6. Upstream projects

LedFx: https://github.com/LedFx/LedFx

Original Android port: https://github.com/broccoliboy/ledfx-android

Modified engine: https://github.com/Skid-Fx/LedFx

## 7. Release versioning

The first planned GitHub release tag is v2.1.5-android.1, based on LedFx 2.1.5.
