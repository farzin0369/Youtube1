"""Wan2.1 text-to-video backend (Apache-2.0 1.3B model).

The Cloudflare text model writes the script and visual prompts. Wan2.1 renders
the actual frames on a CUDA GPU; the text API itself is not a video renderer.
"""
from __future__ import annotations

import os
from pathlib import Path


REFERENCE_STYLE = (
    "cinematic dark fantasy, gothic stone cathedral interior, deep black and blue-teal "
    "shadows, high-contrast golden light, volumetric god rays, realistic stone texture, "
    "subtle film grain, physically plausible lighting, premium film color grade, vertical "
    "composition, smooth slow stabilized camera movement, no text, no captions, no logo, "
    "no watermark"
)
DEFAULT_STYLE = (
    "cinematic realistic documentary footage, natural motion, atmospheric practical "
    "lighting, smooth subtle camera movement, detailed environment, filmic color grading, "
    "no text, no captions, no logo, no watermark"
)
NEGATIVE = (
    "subtitles, letters, watermark, logo, static image, flicker, jitter, blurry details, "
    "distorted anatomy, duplicate objects, cartoon, overexposed"
)
MIN_FREE_VRAM_BYTES = 8_190_000_000
CINEMATIC_FREE_VRAM_BYTES = 24 * 1024**3


def _quality_profile() -> str:
    value = (os.getenv("WAN_QUALITY_PROFILE") or "cinematic").strip().lower()
    if value not in {"cinematic", "low_memory"}:
        raise ValueError("WAN_QUALITY_PROFILE must be 'cinematic' or 'low_memory'")
    return value


def _style_profile() -> str:
    value = (os.getenv("WAN_STYLE_PROFILE") or "reference_dark_fantasy").strip().lower()
    if value == "reference_dark_fantasy":
        return REFERENCE_STYLE
    if value == "default":
        return DEFAULT_STYLE
    raise ValueError("WAN_STYLE_PROFILE must be 'reference_dark_fantasy' or 'default'")


def _scene_prompt(query: str, index: int, style: str) -> str:
    """Turn a short content query into a repeatable cinematic shot brief."""
    shot = (
        "macro close-up of boots crossing a glowing stone floor, slow forward dolly"
        if index == 0 else
        "wide rear tracking shot following the same cloaked figure through the hall, slow dolly"
        if index == 1 else
        "medium frontal reveal as the golden light gathers and grows into a luminous tree, slow push-in"
        if index == 2 else
        "quiet close-up of the figure and the surrounding golden light, slow orbit, contemplative ending"
    )
    return f"{shot}; {query}; {style}"


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
    profile = _quality_profile()
    required_vram = CINEMATIC_FREE_VRAM_BYTES if profile == "cinematic" else MIN_FREE_VRAM_BYTES

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
    if int(free_vram_bytes) < required_vram:
        free_gib = int(free_vram_bytes) / (1024 ** 3)
        required_gib = required_vram / (1024 ** 3)
        raise RuntimeError(
            f"AI_VIDEO_ENGINE=wan {profile} profile needs at least {required_gib:.2f} GB free CUDA VRAM before model download; "
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

    default_model = (
        "Wan-AI/Wan2.1-T2V-14B-Diffusers"
        if profile == "cinematic" else "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
    )
    model_id = (os.getenv("WAN_MODEL_ID") or default_model).strip()
    steps = int(os.getenv("WAN_INFERENCE_STEPS") or ("32" if profile == "cinematic" else "20"))
    if steps < 1 or steps > 60:
        raise ValueError("WAN_INFERENCE_STEPS must be between 1 and 60")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    style = _style_profile()
    try:
        seed = int(os.getenv("WAN_SEED") or "110")
    except ValueError:
        raise ValueError("WAN_SEED must be an integer") from None
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
            generator = torch.Generator(device="cuda").manual_seed(seed + index)
            result = pipe(
                prompt=_scene_prompt(prompt, index, style),
                negative_prompt=NEGATIVE,
                width=width,
                height=height,
                num_frames=num_frames,
                num_inference_steps=steps,
                guidance_scale=5.0,
                generator=generator,
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
