"""Run on Kaggle GPU kernel — produces video_raw.mp4 in /kaggle/working.

Triggered by GitHub Actions when KAGGLE_* secrets are set.
"""
from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
from pathlib import Path

OUT = Path("/kaggle/working")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    print("[kaggle-gpu] start", flush=True)
    try:
        import torch
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video
    except Exception as exc:
        print("[kaggle-gpu] install deps...", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "diffusers", "transformers", "accelerate", "imageio-ffmpeg"]
        )
        import torch
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video

    print("[kaggle-gpu] cuda:", torch.cuda.is_available(), flush=True)
    if not torch.cuda.is_available():
        print("[kaggle-gpu] NO GPU — abort", flush=True)
        return 1

    prompts = [
        "cloaked figure taking one careful step on wet stone path, glowing golden trail, candle-lit cathedral hall, cinematic volumetric light, natural motion, no text",
        "tree of luminous golden light growing from a person's chest in a dark sacred hall, soft camera push-in, filmic color grading, no text no watermark",
    ]

    model_id = "THUDM/CogVideoX-2b"
    pipe = CogVideoXPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    try:
        pipe.enable_model_cpu_offload()
    except Exception:
        pipe.to("cuda")

    clips = []
    for i, prompt in enumerate(prompts):
        print(f"[kaggle-gpu] scene {i+1}", prompt[:60], flush=True)
        gc.collect()
        torch.cuda.empty_cache()
        result = pipe(
            prompt=prompt,
            num_videos_per_prompt=1,
            num_inference_steps=8,
            num_frames=17,
            guidance_scale=6.0,
            generator=torch.Generator(device="cpu").manual_seed(110 + i),
        )
        clip = OUT / f"scene_{i:02d}.mp4"
        export_to_video(result.frames[0], str(clip), fps=8)
        clips.append(clip)
        del result
        gc.collect()
        torch.cuda.empty_cache()

    list_file = OUT / "concat.txt"
    list_file.write_text("\n".join(f"file '{c}'" for c in clips), encoding="utf-8")
    final = OUT / "video_raw.mp4"
    subprocess.check_call(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=8",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
            str(final),
        ]
    )
    meta = {"ok": True, "path": str(final), "bytes": final.stat().st_size, "provider": "kaggle-gpu"}
    (OUT / "result.json").write_text(json.dumps(meta), encoding="utf-8")
    print("[kaggle-gpu] SUCCESS", meta, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
