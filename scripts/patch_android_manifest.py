#!/usr/bin/env python3
"""Configure the LedFx Android foreground service manifest template."""

import argparse
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("template", type=Path)
args = parser.parse_args()

if not args.template.is_file():
    raise SystemExit(f"ERROR: Template not found: {args.template}")

text = args.template.read_text()

pattern = (
    r'<service\s+'
    r'android:name="\{\{ args\.package \}\}\.Service'
    r'\{\{ name\|capitalize \}\}"'
    r'\s+android:process=":service_\{\{ name \}\}"'
    r'(?:\s+android:[A-Za-z]+="[^"]*")*'
    r'\s*/>'
)

replacement = (
    '<service android:name="{{ args.package }}.Service{{ name|capitalize }}"'
    '\n                 android:process=":service_{{ name }}"'
    '\n                 android:foregroundServiceType="connectedDevice"'
    '\n                 android:stopWithTask="true" />'
)

updated, count = re.subn(pattern, lambda _: replacement, text)

if count != 1:
    raise SystemExit(
        f"ERROR: Expected exactly one service template, found {count}."
    )

if updated != text:
    args.template.write_text(updated)
    print("PASS: Android service template patched")
else:
    print("PASS: Android service template already patched")

assert replacement in updated
