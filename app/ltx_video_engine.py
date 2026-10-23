"""LTX-Video scene renderer used by the production pipeline."""
from __future__ import annotations

import gc
import os
import subprocess
from pathlib import Path
from typing import Any

def generate_ltx_film(
    script: str,
    title: str,
    out_path: Path,
    kind: str = "short",
    seed: int = 110,
    scene_plan: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Render scene-matched clips with LTX-Video and concatenate them to silent MP4."""
    import torch
    from diffusers import LTXPipeline
    from diffusers.utils import export_to_video
    from app.scene_plan import atomic_write_json, load_or_create_plan, mark_scene

    if not torch.cuda.is_available():
        raise RuntimeError("LTX-Video requires a CUDA GPU; no CPU fallback is enabled.")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path = out_path.with_name("scene_plan.json")
    clip_count = int(os.getenv("LTX_SCENES_SHORT", "4") if kind == "short" else os.getenv("LTX_SCENES_LONG", "12"))
    plan = load_or_create_plan(
        plan_path, script, title, scene_plan=scene_plan,
        kind=kind, scene_count=clip_count,
        duration_hint_seconds=float(os.getenv("VIDEO_DURATION_HINT_SECONDS", "45" if kind == "short" else "240")),
    )
    model_id = os.getenv("LTX_MODEL", "Lightricks/LTX-Video")
    dtype = torch.float16
    print(f"[ltx] loading {model_id} on {torch.cuda.get_device_name(0)}", flush=True)
    pipe = LTXPipeline.from_pretrained(model_id, torch_dtype=dtype)
    try:
        pipe.enable_model_cpu_offload()
    except Exception:
        pipe.to("cuda")
    frames = int(os.getenv("LTX_VIDEO_FRAMES", "49"))
    steps = int(os.getenv("LTX_VIDEO_STEPS", "20"))
    width = int(os.getenv("LTX_VIDEO_W", "576"))
    height = int(os.getenv("LTX_VIDEO_H", "384"))
    clips_dir = out_path.parent / "ltx_scene_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    try:
        for scene in plan["scenes"]:
            idx = int(scene["index"])
            clip = clips_dir / f"{scene['scene_id']}.mp4"
            if scene.get("status") == "complete" and clip.exists() and clip.stat().st_size > 80_000:
                continue
            spoken = str(scene["spoken_text"])
            prompt = str(scene.get("visual_prompt") or "").strip()
            if not prompt:
                prompt = (
                    f"Cinematic photorealistic spiritual self-reflection scene inspired by this narration: {spoken}. "
                    "Meaningful visual metaphor, realistic human proportions, subtle natural motion, "
                    "slow dolly camera, volumetric golden light, detailed environment, no text, no subtitles, "
                    "no logo, no watermark, vertical-video safe composition."
                )
            scene["visual_prompt"] = prompt
            mark_scene(plan, idx, status="running", clip_path=str(clip), error=None)
            atomic_write_json(plan_path, plan)
            print(f"[ltx] scene {idx + 1}/{len(plan['scenes'])}", flush=True)
            gc.collect()
            torch.cuda.empty_cache()
            result = pipe(
                prompt=prompt,
                negative_prompt="static image, blurry, deformed anatomy, duplicate face, extra limbs, text, watermark, logo",
                width=width,
                height=height,
                num_frames=frames,
                num_inference_steps=steps,
                generator=torch.Generator(device="cpu").manual_seed(seed + idx),
            )
            clip_frames = result.frames[0]
            export_to_video(clip_frames, str(clip), fps=24)
            del result, clip_frames
            if not clip.exists() or clip.stat().st_size < 80_000:
                mark_scene(plan, idx, status="failed", clip_path=str(clip), error="clip missing or too small")
                atomic_write_json(plan_path, plan)
                raise RuntimeError(f"LTX output failed basic size check for scene {idx + 1}")
            mark_scene(plan, idx, status="complete", clip_path=str(clip), error=None)
            atomic_write_json(plan_path, plan)
            gc.collect()
            torch.cuda.empty_cache()
        clips = [Path(s["clip_path"]) for s in plan["scenes"]]
        concat = out_path.parent / "ltx_concat.txt"
        concat.write_text("\n".join("file '" + p.resolve().as_posix().replace("'", "'\\''") + "'" for p in clips), encoding="utf-8")
        result = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=24",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
            str(out_path)
        ], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("FFmpeg LTX concat failed: " + result.stderr[-1200:])
    except Exception:
        atomic_write_json(plan_path, plan)
        raise
    return {
        "video_path": str(out_path), "provider": "ltx-video-colab-gpu",
        "model": model_id, "clips": len(plan["scenes"]), "scene_mapping": "scene_plan_v1",
        "scene_plan_path": str(plan_path), "resumable": True, "output_fps": 24, "ok": True,
    }
