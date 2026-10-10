"""Local text-to-video film engine using CogVideoX text-to-video.
Scene prompts are mapped from the narration's meaning, not pasted as raw Persian text.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Any
from app.utils import env


def _valid_frames(frames: int) -> int:
    """CogVideoX accepts frame counts where (num_frames - 1) is divisible by 4."""
    frames = max(9, int(frames))
    remainder = (frames - 1) % 4
    if remainder:
        frames -= remainder
    return max(9, frames)


def render_attempt_profiles(frames: int, steps: int) -> list[tuple[int, int]]:
    """Full request first, then smaller T4-safe profiles. Duplicates are dropped."""
    frames = _valid_frames(frames)
    steps = max(1, int(steps))
    candidates = (
        (frames, steps),
        (_valid_frames(min(frames, 13)), min(steps, 6)),
        (9, min(steps, 4)),
    )
    profiles: list[tuple[int, int]] = []
    for candidate in candidates:
        if candidate not in profiles:
            profiles.append(candidate)
    return profiles


def _release_process_memory() -> None:
    import gc
    gc.collect()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


def _load():
    import torch
    from diffusers import CogVideoXPipeline
    if not torch.cuda.is_available():
        raise RuntimeError("Local text-to-video requires a CUDA GPU. In Colab select Runtime → Change runtime type → T4 GPU.")
    _release_process_memory()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    model_id = env("LOCAL_VIDEO_MODEL") or "THUDM/CogVideoX-2b"
    pipe = CogVideoXPipeline.from_pretrained(model_id, torch_dtype=torch.float16, low_cpu_mem_usage=True)
    if hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_tiling"):
        pipe.vae.enable_tiling()
    if hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_slicing"):
        pipe.vae.enable_slicing()
    # Sequential offload keeps only one block on the T4. Model offload is the fallback.
    try:
        pipe.enable_sequential_cpu_offload()
        offload = "sequential"
    except Exception as exc:
        print(f"[video] sequential offload unavailable ({exc}); using model CPU offload", flush=True)
        pipe.enable_model_cpu_offload()
        offload = "model"
    free, total = torch.cuda.mem_get_info()
    print(f"[video] loaded {model_id} with {offload} CPU offload; GPU free {free / 1e9:.2f}/{total / 1e9:.2f} GiB", flush=True)
    return pipe, torch, model_id


# News-category visual sequences. These are illustrative B-roll, never claimed to be footage of the actual event.
VISUAL_SEQUENCES = {
    "world": [
        "Wide establishing shot of a major international city at dawn, neutral documentary camera, authentic street movement",
        "Journalists reviewing international dispatches in a newsroom, screens out of focus, candid professional atmosphere",
        "Wide shot of a diplomatic district with flags in the distance, no readable signage, neutral framing",
        "Cargo ships moving through an international port, realistic documentary footage style, no company logos",
        "Aerial view of a busy airport terminal and aircraft taxiing, global travel context, natural light",
    ],
    "politics": [
        "Exterior of a government building with journalists setting up cameras, no identifiable political figure",
        "Empty press briefing room before a news conference, microphones and podium, no party logos",
        "Wide shot of diplomats entering a conference venue from behind, faces not identifiable",
        "Legislative chamber seen from a distant wide angle, no readable signage, neutral documentary",
        "Journalists typing notes during a press briefing, close-up of notebooks without readable text",
    ],
    "technology": [
        "Close-up of a semiconductor wafer and precision equipment in a clean technology lab",
        "Engineers testing a robotics prototype in a modern research workspace, realistic documentary lighting",
        "Data center aisle with server racks and blinking status lights, slow tracking shot",
        "Researcher inspecting an AI computing workstation, screens blurred with no readable text",
        "Industrial robotic arms assembling electronic components, precise motion, cinematic macro details",
    ],
    "business": [
        "Busy financial district at the start of the business day, glass office towers and commuters",
        "Cargo containers being loaded at a commercial port, cranes moving in the distance",
        "Workers inspecting products on a modern factory production line, neutral documentary",
        "Close-up of currency notes being counted at a bank counter, no visible brand or exact financial claim",
        "Small business owner opening a shop at sunrise, authentic everyday commerce",
    ],
    "science": [
        "Scientists in a laboratory observing samples through a microscope, realistic instruments",
        "Large radio telescope dishes turning under a clear night sky, science documentary",
        "Spacecraft model and engineers in a mission-control environment, screens out of focus",
        "Research vessel moving through open ocean with instruments on deck",
        "Close-up of gloved hands handling a laboratory sample, safe and realistic procedure",
    ],
    "sports": [
        "Wide stadium shot before a major sporting event, crowd atmosphere, no visible team crests",
        "Athletes warming up on a track, cinematic slow tracking shot, no identifiable celebrity",
        "Football pitch seen from a high wide angle during play, no specific team branding",
        "Close-up of a referee preparing equipment before a match, documentary framing",
        "Fans watching a live sporting event on a large screen, faces not emphasized",
    ],
    "entertainment": [
        "Film production crew preparing lights on a soundstage, no celebrity likeness",
        "Concert venue before the show with stage lights warming up, no artist branding",
        "Museum visitors viewing a contemporary art exhibition, natural candid documentary",
        "Camera operators and editors working in a post-production suite, screens blurred",
        "Crowd entering a cultural festival venue, colorful but realistic documentary coverage",
    ],
    "health": [
        "Medical researchers working in a clinical laboratory, professional and non-sensational",
        "Public health professionals reviewing charts in a hospital conference room, text unreadable",
        "Doctor and nurse preparing medical equipment in a clean clinic, no identifiable patient",
        "Scientist examining a sample under laboratory lighting, realistic close-up",
        "Wide exterior of a modern hospital during daytime, no emergency sensationalism",
    ],
    "humanitarian": [
        "Relief workers sorting boxed supplies in a warehouse, dignified documentary framing",
        "Volunteers distributing water and essential goods in an organized aid center, no identifiable vulnerable faces",
        "Emergency response teams preparing equipment at a staging area, no graphic imagery",
        "Wide view of temporary shelters from a respectful distance, no identifiable individuals",
        "Aid trucks moving along a road toward a distribution point, realistic documentary style",
    ],
}
BASE_STYLE = (
    "premium photorealistic international news documentary B-roll, natural motion, accurate everyday objects, "
    "neutral non-partisan framing, realistic camera movement, vertical 9:16 composition, subtle film grain, "
    "natural color grade, no subtitles, no written text, no logos, no watermark, no fake news graphics, "
    "no fabricated quotes, no synthetic depiction presented as authentic footage of a specific real event"
)


def _scene_prompt(sentence: str, title: str, index: int) -> str:
    text = f"{title} {sentence}".lower()
    if any(k in text for k in ("انتخابات", "دولت", "پارلمان", "president", "election", "politic", "حکومت")):
        key = "politics"
    elif any(k in text for k in ("هوش مصنوعی", "فناوری", "تراشه", "technology", "artificial intelligence", "chip", "ربات")):
        key = "technology"
    elif any(k in text for k in ("اقتصاد", "بازار", "تورم", "business", "market", "economy", "شرکت")):
        key = "business"
    elif any(k in text for k in ("سلامت", "بیمارستان", "پزشکی", "health", "medical", "واکسن")):
        key = "health"
    elif any(k in text for k in ("ورزش", "فوتبال", "مسابقه", "sport", "football", "match", "المپیک")):
        key = "sports"
    elif any(k in text for k in ("علم", "فضا", "دانشمند", "science", "space", "research", "ناسا")):
        key = "science"
    elif any(k in text for k in ("فیلم", "موسیقی", "هنر", "فرهنگ", "entertainment", "movie", "music", "جشنواره")):
        key = "entertainment"
    elif any(k in text for k in ("کمک‌رسانی", "آوارگان", "بحران انسانی", "humanitarian", "relief", "زلزله", "سیل")):
        key = "humanitarian"
    else:
        key = "world"
    sequence = VISUAL_SEQUENCES[key]
    visual = sequence[index % len(sequence)]
    return f"{visual}. {BASE_STYLE}. Context: {title}. Illustrative B-roll only; do not imply this is actual footage of a specific event."
    

def generate_film(script: str, title: str, out_path: Path, kind: str = "short", seed: int = 110, scene_plan: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Generate clips from a durable scene plan and resume completed scenes when possible."""
    from diffusers.utils import export_to_video
    from app.local_ai import release_ollama_model
    from app.scene_plan import (
        atomic_write_json, completed_scene_indices, load_or_create_plan, mark_scene,
    )

    print("[video] unloading the language model before CogVideoX", flush=True)
    release_ollama_model()
    _release_process_memory()
    pipe, torch, model_id = _load()
    count = int(env("VIDEO_CLIPS_SHORT") or "3") if kind == "short" else int(env("VIDEO_CLIPS_LONG") or "12")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path = out_path.with_name("scene_plan.json")
    plan_kwargs = {
        "kind": kind,
        "duration_hint_seconds": float(env("VIDEO_DURATION_HINT_SECONDS") or (45 if kind == "short" else 240)),
    }
    if scene_plan:
        plan = load_or_create_plan(plan_path, script, title, scene_plan=scene_plan, **plan_kwargs)
    else:
        plan = load_or_create_plan(plan_path, script, title, scene_count=count, **plan_kwargs)
    # Prefer fewer scenes on T4 when a large authored plan arrives.
    if kind == "short" and len(plan.get("scenes") or []) > count:
        plan["scenes"] = plan["scenes"][:count]
        for idx, scene in enumerate(plan["scenes"]):
            scene["index"] = idx
    clips_dir = out_path.parent / "scene_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    # Conservative T4 defaults.
    steps = max(1, int(env("VIDEO_STEPS") or "8"))
    frames = _valid_frames(int(env("VIDEO_FRAMES") or "17"))
    completed = completed_scene_indices(plan)

    try:
        for scene in plan["scenes"]:
            i = int(scene["index"])
            clip = clips_dir / f"{scene['scene_id']}.mp4"
            if i in completed and clip.exists() and clip.stat().st_size > 1024:
                print(f"[video] resume: reusing {scene['scene_id']}", flush=True)
                continue
            sentence = str(scene["spoken_text"])
            # Always prefer curated English visual direction; ignore low-quality Persian LLM prompts.
            prompt = _scene_prompt(sentence, title, i)
            scene["visual_prompt"] = prompt
            mark_scene(plan, i, status="running", clip_path=str(clip), error=None)
            atomic_write_json(plan_path, plan)
            print(f"[video] scene {i + 1}/{len(plan['scenes'])}: {prompt[:180]}", flush=True)
            try:
                import threading
                render_profiles = render_attempt_profiles(frames, steps)
                last_error = None
                for attempt, (attempt_frames, attempt_steps) in enumerate(render_profiles, start=1):
                    try:
                        print(
                            f"[video] render attempt {attempt}/{len(render_profiles)} "
                            f"(frames={attempt_frames}, steps={attempt_steps})",
                            flush=True,
                        )
                        stop_beat = threading.Event()

                        def _beat(label: str = f"scene {i + 1} attempt {attempt}", event: threading.Event = stop_beat) -> None:
                            elapsed = 0
                            while not event.wait(15):
                                elapsed += 15
                                print(f"[video] {label} still running ({elapsed}s)", flush=True)

                        beater = threading.Thread(target=_beat, daemon=True)
                        beater.start()
                        try:
                            result = pipe(
                                prompt=prompt,
                                num_videos_per_prompt=1,
                                num_inference_steps=attempt_steps,
                                num_frames=attempt_frames,
                                guidance_scale=float(env("VIDEO_GUIDANCE") or "6"),
                                generator=torch.Generator(device="cpu").manual_seed(seed + i + attempt),
                            )
                        finally:
                            stop_beat.set()
                            beater.join(timeout=1)
                        export_to_video(result.frames[0], str(clip), fps=8)
                        del result
                        if not clip.exists() or clip.stat().st_size <= 1024:
                            raise RuntimeError("Generated clip is missing or unexpectedly small")
                        last_error = None
                        break
                    except RuntimeError as exc:
                        last_error = exc
                        message = str(exc).lower()
                        is_memory_error = (
                            "out of memory" in message
                            or "cuda error: out of memory" in message
                            or "cudnn_status_alloc_failed" in message
                        )
                        print(
                            f"[video] render attempt failed: {type(exc).__name__}: {str(exc)[:1200]}",
                            flush=True,
                        )
                        if not is_memory_error or attempt >= len(render_profiles):
                            raise
                        print("[video] GPU memory pressure detected; clearing cache and retrying smaller.", flush=True)
                    finally:
                        if "result" in locals():
                            del result
                        _release_process_memory()
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                if last_error is not None:
                    raise last_error
                mark_scene(plan, i, status="complete", clip_path=str(clip), error=None)
                atomic_write_json(plan_path, plan)
            except Exception as exc:
                mark_scene(plan, i, status="failed", clip_path=str(clip), error=repr(exc))
                atomic_write_json(plan_path, plan)
                print("[video] FATAL scene render error:", repr(exc), flush=True)
                raise

        clip_paths = [Path(scene["clip_path"] or "") for scene in plan["scenes"]]
        missing = [str(path) for path in clip_paths if not path.exists() or path.stat().st_size <= 1024]
        if missing:
            raise RuntimeError("Scene plan has missing completed clips: " + ", ".join(missing))
        concat = out_path.parent / "scene_concat.txt"
        concat.write_text(
            "\n".join("file '" + p.resolve().as_posix().replace("'", "'\\''") + "'" for p in clip_paths),
            encoding="utf-8",
        )
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=24",
            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            str(out_path)
        ], check=True, capture_output=True)
    except Exception:
        atomic_write_json(plan_path, plan)
        raise
    return {
        "video_path": str(out_path), "provider": "cogvideox-colab-gpu", "model": model_id,
        "clips": len(plan["scenes"]), "scene_mapping": "scene_plan_v1",
        "scene_plan_path": str(plan_path), "resumable": True, "output_fps": 24, "ok": True,
    }
