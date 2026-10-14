"""Optional open-source LTX-Video backend for scene-matched AI-generated clips.

Cloud LLMs (for example Cloudflare Workers AI) still write the script and visual
prompts. LTX-Video renders the pixels on a CUDA GPU; the text API is not a video
renderer. Selecting this backend is fail-closed: it never silently substitutes
stock footage when AI generation fails.
"""
from __future__ import annotations

import os
from pathlib import Path


STYLE = (
    "cinematic documentary footage, realistic natural motion, carefully composed "
    "wide establishing shot, atmospheric practical lighting, subtle camera movement, "
    "high detail, filmic color grading, no captions, no logos, no watermark"
)
NEGATIVE = (
    "text, subtitles, letters, logos, watermark, flicker, jitter, warped objects, "
    "duplicated limbs, low resolution, oversaturated, cartoon, still image"
)


def generate_ltx_clips(
    prompts: list[str],
    out_dir: Path,
    *,
    width: int = 512,
    height: int = 896,
    num_frames: int = 121,
    fps: int = 24,
) -> list[Path]:
    """Generate one short clip per prompt using the official LTX Diffusers pipeline."""
    cleaned = [str(prompt).strip() for prompt in prompts]
    if not cleaned or any(not prompt for prompt in cleaned):
        raise ValueError("LTX requires one non-empty visual prompt per scene")
    if num_frames < 9 or (num_frames - 1) % 8:
        raise ValueError("LTX num_frames must be 8n+1 and at least 9")
    if width < 256 or height < 256 or width % 32 or height % 32:
        raise ValueError("LTX dimensions must be at least 256 and divisible by 32")

    try:
        import torch
        from diffusers import LTXPipeline
        from diffusers.utils import export_to_video
    except ImportError as exc:
        raise RuntimeError(
            "LTX backend dependencies are missing; install requirements-local.txt on a CUDA GPU"
        ) from exc

    if not torch.cuda.is_available():
        raise RuntimeError(
            "AI_VIDEO_ENGINE=ltx requires a CUDA GPU. GitHub-hosted CPU runners cannot render LTX videos."
        )

    model_id = (os.getenv("LTX_MODEL_ID") or "Lightricks/LTX-Video").strip()
    steps = int(os.getenv("LTX_INFERENCE_STEPS") or "20")
    if steps < 1 or steps > 60:
        raise ValueError("LTX_INFERENCE_STEPS must be between 1 and 60")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    pipe = LTXPipeline.from_pretrained(model_id, torch_dtype=dtype)
    # CPU offload reduces peak VRAM requirements on common Colab GPUs.
    pipe.enable_model_cpu_offload()
    if hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_tiling"):
        pipe.vae.enable_tiling()

    outputs: list[Path] = []
    try:
        for index, prompt in enumerate(cleaned):
            full_prompt = f"{prompt}. {STYLE}"
            result = pipe(
                prompt=full_prompt,
                negative_prompt=NEGATIVE,
                width=width,
                height=height,
                num_frames=num_frames,
                num_inference_steps=steps,
                guidance_scale=3.0,
            )
            frames = result.frames[0]
            target = out_dir / f"ltx_scene_{index:02d}.mp4"
            export_to_video(frames, str(target), fps=fps)
            if not target.is_file() or target.stat().st_size < 50_000:
                raise RuntimeError(f"LTX returned an invalid video for scene {index + 1}")
            outputs.append(target)
            del result, frames
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    finally:
        del pipe
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return outputs
