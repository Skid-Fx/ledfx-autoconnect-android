#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

FRONTEND="$PWD/deps/ledfx/frontend"
ASSETS="$PWD/deps/ledfx/ledfx_frontend"

echo "=== Preparing LedFx Android frontend ==="

test -f "$FRONTEND/package.json" || {
    echo "ERROR: Frontend package.json not found"
    exit 1
}

test -f "$FRONTEND/yarn.lock" || {
    echo "ERROR: Frontend yarn.lock not found"
    exit 1
}

test -f "$ASSETS/__init__.py" || {
    echo "ERROR: LedFx frontend Python package not found"
    exit 1
}

echo "PASS: Frontend source and asset directories verified"

# Install NVM only when it is missing.
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"

if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "=== Installing NVM v0.40.3 ==="
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
fi

# NVM must be loaded explicitly in non-interactive build scripts.
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "ERROR: NVM installation failed"
    exit 1
fi

# shellcheck disable=SC1091
source "$NVM_DIR/nvm.sh"

echo "PASS: NVM is available"

# Use a consistent Node.js version for frontend builds.
NODE_VERSION="22"

if ! nvm ls "$NODE_VERSION" --no-colors | grep -q 'v22\.'; then
    echo "=== Installing Node.js $NODE_VERSION ==="
    nvm install "$NODE_VERSION"
fi

nvm use "$NODE_VERSION" >/dev/null

echo "PASS: Node.js $(node --version)"

# Install the pinned Yarn Classic version only when needed.
YARN_VERSION="1.22.22"
CURRENT_YARN="$(yarn --version 2>/dev/null || true)"

if [ "$CURRENT_YARN" != "$YARN_VERSION" ]; then
    echo "=== Installing Yarn $YARN_VERSION ==="
    npm install --global "yarn@$YARN_VERSION"
fi

CURRENT_YARN="$(yarn --version)"

if [ "$CURRENT_YARN" != "$YARN_VERSION" ]; then
    echo "ERROR: Expected Yarn $YARN_VERSION, found $CURRENT_YARN"
    exit 1
fi

echo "PASS: Yarn $CURRENT_YARN"

# Yarn Classic uses .yarnrc, not the Berry .yarnrc.yml configuration.
# Keep the upstream configuration unchanged.
export YARN_IGNORE_PATH=1

echo "PASS: Yarn Classic configuration prepared"

# Stable fingerprints: Android's frontend build changes package.json homepage.
# Ignore that generated change so repeated builds do not reinstall dependencies.
fingerprint() {
    python3 - "$FRONTEND" "$1" <<'PYHASH'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]
digest = hashlib.sha256()

files = ["package.json", "yarn.lock", ".npmrc"]

if mode == "build":
    files += ["tsconfig.json", "config-overrides.js",
              "craco.config.js", "craco.config.ts",
              ".env", ".env.production"]

for name in files:
    path = root / name
    if not path.is_file():
        continue
    data = path.read_bytes()
    if name == "package.json":
        package = json.loads(data)
        package.pop("homepage", None)
        data = json.dumps(package, sort_keys=True).encode()
    digest.update(name.encode())
    digest.update(data)

if mode == "build":
    for dirname in ("src", "public"):
        directory = root / dirname
        if directory.is_dir():
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    digest.update(str(path.relative_to(root)).encode())
                    digest.update(path.read_bytes())

print(digest.hexdigest())
PYHASH
}

echo "=== Checking frontend dependencies ==="
cd "$FRONTEND"

DEPS_STAMP="node_modules/.skidfx-dependencies.sha256"
DEPS_HASH="$(
    {
        fingerprint dependencies
        node --version
        yarn --version
    } | sha256sum | cut -d ' ' -f 1
)"

if [ -x node_modules/.bin/craco ] &&
   [ -x node_modules/.bin/tsc ] &&
   [ "$(cat "$DEPS_STAMP" 2>/dev/null || true)" = "$DEPS_HASH" ]; then
    echo "PASS: Frontend dependencies already prepared"
