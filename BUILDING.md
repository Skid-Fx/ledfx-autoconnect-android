# Building SkidFx LedFx AutoConnect for Android

This is the build and maintenance guide for the **SkidFx LedFx AutoConnect Android** fork. The Android app uses LedFx engine **2.1.5** and a customized React/TypeScript frontend. The SkidFx release identifier is separate: for this release it is **`v2.1.5-android.3`**. This guide documents the proven WSL build workflow and the custom fixes from the development history; it does **not** claim that a clean-machine rebuild has been tested.

## 1. Verified development environment

| Component | Verified value / source |
| --- | --- |
| Host | Windows with **Ubuntu 22.04 WSL**; build commands run in Ubuntu |
| Host project Python | **3.12.16** (`>=3.12,<3.13` from root `pyproject.toml`) |
| `uv` | **0.13.7**; root `uv.lock` locks the environment |
| Buildozer | **1.6.1.dev0**, pinned via root `uv.lock`; Buildozer Git revision `76bac28545c66bbcc671d49aca553a747d69608e` |
| Java | OpenJDK **17** |
| Android SDK platform | **API 36** |
| Android build tools | **37.0.0** |
| Android NDK | **r28c / 28.2.13676358** |
| Python-for-Android (p4a) | `broccoliboy/python-for-android`, commit **`c02cf781a0d3d232eb4ffbeaf580cc82cf2bd65f`** |
| p4a host / Android Python | **3.11** (host Python 3.11.5 in established build) |
| CMake in project `.venv` | **4.4.4** (checked by build script) |
| NumPy in project `.venv` | **2.3.0** (checked by build script) |
| p4a host setuptools | **84.2.1** (validated by build script) |
| Node.js | **22** managed using NVM (verified local version `v22.23.4`) |
| NVM | **v0.40.3** installed on demand by frontend script |
| Yarn | **Classic 1.22.22** |
| Android ABIs | **`armeabi-v7a`**, **`arm64-v8a`** |
| Package ID | **`com.skidfx.ledfxautoconnect`** |

Development Python 3.12, p4a's host Python 3.11, and the Python packaged into the APK are **different interpreters**. Avoid mixing their site-packages or substituting build-tool versions.

## 2. Get the *complete* source

The application has **two nested Git submodules**: the main project's `deps/ledfx` engine, and that engine's `frontend` source. Both repositories must point to **published, accessible commits** containing the Android modifications; checking in only the parent repository is insufficient.

```bash
git clone --recurse-submodules https://github.com/Skid-Fx/ledfx-autoconnect-android.git
cd ledfx-autoconnect-android
git checkout skidfx-autoconnect
git submodule update --init --recursive
git submodule status --recursive
```

**Release preparation warning:** At the time of the release audit, the `deps/ledfx/frontend` submodule URL was still `https://github.com/YeonV/LedFx-Frontend-v2.git`, even though that checkout had local SkidFx modifications. Before publishing, push the frontend changes to an accessible SkidFx fork, update `deps/ledfx/.gitmodules` and the recorded submodule commit, push the modified LedFx fork, and finally update the main repo's `deps/ledfx` gitlink. After this is done, **verify a recursive fresh clone**. Do not point at an unpushed commit or assume a detached HEAD is a permanent branch.

The original source checkout used during development is `~/AndroidBuilds/ledfx-android-upstream`; do not change the unrelated `~/AndroidBuilds/ledfx-android` checkout. The directory name is not part of the build configuration.

## 3. One-time WSL prerequisites

Install system tools before running the automation: Git, curl, Bash, Python **3.12** with venv support, Java **17**, native build essentials/compiler/linker, `pkg-config`, Ninja, Meson support, C/C++ development headers, `patch`, `zip`/`unzip`, and the standard Android/Buildozer Linux dependencies. The repository's scripts manage pinned application build tools but **do not provision Ubuntu itself**, Java, the host's Python interpreter, or the entire Android SDK from zero. Android SDK licensing and downloads are managed by Buildozer after prerequisites are installed.

Example verification:

```bash
python3.12 --version
java -version
git --version
uv --version
```

Install `uv` **0.13.7** if absent, following its official installation instructions, and make sure `uv` is on `PATH`. `scripts/build_android.sh` creates `.venv` using `uv sync --frozen` only when Buildozer is missing; it assumes a suitable host Python and `uv` are available. On a first checkout you can explicitly initialize:

```bash
uv sync --frozen
```

