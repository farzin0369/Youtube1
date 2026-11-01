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
    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=12",
    "-codec:a", "libmp3lame", "-b:a", "128k", str(audio),
], check=True)
captions.write_text(
    "1\n00:00:00,200 --> 00:00:01,200\nیک تصمیم مهم\n\n"
    "2\n00:00:03,200 --> 00:00:04,200\nدفتر و نوشتن\n\n"
    "3\n00:00:06,200 --> 00:00:07,200\nطلوع و امید\n\n"
    "4\n00:00:09,200 --> 00:00:10,200\nاتم و الکترون\n\n"
    "5\n00:00:10,300 --> 00:00:11,500\nحرکت سه‌بعدی\n",
    encoding="utf-8",
)
scenes = [
    {"spoken_text": "یک تصمیم مهم", "visual_query": "two diverging paths", "on_screen_text": "یک تصمیم مهم"},
    {"spoken_text": "دفتر و نوشتن", "visual_query": "notebook journal", "on_screen_text": "از نو شروع کن"},
    {"spoken_text": "طلوع و امید", "visual_query": "sunrise light", "on_screen_text": "نور امید"},
    {"spoken_text": "اتم و الکترون", "visual_query": "atomic orbit", "on_screen_text": "جهان اتم"},
]
timings = [{"start_seconds": 0.0, "end_seconds": 2.8},
           {"start_seconds": 3.0, "end_seconds": 5.8},
           {"start_seconds": 6.0, "end_seconds": 8.8},
           {"start_seconds": 9.0, "end_seconds": 12.0}]
render = render_bamo_shorts(
    title="BAMO | آزمون موتور سه‌بعدی",
    thumbnail_text="آزمون موتور سه‌بعدی",
    audio_path=audio, captions_path=captions, out_dir=out,
    run_id="cpu-smoke", scenes=scenes, scene_timings=timings,
    hook_overlay=scenes[0]["on_screen_text"],
)
qa = validate_render_package(render, audio, video_format="shorts")
print({"render": render, "qa": qa}, flush=True)
if not qa.get("ok"):
    raise SystemExit("3D renderer media QA failed: " + ", ".join(qa.get("errors") or []))
