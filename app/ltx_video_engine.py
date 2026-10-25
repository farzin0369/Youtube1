"""LTX-Video renderer with scene/narration duration matching and resumable clips."""
from __future__ import annotations

import gc
import inspect
import math
import os
import subprocess
from pathlib import Path
from typing import Any


def _frames_for_duration(seconds: float, fps: int = 8) -> int:
    """LTX temporal length must be 8n+1; choose the closest usable length."""
    if fps < 1:
        raise ValueError("fps must be positive")
    target = max(1.0, float(seconds)) * fps
    n = max(1, round((target - 1) / 8))
    return 8 * n + 1


def _probe_clip_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _normalize_scene_durations(scenes: list[dict[str, Any]], target_seconds: float) -> None:
    """Allocate whole-second scene lengths whose sum matches the narration duration."""
    if not scenes:
        raise ValueError("scene plan must contain at least one scene")
    target = float(target_seconds)
    if target <= 0:
        raise ValueError("target_seconds must be positive")
    total_seconds = max(len(scenes), int(round(target)))
    weights = [max(0.5, float(scene.get("duration_hint_seconds") or 1.0)) for scene in scenes]
    allocations = [0] * len(scenes)
    active = set(range(len(scenes)))
    remaining = total_seconds

    # Reserve at least one second for each scene; re-apportion the rest by narration weight.
    while active:
        weight_sum = sum(weights[index] for index in active)
        proposed = {index: remaining * weights[index] / weight_sum for index in active}
        too_short = [index for index, seconds in proposed.items() if seconds < 1.0]
        if too_short:
            for index in too_short:
                allocations[index] = 1
                active.remove(index)
                remaining -= 1
            continue
        floors = {index: int(math.floor(seconds)) for index, seconds in proposed.items()}
        for index, seconds in floors.items():
            allocations[index] = seconds
        remaining -= sum(floors.values())
        ranked = sorted(active, key=lambda index: proposed[index] - floors[index], reverse=True)
        for index in ranked[:remaining]:
            allocations[index] += 1
        break

    for scene, seconds in zip(scenes, allocations):
        scene["duration_hint_seconds"] = float(seconds)


