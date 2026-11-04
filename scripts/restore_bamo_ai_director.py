#!/usr/bin/env python3
"""Restore app/bamo_ai_director.py from shipped parts (preferred) or known-good raw URL."""
from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "app" / "bamo_ai_director.py"
PARTS = ROOT / "scripts" / "director_parts"
GOOD = "https://raw.githubusercontent.com/farzin0369/Youtube1/7e81232706188da502b839fccd3547bcd8ab5e0e/app/bamo_ai_director.py"


def _from_parts() -> str | None:
    files = sorted(PARTS.glob("part_*.txt"), key=lambda p: int(p.stem.split("_")[1]))
    if not files:
        return None
    text = "".join(p.read_text(encoding="utf-8") for p in files)
    return text if "def direct_scene" in text and len(text) > 20000 else None


def main() -> int:
    text = _from_parts()
    if text is None:
        text = urllib.request.urlopen(GOOD, timeout=60).read().decode("utf-8")
    if "def direct_scene" not in text or len(text) < 20000:
        raise SystemExit("director restore source invalid")
    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("restored", TARGET, "bytes", len(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
