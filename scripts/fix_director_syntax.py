#!/usr/bin/env python3
"""Repair duplicate else blocks left by repeated vector harden patches."""
from __future__ import annotations

import re
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "bamo_ai_director.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    fixed = re.sub(
        r"(else:\n                    obj\[label\] = list\(default\)\n)(?:                else:\n                    obj\[label\] = list\(default\)\n)+",
        r"\1",
        text,
    )
    if fixed == text:
        # Try exact triple-else block
        broken = (
            "                else:\n"
            "                    obj[label] = list(default)\n"
            "                else:\n"
            "                    obj[label] = list(default)\n"
            "                else:\n"
            "                    obj[label] = list(default)\n"
        )
        single = (
            "                else:\n"
            "                    obj[label] = list(default)\n"
        )
        if broken in text:
            fixed = text.replace(broken, single, 1)
    TARGET.write_text(fixed, encoding="utf-8")
    compile(fixed, str(TARGET), "exec")
    print("director syntax ok", len(fixed), "changed", fixed != text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