def generate_ltx_film(
    script: str,
    title: str,
    out_path: Path,
    kind: str = "short",
    seed: int = 110,
    scene_plan: list[dict[str, Any]] | None = None,
    target_duration_seconds: float | None = None,
) -> dict[str, Any]:
    """Generate a moving clip for each narration scene and concatenate to silent MP4."""
    import torch
    from diffusers import LTXPipeline
    from diffusers.utils import export_to_video
    from app.scene_plan import atomic_write_json, load_or_create_plan, mark_scene

    if kind not in {"short", "long"}:
        raise ValueError("kind must be 'short' or 'long'")
    if not torch.cuda.is_available():
        raise RuntimeError("LTX-Video requires a CUDA GPU; no CPU or stock-footage fallback is enabled.")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path = out_path.with_name("scene_plan.json")
    clip_count = int(os.getenv("LTX_SCENES_SHORT", "4") if kind == "short" else os.getenv("LTX_SCENES_LONG", "40"))
    target_duration = float(target_duration_seconds or (45 if kind == "short" else 240))
    plan = load_or_create_plan(
        plan_path, script, title, scene_plan=scene_plan,
        kind=kind, scene_count=clip_count, duration_hint_seconds=target_duration,
    )
    _normalize_scene_durations(plan["scenes"], target_duration)
    atomic_write_json(plan_path, plan)

    model_id = os.getenv("LTX_MODEL", "Lightricks/LTX-Video-0.9.8-2B-distilled")
    fps = int(os.getenv("LTX_GENERATION_FPS", "8"))
    steps = int(os.getenv("LTX_VIDEO_STEPS", "8"))
    width = int(os.getenv("LTX_VIDEO_W", "384" if kind == "short" else "672"))
    height = int(os.getenv("LTX_VIDEO_H", "672" if kind == "short" else "384"))
    guidance = float(os.getenv("LTX_GUIDANCE_SCALE", "3.0"))
    dtype = torch.float16
    print(f"[ltx] loading {model_id} on {torch.cuda.get_device_name(0)}", flush=True)
    # Low-memory initialization is essential on Colab T4. The previous default
    # selected the much larger 13B checkpoint and then moved the whole pipeline
    # to CUDA when model offload was unavailable, which can kill the runtime.
    pipe = LTXPipeline.from_pretrained(
        model_id,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    )
    try:
        pipe.enable_model_cpu_offload()
        print("[ltx] enabled model CPU offload", flush=True)
    except Exception as offload_error:
        # Sequential offload is slower but safer than pipe.to("cuda") on a 16 GB T4.
        try:
            pipe.enable_sequential_cpu_offload()
            print("[ltx] model CPU offload unavailable; enabled sequential CPU offload", flush=True)
        except Exception as sequential_error:
            del pipe
            gc.collect()
            torch.cuda.empty_cache()
            raise RuntimeError(
                "Could not enable memory-safe LTX offload; refusing to move the entire "
                f"pipeline to GPU. model_offload={offload_error}; "
                f"sequential_offload={sequential_error}"
            ) from sequential_error

    clips_dir = out_path.parent / "ltx_scene_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    try:
        for scene in plan["scenes"]:
            idx = int(scene["index"])
            clip = clips_dir / f"{scene['scene_id']}.mp4"
            if scene.get("status") == "complete" and clip.exists() and clip.stat().st_size > 80_000:
                try:
                    if abs(_probe_clip_duration(clip) - float(scene["duration_hint_seconds"])) <= 0.35:
                        continue
                except (OSError, ValueError, subprocess.CalledProcessError):
                    pass  # Stale or unreadable checkpoint: regenerate this scene.
            spoken = str(scene["spoken_text"])
            prompt = str(scene.get("visual_prompt") or "").strip()
            if not prompt:
                orientation = "vertical 9:16" if kind == "short" else "horizontal 16:9"
                prompt = (
                    f"Cinematic photorealistic spiritual self-reflection scene inspired by this narration: {spoken}. "
                    f"Compose for {orientation}; meaningful visual metaphor, natural human proportions, "
                    "subtle continuous motion, slow dolly camera, volumetric golden light, detailed environment, "
                    "no text, no subtitles, no logo, no watermark."
                )
            scene["visual_prompt"] = prompt
            mark_scene(plan, idx, status="running", clip_path=str(clip), error=None)
            atomic_write_json(plan_path, plan)
            scene_seconds = max(1.0, float(scene["duration_hint_seconds"]))
            frames = _frames_for_duration(scene_seconds, fps)
            scene_fps = frames / scene_seconds
            print(f"[ltx] scene {idx + 1}/{len(plan['scenes'])}: {frames} frames, target {scene_seconds:.0f}s", flush=True)
            gc.collect()
            torch.cuda.empty_cache()
            call_kwargs: dict[str, Any] = {
                "prompt": prompt,
                "negative_prompt": (
                    "static image, blurry, deformed anatomy, duplicate face, extra limbs, "
                    "text, watermark, logo, unrelated scene"
                ),
                "width": width,
                "height": height,
                "num_frames": frames,
                "num_inference_steps": steps,
                "generator": torch.Generator(device="cpu").manual_seed(seed + idx),
            }
            try:
                parameters = inspect.signature(pipe.__call__).parameters
                if "guidance_scale" in parameters:
                    call_kwargs["guidance_scale"] = guidance
            except (TypeError, ValueError):
                pass
            result = pipe(**call_kwargs)
            clip_frames = result.frames[0]
            export_to_video(clip_frames, str(clip), fps=scene_fps)
            del result, clip_frames
            if not clip.exists() or clip.stat().st_size < 80_000:
                mark_scene(plan, idx, status="failed", clip_path=str(clip), error="clip missing or too small")
                atomic_write_json(plan_path, plan)
                raise RuntimeError(f"LTX output failed basic size check for scene {idx + 1}")
            mark_scene(plan, idx, status="complete", clip_path=str(clip), error=None)
            atomic_write_json(plan_path, plan)
            gc.collect()
            torch.cuda.empty_cache()

        clips = [Path(scene["clip_path"]) for scene in plan["scenes"]]
        concat = out_path.parent / "ltx_concat.txt"
        concat.write_text(
            "\n".join("file '" + path.resolve().as_posix().replace("'", "'\\''") + "'" for path in clips),
            encoding="utf-8",
        )
        if kind == "short":
            width_out, height_out = 1080, 1920
        else:
            width_out, height_out = 1920, 1080
        result = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
            "-vf", f"scale={width_out}:{height_out}:force_original_aspect_ratio=increase,crop={width_out}:{height_out},fps=24,format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(out_path),
        ], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("FFmpeg LTX concat failed: " + result.stderr[-1200:])
    except Exception:
        atomic_write_json(plan_path, plan)
        raise
    finally:
        del pipe
        gc.collect()
        torch.cuda.empty_cache()

    return {
        "video_path": str(out_path), "provider": "ltx-video-colab-gpu",
        "model": model_id, "clips": len(plan["scenes"]), "scene_mapping": "scene_plan_v1",
        "scene_plan_path": str(plan_path), "resumable": True, "output_fps": 24,
        "generation_fps": fps, "target_duration_seconds": target_duration,
        "output_aspect_ratio": "9:16" if kind == "short" else "16:9", "ok": True,
    }
