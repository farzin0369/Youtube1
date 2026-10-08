"""Local text-to-video engine using CogVideoX.
Runs the model on the self-hosted GPU; no hosted AI generation API is called.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from app.utils import env

def generate_text_video(prompt: str, out_path: Path, duration_seconds: int = 6, seed: int = 110) -> dict[str, Any]:
    try:
        import torch
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video
    except ImportError as e:
        raise RuntimeError("Install requirements-local.txt") from e
    if not torch.cuda.is_available():
        raise RuntimeError("Local text-to-video requires a CUDA GPU on the self-hosted runner.")
    model_id = env("LOCAL_VIDEO_MODEL") or "THUDM/CogVideoX-2b"
    pipe = CogVideoXPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    if hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_tiling"):
        pipe.vae.enable_tiling()
    frames = max(17, min(49, int(duration_seconds * 8) + 1))
    result = pipe(prompt=prompt, num_videos_per_prompt=1,
                  num_inference_steps=int(env("VIDEO_STEPS") or "30"),
                  num_frames=frames, guidance_scale=float(env("VIDEO_GUIDANCE") or "6"),
                  generator=torch.Generator(device="cuda").manual_seed(seed))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(result.frames[0], str(out_path), fps=8)
    return {"video_path": str(out_path), "provider": "cogvideox-local",
            "model": model_id, "duration_generated": frames / 8, "ok": True}