else
    echo "=== Installing frontend dependencies ==="
    yarn install --frozen-lockfile --non-interactive
    printf '%s\n' "$DEPS_HASH" > "$DEPS_STAMP"
    echo "PASS: Frontend dependencies installed"
fi

echo "=== Checking frontend TypeScript ==="
yarn test:types
echo "PASS: Frontend TypeScript validation completed"

if [ "${1:-}" = "--prepare-only" ]; then
    echo "PASS: Frontend environment prepared"
    exit 0
fi

if [ "$#" -ne 0 ]; then
    echo "Usage: $0 [--prepare-only]"
    exit 2
fi

SOURCE_HASH="$(
    {
        fingerprint build
        node --version
        yarn --version
    } | sha256sum | cut -d ' ' -f 1
)"

BUILD_STAMP="$FRONTEND/build/.skidfx-build.sha256"
ASSET_STAMP="$ASSETS/.skidfx-build.sha256"

if [ ! -f "$FRONTEND/build/index.html" ] ||
   [ "$(cat "$BUILD_STAMP" 2>/dev/null || true)" != "$SOURCE_HASH" ]; then
    echo "=== Compiling Android React frontend ==="
    yarn buildandroid
    test -f "$FRONTEND/build/index.html" || {
        echo "ERROR: Frontend compilation did not produce index.html"
        exit 1
    }
    printf '%s\n' "$SOURCE_HASH" > "$BUILD_STAMP"
else
    echo "PASS: Compiled frontend is current"
fi

# Synchronize generated files while preserving Python files and configuration.
sync_frontend() {
    python3 - "$1" "$2" <<'PYSYNC'
import shutil
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])

if not (source / "index.html").is_file():
    raise SystemExit("ERROR: Source frontend is missing index.html")

if not target.is_dir() or not (target / "index.html").is_file():
    raise SystemExit("ERROR: Destination is not an existing LedFx frontend directory")

preserved = {"__init__.py", "frontend_config.json"}

for item in source.iterdir():
    if item.name in preserved or item.name.startswith(".skidfx-"):
        continue

    destination = target / item.name

    if item.is_dir():
        if destination.is_dir():
            shutil.rmtree(destination)
        elif destination.exists():
            destination.unlink()
        shutil.copytree(item, destination)
    elif item.is_file():
        if destination.is_dir():
            shutil.rmtree(destination)
        shutil.copy2(item, destination)

print(f"PASS: Synchronized {target}")
PYSYNC
}

if [ "$(cat "$ASSET_STAMP" 2>/dev/null || true)" != "$SOURCE_HASH" ] ||
   ! cmp -s "$FRONTEND/build/index.html" "$ASSETS/index.html"; then
    echo "=== Updating LedFx frontend package ==="
    sync_frontend "$FRONTEND/build" "$ASSETS"
    printf '%s\n' "$SOURCE_HASH" > "$ASSET_STAMP"
else
    echo "PASS: LedFx frontend package is current"
fi

# Existing p4a distribution bundles may contain an older frontend.
# Update only those package directories; do not delete build caches.
DIST_ROOT="$(cd "$FRONTEND/../../.." && pwd)/.buildozer/android/platform/build-armeabi-v7a_arm64-v8a/dists/ledfxautoconnect"

for ARCH in armeabi-v7a arm64-v8a; do
    CACHE="$DIST_ROOT/_python_bundle__$ARCH/_python_bundle/site-packages/ledfx_frontend"

    if [ -f "$CACHE/index.html" ]; then
        if [ ! -f "$CACHE/.skidfx-build.sha256" ] ||
           [ "$(cat "$CACHE/.skidfx-build.sha256" 2>/dev/null || true)" != "$SOURCE_HASH" ] ||
           ! cmp -s "$ASSETS/index.html" "$CACHE/index.html"; then
            sync_frontend "$ASSETS" "$CACHE"
            printf '%s\n' "$SOURCE_HASH" > "$CACHE/.skidfx-build.sha256"
        else
            echo "PASS: $ARCH frontend cache is current"
        fi
    else
        echo "INFO: $ARCH frontend cache not yet generated"
    fi
done

echo "PASS: Android frontend preparation completed"
