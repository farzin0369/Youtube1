#!/usr/bin/env python3
"""Real Persian-voice CPU smoke test; synthetic tones are deliberately forbidden."""
from pathlib import Path

from app.bamo_production_renderer import render_bamo_shorts
from app.media_qa import validate_render_package
from app.spiritual_tts import synthesize_with_captions

out = Path("output/bamo-3d-smoke")
out.mkdir(parents=True, exist_ok=True)
audio = out / "voice-test.mp3"
captions = out / "captions.srt"
scenes = [
    {
        "spoken_text": "تا حالا دیدی یک انتخاب کوچک چطور مسیر زندگی را عوض می‌کند؟",
        "visual_query": "two diverging cinematic roads",
        "on_screen_text": "یک انتخاب سرنوشت‌ساز",
        "mood": "hook",
    },
    {
        "spoken_text": "مغز با تکرار، مسیرهای عصبی را تقویت می‌کند و انجام کار را آسان‌تر می‌سازد.",
        "visual_query": "glowing neural pathways brain synapses",
        "on_screen_text": "مغز با تکرار می‌سازد",
        "mood": "calm",
    },
    {
        "spoken_text": "امروز یک قدم کوچک بردار و ده دقیقه بدون حواس‌پرتی برای هدفت وقت بگذار.",
        "visual_query": "ascending golden steps cinematic",
        "on_screen_text": "فقط ده دقیقه",
        "mood": "reassuring",
    },
    {
        "spoken_text": "همین شروع ساده می‌تواند آغاز تغییری باشد که فردا نتیجه‌اش را می‌بینی.",
        "visual_query": "radiant sunrise horizon cinematic",
        "on_screen_text": "تغییر از همین‌جا",
        "mood": "motivational",
    },
]
script = " ".join(scene["spoken_text"] for scene in scenes)
tts = synthesize_with_captions(script, audio, captions, scenes=scenes)
if not tts.get("ok") or tts.get("provider") not in {"edge-tts", "elevenlabs"}:
    raise SystemExit("Real speech synthesis did not complete; no tone fallback is permitted.")
if not tts.get("voice") or not tts.get("narrator_locked"):
    raise SystemExit("Persian narrator identity was not verified.")
if audio.stat().st_size < 10_000:
    raise SystemExit("Narration audio is unexpectedly small.")

render = render_bamo_shorts(
    title="BAMO | آزمون واقعی صدای فارسی و موشن سه‌بعدی",
    thumbnail_text="آزمون واقعی موتور",
    audio_path=audio,
    captions_path=captions,
    out_dir=out,
    run_id="cpu-smoke-real-voice",
    scenes=scenes,
    scene_timings=tts.get("scene_timings") or [],
    hook_overlay=scenes[0]["on_screen_text"],
)
qa = validate_render_package(render, audio, video_format="shorts", tts_meta=tts)
evidence = {
    "tts_provider": tts.get("provider"),
    "tts_voice": tts.get("voice"),
    "narration_seconds": tts.get("duration_seconds"),
    "caption_count": tts.get("caption_count"),
    "visual_plans": render.get("scene_visual_plans"),
    "qa": qa,
}
(out / "smoke-evidence.json").write_text(
    __import__("json").dumps(evidence, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
evidence["publishable"] = bool(qa.get("ok"))
print(evidence, flush=True)
errors = list(qa.get("errors") or [])
expected_preview_blocks = {
    "shorts_visuals_not_production_approved",
    "shorts_scene_visual_queries_not_verified",
    "shorts_visual_source_not_approved_portrait_stock",
}
if not expected_preview_blocks.issubset(set(errors)):
    raise SystemExit("BAMO smoke test did not preserve all production safety gates: " + ", ".join(errors))
technical_errors = [error for error in errors if error not in expected_preview_blocks]
if technical_errors:
    raise SystemExit("BAMO smoke test failed unexpectedly: " + ", ".join(technical_errors))
