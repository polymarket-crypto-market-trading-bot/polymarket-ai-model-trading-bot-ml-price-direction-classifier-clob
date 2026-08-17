#!/usr/bin/env python3
"""Verify README image references resolve to existing files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_IMG_PATTERN = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


def main() -> int:
    if not README.exists():
        print(f"ERROR: {README} not found")
        return 1

    content = README.read_text(encoding="utf-8")
    refs = IMAGE_PATTERN.findall(content) + HTML_IMG_PATTERN.findall(content)
    if not refs:
        print("WARNING: No image references found in README.md")
        return 0

    errors = []
    for ref in refs:
        ref = ref.strip()
        if ref.startswith("http://") or ref.startswith("https://"):
            print(f"  OK (remote) {ref}")
            continue
        path = ROOT / ref
        if path.is_file():
            size_kb = path.stat().st_size / 1024
            print(f"  OK {ref} ({size_kb:.0f} KB)")
        else:
            errors.append(ref)
            print(f"  MISSING {ref}")

    if errors:
        print(f"\nFAILED: {len(errors)} broken image reference(s)")
        return 1

    print(f"\nPASSED: All {len(refs)} README image(s) verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