Do not run `pip install` for arbitrary newer versions into the Android or p4a interpreters. The root dependency lock, custom p4a recipes, and host-tool checks are intentional.

## 4. Standard commands (use these, not manual dependency workarounds)

### Verify/prepare without compiling an APK

```bash
set -o pipefail
./scripts/build_android.sh --prepare-only 2>&1 | tee prepare-android.log
```

This prepares the locked project Python environment, checks or installs pinned CMake/NumPy as needed, verifies the pinned p4a checkout and Android manifest templates, validates the host Python and native recipe fixes, and prepares the frontend Node/Yarn dependencies and TypeScript. `--prepare-only` **does not** compile React or the APK. Note: some setup scripts can update *build-environment* files; it is not a pure read-only audit.

### Build the current application

```bash
set -o pipefail
./scripts/build_android.sh 2>&1 | tee android-build.log
```

This invokes `scripts/prepare_frontend.sh`, copies its compiled React assets into the `ledfx_frontend` Python package, synchronizes the WLED API into existing p4a staging directories, refreshes the Android receiver bytecode, invokes Buildozer, and verifies the Android manifest and receiver bytecode in the final APK. Built-in detailed Buildozer output is also written to `icon-fix-build.log`.

The APK created by the current Android engine version/build configuration is:

```text
bin/ledfxautoconnect-2.1.5-armeabi-v7a_arm64-v8a-debug.apk
```

The `2.1.5` in this APK's **filename** and Android `version.filename` comes from `deps/ledfx/ledfx/consts.py`; the separate SkidFx GitHub release tag is `v2.1.5-android.3`. Do not infer the GitHub release number from the APK filename alone.

### Frontend-only preparation/build

```bash
./scripts/prepare_frontend.sh --prepare-only   # Node, Yarn, dependencies, TypeScript
./scripts/prepare_frontend.sh                  # also compile and sync React assets
```

Frontend source: `deps/ledfx/frontend/src/`; Android build: `yarn buildandroid`; output: `deps/ledfx/frontend/build/`; Python-served assets: `deps/ledfx/ledfx_frontend/`. The latter is part of the LedFx Python package and must retain `__init__.py` and `frontend_config.json` during asset syncing. The frontend `.yarnrc.yml` refers to Yarn Berry plugin files not present in this checkout; the automation intentionally uses **Yarn Classic v1** and sets `YARN_IGNORE_PATH=1`. Use the provided `yarn.lock` with `--frozen-lockfile`.

The frontend build's `prebuildandroid`/`postbuildandroid` scripts modify `package.json`'s `homepage`; fingerprinting in `prepare_frontend.sh` excludes that generated field to avoid needless reinstalls. `.skidfx-*.sha256` stamps and `node_modules` are local build artifacts, **not release source**. The fingerprint check avoids redundant dependency installs/React compilation when input files and tool versions have not changed. TypeScript validation currently runs on every preparation.

### Preserve existing caches

Do **not** delete `.buildozer`, the p4a build distributions, Gradle caches, `.venv`, or `node_modules` as a first troubleshooting step. The scripts intentionally reuse the verified native-build caches. When diagnosing a stale APK, inspect the **actual generated APK**, not only the staging directories. p4a packages Python modules as **`.pyc`** inside `lib/<abi>/libpybundle.so` (a GZIP-compressed TAR archive). `wled_scan.py` may therefore be absent as a `.py` file even when `wled_scan.pyc` is present and correct.

## 5. Script inventory — all repository `scripts/` Python and shell scripts

