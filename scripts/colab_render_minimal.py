#!/usr/bin/env python3
"""Minimal CogVideoX short renderer for free Colab T4.

Self-contained: no Ollama, no heavy pipeline deps.
Writes:
  /content/video_raw.mp4
  output/colab_short/video_raw.mp4  (if repo cwd)
"""
from __future__ import annotations

import gc
import json
import os
import sys
import traceback
from pathlib import Path


def main() -> int:
    print("[minimal] start", flush=True)
    try:
        import torch
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video
    except Exception as exc:
        print("[minimal] import failed:", type(exc).__name__, exc, flush=True)
        print("Run: pip install -U diffusers transformers accelerate imageio-ffmpeg", flush=True)
        return 1

    if not torch.cuda.is_available():
        print("[minimal] ERROR: no CUDA GPU. Runtime → Change runtime type → T4 GPU", flush=True)
        return 1

    print("[minimal] GPU:", torch.cuda.get_device_name(0), flush=True)
    free, total = torch.cuda.mem_get_info()
    print(f"[minimal] VRAM free {free/1e9:.1f}/{total/1e9:.1f} GB", flush=True)

    # English cinematic prompts (spiritual, vertical-friendly)
    prompts = [
        "cloaked figure taking one careful step on wet stone path, glowing golden trail, candle-lit cathedral hall, cinematic volumetric light, natural motion",
        "tree of luminous golden light growing from a person's chest in a dark sacred hall, soft camera push-in, filmic color grading, no text no watermark",
    ]

    model_id = os.getenv("LOCAL_VIDEO_MODEL", "THUDM/CogVideoX-2b")
    # T4-safe defaults
    num_frames = int(os.getenv("VIDEO_FRAMES", "9"))  # 4n+1
    steps = int(os.getenv("VIDEO_STEPS", "6"))

    print(f"[minimal] loading {model_id} frames={num_frames} steps={steps}", flush=True)
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
        print("[minimal] sequential CPU offload", flush=True)
    except Exception:
        pipe.enable_model_cpu_offload()
        print("[minimal] model CPU offload", flush=True)

    out_dirs = []
    content = Path("/content")
    if content.is_dir():
        out_dirs.append(content)
    # repo-relative
    cwd = Path.cwd()
    out_dirs.append(cwd / "output" / "colab_short")
    if (cwd / "Youtube1").is_dir():
        out_dirs.append(cwd / "Youtube1" / "output" / "colab_short")

    clip_paths: list[Path] = []
    for i, prompt in enumerate(prompts):
        print(f"[minimal] scene {i+1}/{len(prompts)}: {prompt[:80]}...", flush=True)
        gc.collect()
        torch.cuda.empty_cache()
        try:
            result = pipe(
                prompt=prompt,
                num_videos_per_prompt=1,
                num_inference_steps=steps,
                num_frames=num_frames,
                guidance_scale=6.0,
                generator=torch.Generator(device="cpu").manual_seed(110 + i),
            )
            frames = result.frames[0]
        except Exception as exc:
            print(f"[minimal] scene {i} failed:", type(exc).__name__, str(exc)[:500], flush=True)
            traceback.print_exc()
            # try even smaller
            if "memory" in str(exc).lower() or "cuda" in str(exc).lower():
                print("[minimal] retry with 9 frames / 4 steps", flush=True)
                gc.collect()
                torch.cuda.empty_cache()
                result = pipe(
                    prompt=prompt,
                    num_videos_per_prompt=1,
                    num_inference_steps=4,
                    num_frames=9,
                    guidance_scale=6.0,
                    generator=torch.Generator(device="cpu").manual_seed(110 + i),
                )
                frames = result.frames[0]
            else:
                return 1

        clip = content / f"scene_{i:02d}.mp4" if content.is_dir() else Path(f"scene_{i:02d}.mp4")
        export_to_video(frames, str(clip), fps=8)
        print(f"[minimal] wrote {clip} size={clip.stat().st_size}", flush=True)
        clip_paths.append(clip)
        del result, frames
        gc.collect()
        torch.cuda.empty_cache()

    # Concat with ffmpeg
    import subprocess

    list_file = (content if content.is_dir() else Path(".")) / "concat.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in clip_paths),
        encoding="utf-8",
    )
    final_candidates = []
    if content.is_dir():
        final_candidates.append(content / "video_raw.mp4")
    for d in out_dirs:
        d.mkdir(parents=True, exist_ok=True)
        final_candidates.append(d / "video_raw.mp4")

    primary = final_candidates[0]
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=8",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        str(primary),
    ]
    print("[minimal] ffmpeg", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("[minimal] ffmpeg stderr:", r.stderr[-800:], flush=True)
        return 1

    for dest in final_candidates[1:]:
        try:
            dest.write_bytes(primary.read_bytes())
            print(f"[minimal] copied to {dest}", flush=True)
        except Exception as exc:
            print(f"[minimal] copy skip {dest}: {exc}", flush=True)

    print("[minimal] SUCCESS", primary, primary.stat().st_size, flush=True)
    print(json.dumps({"ok": True, "path": str(primary), "bytes": primary.stat().st_size}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
