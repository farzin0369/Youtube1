"""Wan2.1 text-to-video backend (Apache-2.0 1.3B model).

The Cloudflare text model writes the script and visual prompts. Wan2.1 renders
the actual frames on a CUDA GPU; the text API itself is not a video renderer.
"""
from __future__ import annotations

import os
from pathlib import Path


STYLE = (
    "cinematic realistic documentary footage, natural motion, atmospheric practical "
    "lighting, smooth subtle camera movement, detailed environment, filmic color grading, "
    "no text, no captions, no logo, no watermark"
)
NEGATIVE = (
    "subtitles, letters, watermark, logo, static image, flicker, jitter, blurry details, "
    "distorted anatomy, duplicate objects, cartoon, overexposed"
)
MIN_FREE_VRAM_BYTES = 8_190_000_000


def generate_wan_clips(
    prompts: list[str],
    out_dir: Path,
    *,
    width: int = 480,
    height: int = 832,
    num_frames: int = 81,
    fps: int = 16,
) -> list[Path]:
    """Generate one portrait video clip per scene with Wan2.1 T2V-1.3B."""
    cleaned = [str(prompt).strip() for prompt in prompts]
    if not cleaned or any(not prompt for prompt in cleaned):
        raise ValueError("Wan requires one non-empty visual prompt per scene")
    if num_frames < 9 or (num_frames - 1) % 4:
        raise ValueError("Wan num_frames must be 4n+1 and at least 9")
    if width < 256 or height < 256 or width % 16 or height % 16:
        raise ValueError("Wan dimensions must be at least 256 and divisible by 16")

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "Wan dependencies are missing; install requirements-local.txt on a CUDA GPU"
        ) from exc

    if not torch.cuda.is_available():
        raise RuntimeError(
            "AI_VIDEO_ENGINE=wan requires a CUDA GPU. Standard GitHub-hosted runners are CPU-only."
        )

    try:
        free_vram_bytes, _ = torch.cuda.mem_get_info(0)
    except Exception as exc:
        raise RuntimeError("Could not query free CUDA VRAM; refusing to download the Wan model.") from exc
    if int(free_vram_bytes) < MIN_FREE_VRAM_BYTES:
        free_gib = int(free_vram_bytes) / (1024 ** 3)
        required_gib = MIN_FREE_VRAM_BYTES / (1024 ** 3)
        raise RuntimeError(
            f"AI_VIDEO_ENGINE=wan needs at least 8.19 GB free CUDA VRAM before model download; "
            f"available {free_gib:.2f} GiB, required {required_gib:.2f} GiB."
        )

    try:
        from diffusers import AutoencoderKLWan, WanPipeline
        from diffusers.schedulers.scheduling_unipc_multistep import UniPCMultistepScheduler
        from diffusers.utils import export_to_video
    except ImportError as exc:
        raise RuntimeError(
            "Wan dependencies are missing; install requirements-local.txt on a CUDA GPU"
        ) from exc

    model_id = (os.getenv("WAN_MODEL_ID") or "Wan-AI/Wan2.1-T2V-1.3B-Diffusers").strip()
    steps = int(os.getenv("WAN_INFERENCE_STEPS") or "20")
    if steps < 1 or steps > 60:
        raise ValueError("WAN_INFERENCE_STEPS must be between 1 and 60")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Keep VAE decode in fp32 for stability; T4 supports fp16 for the main model.
    vae = AutoencoderKLWan.from_pretrained(
        model_id, subfolder="vae", torch_dtype=torch.float32
    )
    pipe = WanPipeline.from_pretrained(
        model_id, vae=vae, torch_dtype=torch.float16
    )
    pipe.scheduler = UniPCMultistepScheduler(
        prediction_type="flow_prediction",
        use_flow_sigmas=True,
        num_train_timesteps=1000,
        flow_shift=3.0,
    )
    pipe.enable_model_cpu_offload()

    outputs: list[Path] = []
    try:
        for index, prompt in enumerate(cleaned):
            result = pipe(
                prompt=f"{prompt}. {STYLE}",
                negative_prompt=NEGATIVE,
                width=width,
                height=height,
                num_frames=num_frames,
                num_inference_steps=steps,
                guidance_scale=5.0,
            )
            frames = result.frames[0]
            target = out_dir / f"wan_scene_{index:02d}.mp4"
            export_to_video(frames, str(target), fps=fps)
            if not target.is_file() or target.stat().st_size < 50_000:
                raise RuntimeError(f"Wan returned an invalid video for scene {index + 1}")
            outputs.append(target)
            del result, frames
            torch.cuda.empty_cache()
    finally:
        del pipe, vae
        torch.cuda.empty_cache()
    return outputs
