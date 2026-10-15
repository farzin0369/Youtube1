#!/usr/bin/env python3
"""Render one cinematic spiritual short on a CUDA GPU (Colab T4+).

Usage on Colab:
  !python scripts/colab_render_short.py

Produces:
  output/colab_short/video_raw.mp4   — silent AI film
  output/colab_short/scene_plan.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Sensible T4 defaults
os.environ.setdefault("LOCAL_VIDEO_MODEL", "THUDM/CogVideoX-2b")
os.environ.setdefault("VIDEO_CLIPS_SHORT", "4")
os.environ.setdefault("VIDEO_DURATION_HINT_SECONDS", "16")


def main() -> int:
    from app.local_video_engine import generate_film
    from app.visual_prompts import cinematic_prompts_for_scenes

    # Default demo: same spirit as user reference (one step / inner light)
    topic = os.getenv("SHORT_TOPIC", "قدم کوچک")
    scenes = [
        os.getenv("SCENE_1", "شاید لازم نیست همه چیز را همین امروز حل کنی."),
        os.getenv("SCENE_2", "فقط یک قدم بردار."),
        os.getenv("SCENE_3", "گاهی نوری که دنبالش میگردی از درون خودت روشن میشود."),
        os.getenv("SCENE_4", "از درون خودت روشن میشود."),
    ]
    script = " ".join(scenes)
    title = f"Imam Ali ✨ {topic}"

    prompts = cinematic_prompts_for_scenes(scenes, topic=topic)
    print("[colab] cinematic prompts:", json.dumps(prompts, ensure_ascii=False, indent=2))

    out_dir = ROOT / "output" / "colab_short"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "video_raw.mp4"

    result = generate_film(
        script=script,
        title=title,
        out_path=out_path,
        kind="short",
        seed=110,
    )
    print("[colab] done:", json.dumps(result, ensure_ascii=False, indent=2))
    print("[colab] video:", out_path)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
