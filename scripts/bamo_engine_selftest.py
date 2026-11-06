#!/usr/bin/env python3
"""Quick self-test for BAMO Smart Director + procedural audio (no browser required)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    print("BAMO engine self-test")
    from app.bamo_director import detect_mood, guess_motif, enrich_project
    from app.bamo_procedural_audio import generate_ambient

    samples = [
        "گاهی فقط باید صبر کنی و در آرامش بمانی",
        "این یک پیروزی حماسی و قدرت بزرگ است",
        "نور امید و طلوع دوباره می‌آید",
        "رازی تاریک در سایه‌ها پنهان است",
    ]
    for text in samples:
        mood = detect_mood(text)
        motif = guess_motif(text)
        print(f"  [{mood['id']:12}] motif={motif:8} | {text[:40]}")

    project = {
        "format": "short",
        "fps": 24,
        "scenes": [
            {"duration": 3, "text": "صبر", "narration": samples[0], "visual_prompt": "آرامش"},
            {"duration": 3, "text": "امید", "narration": samples[2], "visual_prompt": "نور طلوع"},
        ],
    }
    project = enrich_project(project)
    assert project["scenes"][0].get("palette")
    assert project["scenes"][0].get("motif")
    print("enrich_project: OK")

    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "test.wav"
        generate_ambient(wav, 2.0, mood=project.get("globalMood") or "spiritual")
        assert wav.is_file() and wav.stat().st_size > 1000
        print(f"procedural audio: OK ({wav.stat().st_size} bytes)")

    print("ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
