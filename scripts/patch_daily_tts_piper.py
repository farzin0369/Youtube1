#!/usr/bin/env python3
from pathlib import Path
TARGET = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "daily_run.yml"
text = TARGET.read_text(encoding="utf-8")
old = "TTS_PROVIDER: ${{ vars.TTS_PROVIDER || 'edge-tts' }}"
new = "TTS_PROVIDER: ${{ vars.TTS_PROVIDER || 'piper' }}"
if new in text:
    print("NOOP")
elif old not in text:
    raise SystemExit("FAIL")
else:
    TARGET.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("APPLIED")
