#!/usr/bin/env python3
"""LTX-Video scene renderer for the ImamAli110 Colab GPU path.

Upstream model: https://github.com/Lightricks/LTX-Video
This renders visual clips only. It never uploads or publishes to YouTube.
For story-aligned production, pass a scene plan containing a visual_prompt for
each scene (JSON list, or an object with a "scenes" list).
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

MIN_SCENE_BYTES = 80_000
MIN_FINAL_BYTES = 200_000

DEMO_PROMPTS = [
    "A tired traveler pauses at a quiet mountain path at sunrise, soft golden light breaking through clouds, slow cinematic dolly forward, contemplative spiritual mood, photorealistic, natural movement, vertical composition, no text, no logo, no watermark.",
    "Close shot of a hand opening to release a small worn coin beside a simple wooden table, warm window light, subtle camera slide, realistic textures, quiet emotional storytelling, vertical composition, no text, no logo, no watermark.",
    "A solitary person stands beside a calm lake at dawn, wind moving their coat gently, sunlight reflecting on rippling water, slow camera orbit, hopeful contemplative mood, photorealistic, vertical composition, no text, no logo, no watermark.",
    "A narrow path through a forest opens into warm sunlight, leaves moving softly in the breeze, slow forward tracking shot, hopeful peaceful ending, photorealistic, vertical composition, no text, no logo, no watermark.",
]


def _load_scene_prompts(path: Path | None, strict: bool) -> list[str]:
    if path and path.is_file():
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
        scenes = payload.get("scenes", payload) if isinstance(payload, dict) else payload
        if not isinstance(scenes, list) or not scenes:
            raise ValueError(f"Scene plan has no non-empty scenes list: {path}")
        prompts: list[str] = []
        for index, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                raise ValueError(f"Scene {index} must be a JSON object")
            prompt = next((scene.get(key) for key in (
                "visual_prompt", "video_prompt", "visual_query", "prompt"
            ) if isinstance(scene.get(key), str) and scene[key].strip()), None)
            if not prompt:
                raise ValueError(
                    f"Scene {index} has no visual_prompt/video_prompt/visual_query/prompt. "
                    "Do not substitute unrelated stock prompts."
                )
            prompts.append(prompt.strip())
        return prompts
    if strict:
        raise FileNotFoundError(
            "A scene plan is required. Pass --scene-plan or set LTX_SCENE_PLAN."
        )
    print("[ltx] WARNING: no scene plan supplied; using demo prompts only. "
          "This output is not approved for publishing.", flush=True)
    return DEMO_PROMPTS


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-1800:]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-plan", default=os.getenv("LTX_SCENE_PLAN"))
    parser.add_argument("--output", default="/content/video_raw.mp4")
    parser.add_argument("--strict-scene-plan", action="store_true")
    parser.add_argument("--frames", type=int, default=int(os.getenv("VIDEO_FRAMES", "49")))
    parser.add_argument("--steps", type=int, default=int(os.getenv("VIDEO_STEPS", "30")))
    parser.add_argument("--height", type=int, default=int(os.getenv("VIDEO_H", "768")))
    parser.add_argument("--width", type=int, default=int(os.getenv("VIDEO_W", "512")))
    args = parser.parse_args()

    print("[ltx] start", flush=True)
    try:
        import torch
        from diffusers import LTXPipeline
        from diffusers.utils import export_to_video
    except Exception:
        print("[ltx] installing inference dependencies...", flush=True)
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-q",
            "diffusers>=0.41.0", "transformers", "accelerate",
            "imageio-ffmpeg", "sentencepiece", "safetensors",
        ])
        import torch
        from diffusers import LTXPipeline
        from diffusers.utils import export_to_video

    if not torch.cuda.is_available():
        raise RuntimeError("No CUDA GPU. Select a GPU runtime in Google Colab; CPU generation is disabled.")

    print("[ltx] GPU:", torch.cuda.get_device_name(0), flush=True)
    free, total = torch.cuda.mem_get_info()
    print(f"[ltx] VRAM free/total={free / 1e9:.1f}/{total / 1e9:.1f} GB", flush=True)

    model_id = os.getenv("LTX_MODEL", "Lightricks/LTX-Video")
    prompts = _load_scene_prompts(
        Path(args.scene_plan) if args.scene_plan else None,
        args.strict_scene_plan,
    )
    frames = max(9, args.frames)
    # LTX requires frame counts of 8n+1 and spatial dimensions divisible by 32.
    frames = ((frames - 1) // 8) * 8 + 1
    height = max(256, (args.height // 32) * 32)
    width = max(256, (args.width // 32) * 32)
    steps = max(1, args.steps)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.parent / "ltx_scene_clips"
    work.mkdir(parents=True, exist_ok=True)

    # FP16 is more appropriate for Colab T4 than BF16. CPU offload is required
    # to reduce peak VRAM; no fake low-quality renderer is used on failure.
    dtype = torch.float16
    print(f"[ltx] loading {model_id}; {len(prompts)} scenes; {width}x{height}; "
          f"{frames} frames; {steps} steps", flush=True)
    pipe = LTXPipeline.from_pretrained(model_id, torch_dtype=dtype, low_cpu_mem_usage=True)
    pipe.enable_model_cpu_offload()

    clips: list[Path] = []
    for index, prompt in enumerate(prompts, start=1):
        clip = work / f"scene_{index:02d}.mp4"
        print(f"[ltx] scene {index}/{len(prompts)}", flush=True)
        gc.collect()
        torch.cuda.empty_cache()
        result = pipe(
            prompt=prompt,
            negative_prompt=(
                "blurry, low quality, frozen frame, jittery motion, distorted anatomy, "
                "unreadable text, subtitles, watermark, logo, oversaturated"
            ),
            width=width,
            height=height,
            num_frames=frames,
            num_inference_steps=steps,
            guidance_scale=3.0,
        )
        frames_out = result.frames[0]
        export_to_video(frames_out, str(clip), fps=24)
        size = clip.stat().st_size
        print(f"[ltx] wrote {clip} ({size} bytes)", flush=True)
        if size < MIN_SCENE_BYTES:
            raise RuntimeError(f"QA failed: scene {index} is only {size} bytes")
        clips.append(clip)
        del result, frames_out
        gc.collect()
        torch.cuda.empty_cache()

    concat_file = work / "concat.txt"
    concat_file.write_text(
        "\n".join("file '" + str(p).replace("'", "'\\''") + "'" for p in clips) + "\n",
        encoding="utf-8",
    )
    _run_ffmpeg([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", f"scale=720:1280:force_original_aspect_ratio=decrease,"
               f"pad=720:1280:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-movflags", "+faststart", str(output),
    ])
    if not output.is_file() or output.stat().st_size < MIN_FINAL_BYTES:
        raise RuntimeError("QA failed: final MP4 missing or too small")
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", str(output),
    ], capture_output=True, text=True, check=True)
    stream = json.loads(probe.stdout)["streams"][0]
    if (stream.get("width"), stream.get("height")) != (720, 1280):
        raise RuntimeError(f"QA failed: expected 720x1280, got {stream}")
    print(json.dumps({
        "ok": True, "path": str(output), "bytes": output.stat().st_size,
        "engine": "Lightricks/LTX-Video", "scenes": len(clips),
        "width": 720, "height": 1280, "approved_for_publishing": False,
        "scene_plan_used": bool(args.scene_plan),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
