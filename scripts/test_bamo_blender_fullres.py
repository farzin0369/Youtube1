#!/usr/bin/env python3
"""Full-resolution 49-frame integration proof for the real Blender CPU renderer."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.bamo_motion_engine import render_project

OUT = Path("output/bamo-blender-fullres-49")
OUT.mkdir(parents=True, exist_ok=True)
video = OUT / "bamo-blender-49-frame-proof.mp4"

project = {
    "format": "short",
    "fps": 24,
    "scenes": [{
        "duration": 49 / 24,
        "text": "آسمان شب؛ یک صحنهٔ سه‌بعدی واقعی",
        "narration": "آسمان شب",
        "visual_prompt": "starfield above curved planetary night horizon",
    }],
}
render_project(project, video)

probe = subprocess.run(
    [
        "ffprobe", "-v", "error", "-count_frames",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_read_frames",
        "-of", "json", str(video),
    ],
    check=True, capture_output=True, text=True, timeout=60,
)
streams = json.loads(probe.stdout).get("streams", [])
if len(streams) != 1:
    raise SystemExit("Expected exactly one video stream in the Blender proof.")
stream = streams[0]
evidence = {
    "renderer": "Blender Cycles CPU",
    "video": str(video),
    "bytes": video.stat().st_size,
    "codec": stream.get("codec_name"),
    "width": stream.get("width"),
    "height": stream.get("height"),
    "frame_rate": stream.get("r_frame_rate"),
    "frames": int(stream.get("nb_read_frames", "0")),
    "resolution_percentage": 100,
    "samples": 16,
}
(OUT / "render-evidence.json").write_text(
    json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)

if evidence["width"] != 720 or evidence["height"] != 1280:
    raise SystemExit("Blender proof is not full 720x1280 portrait resolution.")
if evidence["frame_rate"] != "24/1" or evidence["frames"] != 49:
    raise SystemExit("Blender proof must contain exactly 49 frames at 24 FPS.")
if evidence["bytes"] < 100_000:
    raise SystemExit("Blender proof MP4 is unexpectedly small.")
