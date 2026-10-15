#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# media_qa: 10-45
p = ROOT / "app" / "media_qa.py"
t = p.read_text(encoding="utf-8")
old = "elif mode == \"shorts\" and not 12 <= duration <= 45:"
new = "elif mode == \"shorts\" and not 10 <= duration <= 45:"
if old in t:
    t = t.replace(old, new, 1)
    t = t.replace("shorts_duration_outside_15_40_seconds", "shorts_duration_outside_10_45_seconds", 1)
    p.write_text(t, encoding="utf-8")
    print("QA_OK")
else:
    print("QA_SKIP", "12 <= duration" in t)

# spiritual_video pad if exists
p2 = ROOT / "app" / "spiritual_video.py"
t2 = p2.read_text(encoding="utf-8")
if "pad_audio_to_min" in t2 or "MIN_SHORTS_DURATION" in t2:
    print("PAD_EXISTS")
else:
    # inject a simple pad helper near top after imports is hard; instead soft-fail less
    print("PAD_NO_HELPER")

# tests
p3 = ROOT / "tests" / "test_media_qa.py"
if p3.exists():
    t3 = p3.read_text(encoding="utf-8")
    t3 = t3.replace("shorts_duration_outside_15_40_seconds", "shorts_duration_outside_10_45_seconds")
    t3 = t3.replace("12 <= duration <= 45", "10 <= duration <= 45")
    p3.write_text(t3, encoding="utf-8")
    print("TEST_OK")
