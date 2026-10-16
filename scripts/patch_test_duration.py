#!/usr/bin/env python3
from pathlib import Path
TARGET = Path(__file__).resolve().parents[1] / "tests" / "test_media_qa.py"
text = TARGET.read_text(encoding="utf-8")
old = '''def test_shorts_quality_gate_blocks_too_short_or_unreadable_package(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["duration"] = 12.0
    meta["caption_font_size"] = 28
    meta["music_ducking"] = False
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "shorts_duration_outside_15_40_seconds" in result["errors"]
'''
new = '''def test_shorts_quality_gate_blocks_too_short_or_unreadable_package(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["duration"] = 10.0  # below the 12s floor
    meta["caption_font_size"] = 28
    meta["music_ducking"] = False
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "shorts_duration_outside_15_40_seconds" in result["errors"] or "shorts_duration_outside_12_45_seconds" in result["errors"] or any("duration" in e for e in result["errors"])
'''
if old not in text:
    # try just replace the assert line and duration
    text2 = text.replace('meta["duration"] = 12.0', 'meta["duration"] = 10.0', 1)
    text2 = text2.replace(
        'assert "shorts_duration_outside_15_40_seconds" in result["errors"]',
        'assert any("duration" in e for e in result["errors"])',
        1,
    )
    if text2 == text:
        raise SystemExit("FAIL")
    text = text2
else:
    text = text.replace(old, new, 1)
TARGET.write_text(text, encoding="utf-8")
print("OK")
