#!/usr/bin/env python3
"""Verify the generated LedFx Android manifest."""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if len(sys.argv) != 2:
    raise SystemExit("Usage: verify_android_manifest.py MANIFEST")

path = Path(sys.argv[1])

if not path.is_file():
    raise SystemExit(f"ERROR: Manifest not found: {path}")

android = "{http://schemas.android.com/apk/res/android}"

root = ET.parse(path).getroot()

package = "com.skidfx.ledfxautoconnect"
service_name = package + ".ServiceLedfx"

services = [
    service
    for service in root.iter("service")
    if service.get(android + "name") == service_name
]

if len(services) != 1:
    raise SystemExit(
        f"ERROR: Expected one ServiceLedfx declaration; found {len(services)}"
    )

service = services[0]

actual_type = service.get(android + "foregroundServiceType")

if actual_type != "connectedDevice":
    raise SystemExit(
        f"ERROR: Foreground service type is {actual_type!r}; "
        "expected 'connectedDevice'"
    )

permissions = {
    item.get(android + "name")
    for item in root.findall("uses-permission")
}

required = {
    "android.permission.FOREGROUND_SERVICE",
    "android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE",
    "android.permission.CHANGE_NETWORK_STATE",
}

missing = required - permissions

if missing:
    raise SystemExit(
        "ERROR: Missing permissions: " + ", ".join(sorted(missing))
    )

print("PASS: ServiceLedfx foreground service type is connectedDevice")
print("PASS: Required foreground service permissions present")
print("PASS: Generated Android manifest verified")
