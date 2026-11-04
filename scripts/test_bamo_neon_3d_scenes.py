#!/usr/bin/env python3
"""Render two different BAMO neon/science motifs through the real Blender CPU path."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from app.bamo_motion_engine import FORMATS, render_project

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
engine = os.getenv("BAMO_BLENDER_ENGINE", "BLENDER_WORKBENCH").upper()
evidence = {
    "renderer": f"BAMO Blender {engine} CPU",
    "video": str(video),
    "bytes": video.stat().st_size,
    "codec": stream.get("codec_name"),
    "width": stream["width"],
    "height": stream["height"],
    "frame_rate": stream["r_frame_rate"],
    "frames": int(stream["nb_read_frames"]),
    "duration": float(data["format"]["duration"]),
    "scenes": ["neon_ellipse_mesh", "wave_interference"],
    "samples": int(os.getenv("BAMO_BLENDER_SAMPLES", "16")),
    "resolution_percentage": int(os.getenv("BAMO_BLENDER_RESOLUTION_PERCENTAGE", "100")),
}
(out / "render-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
for stamp, name in (("1.0", "ellipse-review.png"), ("3.5", "wave-review.png")):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", stamp,
         "-i", str(video), "-frames:v", "1", str(out / name)],
        check=True, timeout=60,
    )
print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)
expected_width, expected_height = FORMATS["short"]
if (stream["width"], stream["height"]) != (expected_width, expected_height):
    raise SystemExit(f"Expected portrait {expected_width}x{expected_height} output")
if stream.get("codec_name") != "h264":
    raise SystemExit(f"Expected H.264 video, got {stream.get('codec_name')}")
if stream["r_frame_rate"] != "24/1" or int(stream["nb_read_frames"]) != 120:
    raise SystemExit("Expected exactly 120 frames at 24 FPS")
if video.stat().st_size < 100_000:
    raise SystemExit("Rendered MP4 is unexpectedly small")
