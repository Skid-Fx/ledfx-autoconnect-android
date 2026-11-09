#!/usr/bin/env python3
"""Configure the LedFx AutoConnect Android foreground service template."""

import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("template", type=Path)
args = parser.parse_args()

template = args.template

if not template.is_file():
    raise SystemExit(f"ERROR: Template not found: {template}")

text = template.read_text()

old = '''<service android:name="{{ args.package }}.Service{{ name|capitalize }}"
                 android:process=":service_{{ name }}" />'''

new = '''<service android:name="{{ args.package }}.Service{{ name|capitalize }}"
                 android:process=":service_{{ name }}"
                 android:foregroundServiceType="mediaPlayback"
                 android:stopWithTask="true" />'''

if new in text:
    print("PASS: Android service template already patched")
elif text.count(old) == 1:
    template.write_text(text.replace(old, new, 1))
    print("PASS: Android service template patched")
else:
    raise SystemExit("ERROR: Unexpected template format. No changes made.")
