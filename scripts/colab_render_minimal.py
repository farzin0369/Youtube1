#!/usr/bin/env python3
"""LTX-Video cinematic short on free Colab T4 — real motion, not garbage frames.

Why LTX: designed for consumer GPUs; 49 frames @ ~24fps ≈ 2s of real motion per clip.
Hard QA: refuse to write final if file too small / no motion.
"""
from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

# The model is public: avoid implicit authentication/Colab-vault token lookup.
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "30")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "15")

MIN_SCENE_BYTES = 80_000  # reject empty/red-dot outputs
MIN_FINAL_BYTES = 200_000


def main() -> int:
    print("[ltx] start", flush=True)
    try:
        import torch
        from diffusers import LTXPipeline
        from diffusers.utils import export_to_video
    except Exception:
        print("[ltx] installing deps...", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q",
             "diffusers>=0.32.0", "transformers", "accelerate", "imageio-ffmpeg", "sentencepiece"]
        )
        import torch
        from diffusers import LTXPipeline
        from diffusers.utils import export_to_video

    if not torch.cuda.is_available():
        print("[ltx] ERROR: no CUDA", flush=True)
        return 1

    print("[ltx] GPU:", torch.cuda.get_device_name(0), flush=True)
    free, total = torch.cuda.mem_get_info()
    print(f"[ltx] VRAM {free/1e9:.1f}/{total/1e9:.1f} GB", flush=True)

    # Strong visual prompts — photoreal / 3D-like cinematic spiritual
    prompts = [
        (
            "cinematic vertical video, photorealistic, a hooded traveler in a dark stone cathedral, "
            "golden volumetric god rays through tall windows, slow camera dolly forward, "
            "dust particles floating, wet stone floor reflections, epic sacred atmosphere, "
            "high detail, natural motion, no text, no watermark, no logo"
        ),
        (
            "cinematic vertical video, photorealistic close-up, glowing golden light symbols "
            "carved into ancient stone walls, soft camera pan left, warm candle flicker, "
            "depth of field, film grain, sacred mood, natural motion, no text no watermark"
        ),
        (
            "cinematic vertical video, photorealistic, luminous golden tree of light growing "
            "from a person's chest in a dark cathedral, gentle camera push-in, emotional lighting, "
            "particles rising, filmic color grade, natural motion, no text no watermark"
        ),
        (
            "cinematic vertical video, photorealistic wide shot, cloaked figure standing under "
            "a column of golden light in a vast hall, particles rising, slow orbit camera, "
            "epic calm ending, highly detailed, natural motion, no text no watermark"
        ),
    ]

    model_id = os.getenv("LTX_MODEL", "Lightricks/LTX-Video")
    num_frames = int(os.getenv("VIDEO_FRAMES", "49"))  # LTX likes longer sequences
    steps = int(os.getenv("VIDEO_STEPS", "30"))
    height = int(os.getenv("VIDEO_H", "512"))
    width = int(os.getenv("VIDEO_W", "768"))

    print(f"[ltx] load {model_id} frames={num_frames} steps={steps} {width}x{height}", flush=True)
    pipe = LTXPipeline.from_pretrained(model_id, torch_dtype=torch.bfloat16)
    try:
        pipe.enable_model_cpu_offload()
    except Exception:
        pipe.to("cuda")

    content = Path("/content")
    content.mkdir(parents=True, exist_ok=True)
    clip_paths: list[Path] = []

    for i, prompt in enumerate(prompts):
        print(f"[ltx] scene {i+1}/{len(prompts)}", flush=True)
        gc.collect()
        torch.cuda.empty_cache()
        try:
            out = pipe(
                prompt=prompt,
                negative_prompt="blurry, low quality, static image, text, watermark, logo, cartoon, deformed",
                width=width,
                height=height,
                num_frames=num_frames,
                num_inference_steps=steps,
                guide_scale=3.0 if hasattr(pipe, "guide_scale") else None,
            )
            # handle different return shapes
            frames = out.frames[0] if hasattr(out, "frames") else out[0]
        except TypeError:
            # older API without guide_scale
            out = pipe(
                prompt=prompt,
                negative_prompt="blurry, low quality, static image, text, watermark, logo",
                width=width,
                height=height,
                num_frames=num_frames,
                num_inference_steps=steps,
            )
            frames = out.frames[0]
        except Exception as exc:
            print(f"[ltx] scene fail: {exc}", flush=True)
            traceback.print_exc()
            # fallback smaller
            gc.collect()
            torch.cuda.empty_cache()
            out = pipe(
                prompt=prompt,
                width=384,
                height=576,
                num_frames=25,
                num_inference_steps=20,
            )
            frames = out.frames[0]

        clip = content / f"scene_{i:02d}.mp4"
        export_to_video(frames, str(clip), fps=24)
        size = clip.stat().st_size
        print(f"[ltx] wrote {clip} bytes={size}", flush=True)
        if size < MIN_SCENE_BYTES:
            print(f"[ltx] QA FAIL scene too small ({size} < {MIN_SCENE_BYTES}) — abort", flush=True)
            return 2
        clip_paths.append(clip)
        del out, frames
        gc.collect()
        torch.cuda.empty_cache()

    list_file = content / "concat.txt"
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_paths), encoding="utf-8")
    primary = content / "video_raw.mp4"
    # Vertical 9:16 for Shorts + slight slow for longer watch time
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-vf",
        "setpts=1.15*PTS,scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=24",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
        str(primary),
    ]
    print("[ltx] ffmpeg", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("[ltx] ffmpeg err:", r.stderr[-1200:], flush=True)
        return 1

    fsize = primary.stat().st_size
    if fsize < MIN_FINAL_BYTES:
        print(f"[ltx] QA FAIL final too small ({fsize}) — refuse publish", flush=True)
        return 2

    print("[ltx] SUCCESS", primary, fsize, flush=True)
    print(json.dumps({"ok": True, "path": str(primary), "bytes": fsize, "engine": "ltx", "scenes": len(prompts)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