| Script | Role / when it runs |
| --- | --- |
| `scripts/build_android.sh` | **Main entry point**; pinned environment checks, recipes, frontend, receiver, Buildozer, APK verification; supports `--prepare-only` |
| `scripts/prepare_android_build.sh` | Clone/check exact p4a commit and patch Android manifest templates; called by main script |
| `scripts/prepare_frontend.sh` | Install NVM/Node/Yarn as needed; reuse locked frontend dependencies; TypeScript, React Android build, asset and ABI-cache sync; called by main script |
| `scripts/sync_wled_scan_api.py` | Validate and copy WLED discovery endpoint into already-generated p4a per-ABI staging directories; called before Buildozer |
| `scripts/sync_android_receiver.py` | Sync Android receiver compatibility files into cached source trees; called by main script |
| `scripts/compile_android_receiver.py` | Compile/refresh receiver using p4a's Android-target Python 3.11 bytecode toolchain; called by main script when host Python exists |
| `scripts/audit_build_interpreters.py` | Validate actual build interpreters/setuptools requirements; called by main script |
| `scripts/prepare_aubio.py` | Apply/check cross-Android aubio Meson patch for both ABIs; called by main script |
| `scripts/patch_android_manifest.py` | Patch required foreground service/Android manifest settings; invoked by `prepare_android_build.sh` |
| `scripts/verify_android_manifest.py` | Verify generated AndroidManifest.xml after build; called by main script |
| `scripts/verify_apk_receiver.py` | Inspect packaged `libpybundle.so` bytecode for receiver fix in **both** ABIs; called by main script |
| `scripts/p4a_hook.py` | p4a hook configured by `p4a.hook` in `buildozer.spec`, applied during packaging |
| `scripts/update_icons.py` | Generate Android icon, presplash, TV banner resolutions from LedFx assets; utility; **not called by the main build script** |
| `scripts/clean_ledfx.py` | Repository maintenance/cleanup helper; **do not use as a routine build step or when preserving caches** |

The build also uses customized recipes under `recipes/`: `Pillow`, `aiohttp`, `android`, `aubio-ledfx`, `aubio`, `ifaddr`, `ledfx`, `numpy`, `pybase64`, `pyjnius`, `requests`, `samplerate-ledfx`, `samplerate`, `uvloop`, `vnoise`, and `zeroconf`. Keep the patches in `recipes/Pillow/setup.py.patch` and `recipes/aubio-ledfx/android-cross-python.patch`. The main script checks registered non-isolated build options (`--no-isolation`) across the listed native recipes. The p4a Python host must recognize its expected `setuptools`, `build`, `Cython`, `meson-python`, `ninja`, `numpy`, `wheel`, `packaging`, and `pyproject_hooks` packages. The established pipeline includes recovery checks for conflicting setuptools metadata and invalid host Python include paths in compiled Meson configurations.

## 6. Verify the *actual* APK

Run the built-in validation first:

```bash
python3 scripts/verify_apk_receiver.py \
  bin/ledfxautoconnect-2.1.5-armeabi-v7a_arm64-v8a-debug.apk
```

For frontend and new API verify files inside each bundled archive (this does not change the APK):

```bash
python3 - <<'PY'
import tarfile, zipfile, io
apk = 'bin/ledfxautoconnect-2.1.5-armeabi-v7a_arm64-v8a-debug.apk'
with zipfile.ZipFile(apk) as z:
    for arch in ('armeabi-v7a', 'arm64-v8a'):
        with tarfile.open(fileobj=io.BytesIO(z.read(f'lib/{arch}/libpybundle.so')), mode='r:gz') as t:
            names = t.getnames()
            assert any(n.endswith('/ledfx/api/wled_scan.pyc') for n in names), arch
            assert any(n.endswith('/ledfx_frontend/index.html') for n in names), arch
            print('PASS:', arch, 'WLED discovery API and compiled frontend')
PY
```

Functional phone tests required before publishing: Android startup and service; working audio and LED output; existing automatic WLED IP recovery on hotspot and Wi-Fi; open **Add Device → WLED → search**; discover controller; select **ADD** (populate IP without creating a device prematurely); add it; rescan to confirm **Already Added** is displayed but not selectable; **CANCEL** leaves original IP unchanged; add a second device via **+**; test portrait/landscape; verify GitHub update indicator remains hidden when current and opens the proper release when newer.

## 7. Windows Downloads and wireless debugging

Copy from WSL to Windows Downloads (adjust the Windows username/path for your machine):

```bash
cp -v bin/ledfxautoconnect-2.1.5-armeabi-v7a_arm64-v8a-debug.apk \
  /mnt/c/Users/v8pow/Downloads/LedFx-AutoConnect-WLED-Discovery-Test.apk
sha256sum bin/*.apk /mnt/c/Users/v8pow/Downloads/LedFx-AutoConnect-WLED-Discovery-Test.apk
```

In **Windows PowerShell**, not Ubuntu:

```powershell
adb devices
$device = 'adb-RFGL14XLWML-ChOaRk._adb-tls-connect._tcp' # example: use the ID reported by adb devices
$apk = "$env:USERPROFILE\Downloads\LedFx-AutoConnect-WLED-Discovery-Test.apk"
adb -s $device install -r $apk
adb -s $device shell am force-stop --user 0 com.skidfx.ledfxautoconnect
adb -s $device shell monkey -p com.skidfx.ledfxautoconnect -c android.intent.category.LAUNCHER 1
```

