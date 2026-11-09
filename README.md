# LedFx AutoConnect for Android

An Android version of [LedFx](https://github.com/LedFx/LedFx), featuring automatic reconnection to WLED controllers when their network addresses change.

Based on the Android port originally developed by [broccoliboy](https://github.com/broccoliboy/ledfx-android).

## About

LedFx is an open-source application that creates real-time audio-reactive lighting effects for LED devices.

LedFx AutoConnect for Android brings LedFx to Android devices and adds improvements for maintaining connections to WLED controllers.

The application uses the LedFx 2.1.5 engine with Android-specific modifications.

## Features

- Run LedFx directly on an Android device.
- Control compatible WLED devices.
- Generate real-time audio-reactive LED effects.
- Automatically reconnect to previously configured WLED controllers when their IP addresses change.
- Detect controllers after switching between supported networks.
- Continue running the LedFx service while the Android screen is off.
- Stop the background service when the application is closed through Android's Recent Apps interface.

## AutoConnect

The AutoConnect modifications help LedFx recover connections when a WLED controller receives a different IP address.

This is particularly useful when moving between Wi-Fi networks or using a mobile hotspot.

The application periodically checks controller connectivity and searches for previously configured controllers when reconnection is needed.

## Downloads

Android APK releases will be published on the
[GitHub Releases page](https://github.com/Skid-Fx/ledfx-autoconnect-android/releases).

The initial planned release is **v2.1.5-android.1**.

The Android release identifier is separate from the underlying LedFx engine version.

## Building from Source

The project uses:

- Python 3.12 for the development environment
- Buildozer and Python-for-Android
- Java 17
- Android SDK API 36
- Android NDK r28c
- Custom Python-for-Android recipes

Detailed installation and compilation instructions are provided in [BUILDING.md](BUILDING.md).

The LedFx engine is included as a Git submodule. Clone the project with submodules enabled.

## Source Code

The project incorporates two upstream projects:

**LedFx engine:**
https://github.com/LedFx/LedFx

**Original Android port:**
https://github.com/broccoliboy/ledfx-android

**Modified LedFx engine:**
https://github.com/Skid-Fx/LedFx

**LedFx AutoConnect for Android:**
https://github.com/Skid-Fx/ledfx-autoconnect-android

## Credits

LedFx was created and developed by the LedFx open-source community.

The original LedFx Android port was developed by broccoliboy.

LedFx AutoConnect for Android builds on their work with additional Android integration and WLED reconnection improvements.

All original third-party copyright notices and applicable licenses remain in effect.

## Project Status

The Android source code and custom build configuration are available in this repository.

The automated build procedure and first public APK release are being finalized.
