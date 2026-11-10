#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

P4A_DIR=".buildozer/android/platform/python-for-android"
P4A_REPO="https://github.com/broccoliboy/python-for-android.git"
P4A_COMMIT="c02cf781a0d3d232eb4ffbeaf580cc82cf2bd65f"

echo "=== Preparing LedFx AutoConnect Android build ==="

if [ ! -d "$P4A_DIR/.git" ]; then
    echo "Downloading Python-for-Android..."
    mkdir -p "$(dirname "$P4A_DIR")"
    git clone "$P4A_REPO" "$P4A_DIR"
    git -C "$P4A_DIR" checkout "$P4A_COMMIT"
fi

CURRENT_COMMIT=$(git -C "$P4A_DIR" rev-parse HEAD)

if [ "$CURRENT_COMMIT" != "$P4A_COMMIT" ]; then
    echo "ERROR: Unexpected Python-for-Android revision: $CURRENT_COMMIT"
    echo "Expected: $P4A_COMMIT"
    exit 1
fi

# Patch the upstream, cached bootstrap, and distribution templates.
# Cached distributions may otherwise retain the original manifest.
TEMPLATES=(
    "$P4A_DIR/pythonforandroid/bootstraps/webview/build/templates/AndroidManifest.tmpl.xml"
    ".buildozer/android/platform/build-armeabi-v7a_arm64-v8a/build/bootstrap_builds/webview/templates/AndroidManifest.tmpl.xml"
    ".buildozer/android/platform/build-armeabi-v7a_arm64-v8a/dists/ledfxautoconnect/templates/AndroidManifest.tmpl.xml"
)

for TEMPLATE in "${TEMPLATES[@]}"; do
    if [ -f "$TEMPLATE" ]; then
        python3 scripts/patch_android_manifest.py "$TEMPLATE"
    else
        echo "INFO: Template not generated yet: $TEMPLATE"
    fi
done

echo "PASS: Android build preparation completed"
