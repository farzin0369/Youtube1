#!/usr/bin/env python3
"""Render a distinct science short with the approved BAMO CPU 3D motion-graphics engine."""
from __future__ import annotations

import json
from pathlib import Path

from app.bamo_production_renderer import render_bamo_shorts
from app.media_qa import validate_render_package
from app.spiritual_tts import synthesize_with_captions

TITLE = "چرا آسمان شب با وجود میلیاردها ستاره تاریک است؟"
OUT = Path("output/bamo-olbers-paradox")
OUT.mkdir(parents=True, exist_ok=True)
AUDIO = OUT / "voice-fa.mp3"
CAPTIONS = OUT / "captions.srt"

# Four distinct, narration-matched scientific scenes. No generic/reused motivation visuals.
SCENES = [
    {
        "spoken_text": "یک سؤال عجیب: اگر میلیاردها ستاره در جهان می‌درخشند، چرا آسمان شب کاملاً روشن نیست؟",
        "visual_query": "Earth night horizon under dark starfield, countless stars, cinematic scientific 3D space visualization",
        "on_screen_text": "چرا شب تاریک است؟",
        "mood": "curiosity",
    },
    {
        "spoken_text": "این معما را پارادوکس اولبرس می‌نامند؛ مسئله‌ای که اخترشناسان قرن‌ها درباره‌اش فکر می‌کردند.",
        "visual_query": "3D astronomical star distribution shells around observer, expanding cosmic distance visualization",
        "on_screen_text": "پارادوکس اولبرس",
        "mood": "discovery",
    },
    {
        "spoken_text": "جهان عمر محدودی دارد؛ پس نور همه ستاره‌ها فرصت نداشته به زمین برسد، و خود فضا هم در حال انبساط است.",
        "visual_query": "Big Bang expanding spacetime grid with traveling light rays and redshift, accurate educational 3D animation",
        "on_screen_text": "عمر محدود + انبساط جهان",
        "mood": "explanation",
    },
    {
        "spoken_text": "پس تاریکی آسمان نشانه خالی بودن جهان نیست؛ پنجره‌ای است به تاریخ، فاصله‌ها و انبساط کیهان.",
        "visual_query": "cinematic camera pullback from glowing Earth into deep expanding universe, galaxies and cosmic web",
        "on_screen_text": "تاریکی، ردّ تاریخ کیهان",
        "mood": "wonder",
    },
]
# The semantic AI director now authors a fresh executable scene graph per
# narration segment; do not gate the new engine through the legacy finite motif map.

SCRIPT = " ".join(scene["spoken_text"] for scene in SCENES)
tts = synthesize_with_captions(SCRIPT, AUDIO, CAPTIONS, scenes=SCENES)
if not tts.get("ok") or tts.get("provider") not in {"edge-tts", "elevenlabs"}:
    raise SystemExit("Persian narration synthesis failed; refusing silent or synthetic-tone fallback.")
if not tts.get("voice") or not tts.get("narrator_locked"):
    raise SystemExit("Persian narrator identity was not verified.")
if not AUDIO.exists() or AUDIO.stat().st_size < 10_000:
    raise SystemExit("Persian narration audio is missing or unexpectedly small.")

render = render_bamo_shorts(
    title=TITLE,
    thumbnail_text="راز تاریکی آسمان",
    audio_path=AUDIO,
    captions_path=CAPTIONS,
    out_dir=OUT,
    run_id="science-olbers-paradox",
    scenes=SCENES,
    scene_timings=tts.get("scene_timings") or [],
    hook_overlay=SCENES[0]["on_screen_text"],
)
qa = validate_render_package(render, AUDIO, video_format="shorts", tts_meta=tts)
evidence = {
    "topic": "Olbers paradox / why the night sky is dark",
    "title": TITLE,
    "tts_provider": tts.get("provider"),
    "tts_voice": tts.get("voice"),
    "narration_seconds": tts.get("duration_seconds"),
    "caption_count": tts.get("caption_count"),
    "visual_plans": render.get("scene_visual_plans"),
    "qa": qa,
    "publishable": bool(qa.get("ok")),
}
(OUT / "production-evidence.json").write_text(
    json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)
# Technical render is successful even when the independent visual-approval gate
# correctly blocks public release. Never convert that gate into a false approval.
if not render.get("video_path") or not Path(render["video_path"]).is_file():
    raise SystemExit("The renderer did not produce an MP4.")
if not qa.get("ok"):
    print("RENDERED_PREVIEW_ONLY: production visual QA did not approve public publishing.", flush=True)
