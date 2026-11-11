# LedFx AutoConnect for Android — SkidFx

An Android version of [LedFx](https://github.com/LedFx/LedFx), with improved WLED device discovery and automatic recovery when a controller's IP address changes.

Based on the [Android port by broccoliboy](https://github.com/broccoliboy/ledfx-android). This project uses the LedFx **2.1.5** engine with Android-specific modifications.

## Features

- Run LedFx directly on a compatible Android device.
- Control WLED controllers with real-time audio-reactive lighting effects.
- **Find WLED controllers when adding devices:** In **Add Device → WLED**, tap the magnifying-glass button to search the phone's Wi-Fi and hotspot networks. Discovery lists a controller's name, IP address, and WLED version. Select a new controller and tap **ADD** to populate the IP address field, then complete the standard Add Device form.
- **See already-added WLED controllers:** Devices already configured in LedFx still appear in discovery results, marked **Already Added**, and cannot be selected again.
- Cancel a manual discovery scan without changing the IP address field or automatically creating a device.
- Automatically reconnect to previously configured WLED controllers if their IP addresses change, including after switching supported networks.
- Keep the LedFx service running while the Android screen is off, with Android-specific service lifecycle handling.

## Two different WLED discovery functions

**Manual Add Device discovery** searches for available WLED controllers, including unconfigured devices. The user chooses a device; discovery never adds it automatically. Already-added devices appear as disabled entries.

**AutoConnect** independently monitors previously configured WLED controllers and searches for their current IP addresses if communication fails or the network changes. AutoConnect does not require opening the Add Device dialog.

Both use the Android network-interface detection used by the existing LedFx AutoConnect implementation. Manual discovery also reports scan progress and scanned networks.

## Downloads

Download Android APKs from [SkidFx AutoConnect releases](https://github.com/Skid-Fx/ledfx-autoconnect-android/releases).

The Android release series uses tags such as `v2.1.5-android.3`. The suffix is specific to this Android fork; it does not change the underlying LedFx engine's `2.1.5` version.

## Build from source

See **[BUILDING.md](BUILDING.md)** for the exact WSL/Ubuntu environment, pinned Android and frontend dependencies, recursive submodules, all automation scripts, build instructions, APK verification, and wireless installation.

The short version is:

```bash
git clone --recurse-submodules https://github.com/Skid-Fx/ledfx-autoconnect-android.git
cd ledfx-autoconnect-android
git checkout skidfx-autoconnect
git submodule update --init --recursive
./scripts/build_android.sh --prepare-only
./scripts/build_android.sh
```

The documented host prerequisites must be installed first. The build script prepares pinned dependencies and reuses caches; it is not a complete OS provisioning tool.

## Source and credits

- [SkidFx AutoConnect Android source](https://github.com/Skid-Fx/ledfx-autoconnect-android)
- [SkidFx modified LedFx engine](https://github.com/Skid-Fx/LedFx)
- [LedFx upstream](https://github.com/LedFx/LedFx)
- [Original Android port](https://github.com/broccoliboy/ledfx-android)

LedFx is developed by the LedFx community. All applicable upstream copyright notices and licenses remain in effect. This is an independent, unofficial Android build and is not supported by the LedFx team.
