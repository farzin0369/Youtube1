#!/usr/bin/env python3
"""CPU smoke test for the production BAMO 3D renderer, audio mux and Persian captions."""
from pathlib import Path
import subprocess

from app.bamo_production_renderer import render_bamo_shorts
from app.media_qa import validate_render_package

out = Path("output/bamo-3d-smoke")
out.mkdir(parents=True, exist_ok=True)
audio = out / "voice-test.mp3"
captions = out / "captions.srt"
subprocess.run([
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=18",
    "-codec:a", "libmp3lame", "-b:a", "128k", str(audio),
], check=True)
# Eight short, valid SRT cues: two synchronized caption beats per visual scene.
captions.write_text(
    "1\n00:00:00,300 --> 00:00:02,000\nیک تصمیم\n\n"
    "2\n00:00:02,000 --> 00:00:03,900\nمهم\n\n"
    "3\n00:00:04,700 --> 00:00:06,400\nپیوندهای\n\n"
    "4\n00:00:06,400 --> 00:00:08,200\nشیمیایی\n\n"
    "5\n00:00:09,200 --> 00:00:11,000\nهندسه\n\n"
    "6\n00:00:11,000 --> 00:00:13,000\nدر حرکت\n\n"
    "7\n00:00:13,700 --> 00:00:15,500\nنیرو\n\n"
    "8\n00:00:15,500 --> 00:00:17,700\nو حرکت\n",
    encoding="utf-8",
)
scenes = [
    {"spoken_text": "یک تصمیم مهم", "visual_query": "two diverging paths", "on_screen_text": "یک تصمیم مهم"},
    {"spoken_text": "پیوند مولکولی", "visual_query": "chemistry molecule bonds", "on_screen_text": "پیوندهای شیمیایی"},
    {"spoken_text": "هندسه و منحنی", "visual_query": "3D geometry coordinate grid and curve", "on_screen_text": "هندسه در حرکت"},
    {"spoken_text": "قانون حرکت و نیرو", "visual_query": "physics wavefront and force vectors", "on_screen_text": "نیرو و حرکت"},
]
timings = [
    {"start_seconds": 0.0, "end_seconds": 4.3},
    {"start_seconds": 4.5, "end_seconds": 8.8},
    {"start_seconds": 9.0, "end_seconds": 13.3},
    {"start_seconds": 13.5, "end_seconds": 18.0},
]
render = render_bamo_shorts(
    title="BAMO | آزمون موتور سه‌بعدی",
    thumbnail_text="آزمون موتور سه‌بعدی",
    audio_path=audio, captions_path=captions, out_dir=out,
    run_id="cpu-smoke", scenes=scenes, scene_timings=timings,
    hook_overlay=scenes[0]["on_screen_text"],
)
qa = validate_render_package(render, audio, video_format="shorts")
print({"render": render, "qa": qa}, flush=True)
# This is a renderer smoke test, not a publish-approval test. The current
# procedural renderer has no independent pixel-to-narration verifier, so the
# semantic and publish gates MUST remain closed while technical output is tested.
technical_checks = (
    "video_path", "thumbnail_path", "captions_path", "video_dimensions",
    "thumbnail_dimensions", "duration_seconds", "audio_duration_seconds",
    "burned_captions_path", "caption_animation", "persian_text_shaping",
    "audio_path", "caption_cues",
)
missing = [key for key in technical_checks if key not in qa.get("checks", {})]
failed = [
    key for key in ("video_path", "thumbnail_path", "captions_path",
                    "burned_captions_path", "caption_animation",
                    "persian_text_shaping", "audio_path")
    if not qa.get("checks", {}).get(key, {}).get("ok", False)
]
expected_blockers = {
    "shorts_scene_visual_queries_not_verified",
    "shorts_visual_source_not_approved_portrait_stock",
}
unexpected = [error for error in qa.get("errors", []) if error not in expected_blockers]
if missing or failed or unexpected:
    raise SystemExit(
        "CPU renderer technical smoke failed; missing=%s failed=%s unexpected=%s"
        % (missing, failed, unexpected)
    )
if qa.get("checks", {}).get("semantic_alignment", {}).get("verified") is not False:
    raise SystemExit("semantic publish gate must remain closed without independent verification")
print("CPU_RENDER_SMOKE=PASS; SEMANTIC_ALIGNMENT=UNVERIFIED; PUBLISH_GATE=BLOCKED", flush=True)
