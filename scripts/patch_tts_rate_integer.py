#!/usr/bin/env python3
from pathlib import Path
import re
TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_tts.py"
text = TARGET.read_text(encoding="utf-8")
new_line = 'return f"{int(round(rate)):+d}%", f"{int(round(pitch)):+d}Hz"'
if new_line in text:
    print("PATCH_NOOP")
    raise SystemExit(0)
text2, n = re.subn(
    r'return f"\{rate:\+\.1f\}%", f"\{pitch:\+\.1f\}Hz"',
    new_line,
    text,
    count=1,
)
if n != 1:
    old = 'return f"{rate:+.1f}%", f"{pitch:+.1f}Hz"'
    if old not in text:
        raise SystemExit(f"PATCH_FAIL n={n}")
    text2 = text.replace(old, new_line, 1)
compile(text2, str(TARGET), "exec")
TARGET.write_text(text2, encoding="utf-8")
print("PATCH_APPLIED")
