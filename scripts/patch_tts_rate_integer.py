#!/usr/bin/env python3
"""Edge-TTS requires integer rate/pitch like +4% not +4.4%."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_tts.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    old = 'return f"{rate:+.1f}%", f"{pitch:+.1f}Hz"'
    new = 'return f"{int(round(rate)):+d}%", f"{int(round(pitch)):+d}Hz"'
    if new in text:
        print("PATCH_NOOP")
        return 0
    if old not in text:
        raise SystemExit("PATCH_FAIL: rate format line not found")
    text = text.replace(old, new, 1)
    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED integer TTS rate/pitch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
