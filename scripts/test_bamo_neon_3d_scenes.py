#!/usr/bin/env python3
"""Render two different BAMO neon/science motifs through the real Blender CPU path."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.bamo_motion_engine import render_project

out = Path("output/bamo-neon-3d-validation")
out.mkdir(parents=True, exist_ok=True)
video = out / "bamo-neon-ellipse-and-wave.mp4"
project = {
    "format": "short",
    "fps": 24,
    "scenes": [
        {
            "duration": 2.5,
            "text": "هندسهٔ زنده؛ ذرات روی مدار",
            "narration": "ذرات نورانی روی یک مدار بیضوی حرکت می‌کنند.",
            "visual_prompt": "neon ellipse with orbiting particles and geometric web",
        },
        {
            "duration": 2.5,
            "text": "تداخل؛ برهم‌نهی دو موج",
            "narration": "دو موج با هم ترکیب می‌شوند و الگوی تداخل می‌سازند.",
            "visual_prompt": "two wave sources and constructive destructive interference",
        },
    ],
}
render_project(project, video)
probe = subprocess.run(
    ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
     "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_read_frames",
     "-show_entries", "format=duration,size", "-of", "json", str(video)],
    check=True, capture_output=True, text=True, timeout=60,
)
data = json.loads(probe.stdout)
stream = data["streams"][0]
evidence = {
    "renderer": "BAMO Blender Cycles CPU",
    "video": str(video),
    "bytes": video.stat().st_size,
    "width": stream["width"],
    "height": stream["height"],
    "frame_rate": stream["r_frame_rate"],
    "frames": int(stream["nb_read_frames"]),
    "duration": float(data["format"]["duration"]),
    "scenes": ["neon_ellipse_mesh", "wave_interference"],
    "samples": 2,
    "resolution_percentage": 25,
}
(out / "render-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
for stamp, name in (("1.0", "ellipse-review.png"), ("3.5", "wave-review.png")):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", stamp,
         "-i", str(video), "-frames:v", "1", str(out / name)],
        check=True, timeout=60,
    )
print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)
if (stream["width"], stream["height"]) != (720, 1280):
    raise SystemExit("Expected portrait 720x1280 output")
if stream["r_frame_rate"] != "24/1" or int(stream["nb_read_frames"]) != 120:
    raise SystemExit("Expected exactly 120 frames at 24 FPS")
if video.stat().st_size < 100_000:
    raise SystemExit("Rendered MP4 is unexpectedly small")