Wireless debug IP:port is **session-dependent**; use the current ADB device identifier. `adb install -r` preserves user data when signatures match. **Do not run** `adb shell pm clear` or uninstall just to refresh a frontend: doing so could erase configured devices.

## 8. Git source publication and releases (nested repositories)

Three Git working trees must be handled **inside out**: frontend → `deps/ledfx` engine → main Android repository. At the release audit, frontend and engine were both detached HEAD checkouts, and frontend still tracked upstream `YeonV/LedFx-Frontend-v2`. They are not safe to publish as-is.

1. Create or identify a writable, public SkidFx frontend fork. Set `deps/ledfx/frontend`'s `origin`/push remote to that fork. Commit the modified frontend source on a named SkidFx branch and push it. Confirm the commit is accessible on GitHub.
2. In the engine repo, update `.gitmodules` to the SkidFx frontend fork URL (not the original upstream), record the new frontend gitlink, and commit the WLED API and updated `ledfx_frontend` asset files on a named branch. Push to the already configured SkidFx LedFx engine repository. Confirm its recorded frontend commit resolves.
3. In the main Android repo on `skidfx-autoconnect`, commit the updated engine gitlink, new frontend/API preparation scripts, `scripts/build_android.sh`, and the current `README.md`/`BUILDING.md`. Push to GitHub.
4. In a separate **fresh clone** using `git clone --recurse-submodules`, run submodule status and source/package checks. Validate a normal build when practical; at minimum, confirm `./scripts/build_android.sh --prepare-only` and absence of missing checkout files. The original successful phone build was on the established WSL cache, not a pristine build environment.
5. Create tag **`v2.1.5-android.3`** on the pushed main commit. Attach the **tested APK**, not a newly inferred or stale file. Set its release name and assets consistently. Do **not** mark it draft/prerelease accidentally unless intended: the frontend update checker enumerates releases (including prereleases), excludes drafts, compares SkidFx tags, and requires an `.apk` asset. Existing `v2.1.5-android.2` must remain available.

Do not add to Git: `.venv`, `.buildozer`, `node_modules`, frontend `build/`, `*.apk`, log files, local fingerprint stamps (e.g. `ledfx_frontend/.skidfx-build.sha256`) or user secrets. Do include generated frontend assets needed by the packaged `ledfx_frontend` Python package. The HTML/JS/CSS and hashed filenames will change on release; review removals and additions rather than assuming deleted obsolete hashes indicate broken files.

For a future release, update **`deps/ledfx/frontend/src/config/skidfxRelease.ts`** (`SKIDFX_VERSION`) and the dashboard will display the shared version; the GitHub update button compares that string to `vX.Y.Z-android.N` tags. Updating the underlying LedFx `PROJECT_VERSION` is a separate decision, and changing it affects APK naming/Android version behavior.

## 9. Handoff: where to work next time

- Main repo: `~/AndroidBuilds/ledfx-android-upstream`, branch `skidfx-autoconnect`.
- Backend WLED discovery: `deps/ledfx/ledfx/api/wled_scan.py` (POST start, GET status/progress/results, DELETE cancellation); **do not accidentally change** proven AutoConnect network detection in `deps/ledfx/ledfx/mdns_manager.py`.
- Popup: `deps/ledfx/frontend/src/components/Dialogs/WledDiscoveryDialog.tsx`.
- Form integration: `AddDeviceDialog.tsx`, `SchemaForm.tsx` and props, `BladeSelect.tsx` and props.
- Main UI: `pages/Home/Dashboard.tsx`, `components/AddButton/AddB.styles.tsx`.
- Update checker: `components/Bars/BarTop/BarTop.tsx`, `Title.tsx`, shared `src/config/skidfxRelease.ts`.
- Build automation: `scripts/build_android.sh`, `scripts/prepare_frontend.sh`, `scripts/sync_wled_scan_api.py` plus the established scripts in section 5.
- Pinned Android service and UI have been tested with working Wi-Fi/hotspot WLED discovery; do not change auto-reconnect or clear known working caches without a specific failure.

## 10. Credits

[LedFx](https://github.com/LedFx/LedFx) · [broccoliboy Android port](https://github.com/broccoliboy/ledfx-android) · [SkidFx Android project](https://github.com/Skid-Fx/ledfx-autoconnect-android)
