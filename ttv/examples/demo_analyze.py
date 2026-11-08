#!/usr/bin/env python3
"""Demo: text → analysis → scene plan (no render yet)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ttv.core import SceneGenerator, TextAnalyzer

SAMPLE_FA = """شفق قطبی چیست؟
خورشید ذره‌های باردار را به فضا می‌فرستد.
میدان مغناطیسی زمین آن‌ها را به سوی قطب‌ها می‌کشاند.
با برخورد به جو، گازها نورانی می‌شوند و آسمان رنگ می‌گیرد.
رنگ‌ها به ارتفاع و نوع گاز بستگی دارد.
"""

SAMPLE_EN = """Why is the sky blue?
Sunlight looks white, but air molecules scatter blue wavelengths more strongly.
At sunset the path through the atmosphere is longer, so red and orange dominate.
"""


def main() -> int:
    text = SAMPLE_FA if (len(sys.argv) < 2 or sys.argv[1] == "fa") else SAMPLE_EN
    analysis = TextAnalyzer().analyze(text)
    plan = SceneGenerator(aspect="portrait", fps=30).from_analysis(analysis)

    print("=== ANALYSIS ===")
    print(json.dumps({
        "language": analysis.language,
        "tone": analysis.tone,
        "keywords": analysis.keywords,
        "topics": analysis.topics,
        "visual_queries": analysis.visual_queries,
        "music_mood": analysis.music_mood,
        "estimated_speech_sec": analysis.estimated_total_speech_sec,
    }, ensure_ascii=False, indent=2))

    print("\n=== SCENE PLAN ===")
    print(json.dumps({
        "title": plan.title,
        "total_duration_sec": plan.total_duration_sec,
        "scene_count": len(plan.scenes),
        "scenes": [
            {
                "id": s.id,
                "start": s.start_sec,
                "dur": s.duration_sec,
                "caption": s.caption,
                "visual": s.visual_query,
                "motion": s.motion,
                "transition": s.transition_in,
            }
            for s in plan.scenes
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
