#!/usr/bin/env python3
"""Higher-quality CogVideoX short for free Colab T4.

Target: ~12–18s vertical cinematic (more scenes, more frames).
Writes /content/video_raw.mp4
"""
from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path


def main() -> int:
    print("[hq] start", flush=True)
    try:
        import torch
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video
    except Exception:
        print("[hq] installing deps...", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q",
             "diffusers", "transformers", "accelerate", "imageio-ffmpeg"]
        )
        import torch
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video

    if not torch.cuda.is_available():
        print("[hq] ERROR: no CUDA", flush=True)
        return 1

    print("[hq] GPU:", torch.cuda.get_device_name(0), flush=True)
    free, total = torch.cuda.mem_get_info()
    print(f"[hq] VRAM {free/1e9:.1f}/{total/1e9:.1f} GB", flush=True)

    # 4 cinematic beats aligned with Persian spiritual short
    prompts = [
        "cloaked hooded figure walks slowly into a vast candle-lit stone cathedral, golden dust in volumetric god rays, cinematic camera tracking shot, film grain, no text no watermark",
        "close-up of ancient golden light symbols glowing on dark stone walls, soft slow pan, sacred atmosphere, highly detailed, cinematic lighting, no text",
        "tree of luminous golden light grows from a person's chest in a dark sacred hall, gentle camera push-in, emotional spiritual mood, filmic color grade, no text",
        "wide shot of the same cloaked figure standing under a column of golden light, particles rising, epic calm ending, vertical 9:16 composition, cinematic, no text no watermark",
    ]

    model_id = os.getenv("LOCAL_VIDEO_MODEL", "THUDM/CogVideoX-2b")
    # CogVideoX needs 4n+1 frames. 17 frames @ 8fps ≈ 2.1s per scene → ~8.5s total
    num_frames = int(os.getenv("VIDEO_FRAMES", "17"))
    steps = int(os.getenv("VIDEO_STEPS", "10"))

    print(f"[hq] load {model_id} frames={num_frames} steps={steps} scenes={len(prompts)}", flush=True)
    pipe = CogVideoXPipeline.from_pretrained(
        model_id, torch_dtype=torch.float16, low_cpu_mem_usage=True
    )
    if hasattr(pipe, "vae"):
        if hasattr(pipe.vae, "enable_tiling"):
            pipe.vae.enable_tiling()
        if hasattr(pipe.vae, "enable_slicing"):
            pipe.vae.enable_slicing()
    try:
        pipe.enable_sequential_cpu_offload()
        print("[hq] sequential CPU offload", flush=True)
    except Exception:
        pipe.enable_model_cpu_offload()

    content = Path("/content")
    content.mkdir(parents=True, exist_ok=True)
    clip_paths: list[Path] = []

    for i, prompt in enumerate(prompts):
        print(f"[hq] scene {i+1}/{len(prompts)}", prompt[:70], flush=True)
        gc.collect()
        torch.cuda.empty_cache()
        try:
            result = pipe(
                prompt=prompt,
                num_videos_per_prompt=1,
                num_inference_steps=steps,
                num_frames=num_frames,
                guidance_scale=6.5,
                generator=torch.Generator(device="cpu").manual_seed(1100 + i),
            )
            frames = result.frames[0]
        except Exception as exc:
            print(f"[hq] OOM/fail scene {i}: {exc}", flush=True)
            traceback.print_exc()
            gc.collect()
            torch.cuda.empty_cache()
            result = pipe(
                prompt=prompt,
                num_videos_per_prompt=1,
                num_inference_steps=max(6, steps - 2),
                num_frames=13,
                guidance_scale=6.0,
                generator=torch.Generator(device="cpu").manual_seed(1100 + i),
            )
            frames = result.frames[0]

        clip = content / f"scene_{i:02d}.mp4"
        export_to_video(frames, str(clip), fps=8)
        print(f"[hq] wrote {clip} bytes={clip.stat().st_size}", flush=True)
        clip_paths.append(clip)
        del result, frames
        gc.collect()
        torch.cuda.empty_cache()

    list_file = content / "concat.txt"
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_paths), encoding="utf-8")
    primary = content / "video_raw.mp4"
    # Slight slow-mo for more screen time (~1.35x duration) while keeping motion smooth
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-vf",
        "setpts=1.35*PTS,scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=24",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(primary),
    ]
    print("[hq] ffmpeg", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("[hq] ffmpeg err:", r.stderr[-1000:], flush=True)
        return 1

    print("[hq] SUCCESS", primary, primary.stat().st_size, flush=True)
    print(json.dumps({"ok": True, "path": str(primary), "bytes": primary.stat().st_size, "scenes": len(prompts)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
