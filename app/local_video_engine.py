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


# Short visual sequences keyed to the meaning of the spoken Persian narration.
# The prompts are English because the video model follows English visual direction more reliably.
VISUAL_SEQUENCES = {
    "kindness": [
        "Close-up of a supportive hand guiding an elderly person across a quiet street, golden-hour cinematic documentary, faces softly out of focus",
        "Hands placing a warm meal into another person's hands in a humble community kitchen, genuine kindness, realistic fabric and steam",
        "Two silhouettes sitting on a park bench at dusk, one listening with compassion, natural light, documentary realism",
        "A neighbor carrying grocery bags upstairs, candid human moment, handheld documentary camera, faces not identifiable",
        "Several people from different backgrounds sharing food at a community table, warm sunlight, respectful framing",
        "Someone quietly leaving groceries at a doorway and walking away, compassionate understated action",
        "A child offering water to a tired worker on a hot day, close-up of the exchange, natural documentary realism",
        "Two people reconciling with a sincere handshake, peaceful atmosphere, faces softly blurred",
    ],
    "patience": [
        "A person waiting calmly beside a hospital garden window, breathing slowly, soft morning light, quiet cinematic documentary",
        "A gardener carefully tending a small plant in rich soil, close-up of patient hands, sunlight and shallow depth of field",
        "A craftsperson patiently repairing a handmade object at a wooden workbench, detailed hands, calm warm light",
        "Someone walking slowly through a rain-soaked city street without rushing, reflective mood, cinematic tracking shot",
        "A farmer waiting beside a field at sunrise, wind moving the crops, wide peaceful landscape shot",
        "Hands resting still during a difficult conversation, restrained natural acting, soft interior light",
    ],
    "gratitude": [
        "Sunlight falling across a simple breakfast table as hands gently pour tea, quiet everyday gratitude, cinematic close-up",
        "Curtains opening to a beautiful sunrise and a quiet pause of appreciation, natural realistic film",
        "A modest family meal table with warm light and gentle conversation, documentary style, faces not centered",
        "Hands watering a small garden after rain, sparkling droplets and new leaves, contemplative cinematic macro shot",
        "A respectful nod toward a street cleaner at dawn, authentic everyday kindness, soft focus faces",
        "A wide sunrise over a peaceful landscape, soft golden light, slow cinematic camera movement",
    ],
    "honesty": [
        "A shopkeeper returning a lost wallet in a busy market, sincere gesture, documentary realism, faces soft",
        "A worker calmly admitting a mistake to a colleague, respectful conversation, natural office light",
        "Hands carefully counting change and returning extra coins, close-up on hands",
        "Two colleagues discussing a difficult decision at a simple table, natural light",
        "Someone finding a dropped envelope and handing it back on a city sidewalk",
    ],
    "forgiveness": [
        "Two old friends meeting after disagreement, one offers a sincere apology, soft cinematic light, faces not sacred or iconic",
        "A person taking a deep breath and choosing not to argue, restrained natural acting",
        "Family members reconciling at a doorway with a gentle embrace, warm natural light",
        "Someone walking away from tension into a peaceful garden, reflective slow tracking shot",
    ],
    "charity": [
        "Volunteers packing fresh food into paper bags at a community aid center, teamwork, cinematic documentary",
        "A volunteer handing a warm blanket outdoors on a cold evening, respectful framing, no sensationalism",
        "Hands placing bread, fruit and water into a donation box, close-up, natural light",
        "Neighbors distributing food parcels with dignity and warmth, realistic documentary film",
    ],
    "faith": [
        "A solitary figure walking at dawn through a quiet stone courtyard, sunlight through arches, contemplative spiritual mood, face not identifiable",
        "Close-up of hands resting peacefully on wood beside a small beam of sunlight, quiet reflective moment",
        "A wide landscape at sunrise with distant birds, gentle wind across grasses, reverent cinematic documentary",
        "An empty historic stone courtyard with intricate geometric architecture, warm light and long shadows, no readable text",
        "Symbolic lion silhouette on a desert ridge at golden hour, majestic and respectful, no human faces, cinematic wide shot",
        "Open book pages turning in soft wind under warm light, abstract spiritual mood, no sacred portraits",
    ],
}
BASE_STYLE = (
    "photorealistic premium cinematic documentary, natural human motion when people appear, anatomically correct hands, "
    "authentic candid behavior, realistic skin and fabric, subtle film grain, soft volumetric golden light, "
    "shallow depth of field when appropriate, slow controlled dolly or tracking camera, vertical 9:16 composition, "
    "consistent warm-neutral color grade, no subtitles, no written text, no logos, no watermark, "
    "no fantasy effects, no cartoon, no slideshow, no depiction of prophets or sacred faces, no religious iconography of holy figures"
)


def _scene_prompt(sentence: str, title: str, index: int) -> str:
    text = f"{title} {sentence}".lower()
    if any(k in text for k in ("مهربان", "رحمت", "محبت", "kindness")):
        key = "kindness"
    elif any(k in text for k in ("صبر", "شکیب", "تحمل", "صبور", "patience")):
        key = "patience"
    elif any(k in text for k in ("شکر", "سپاس", "نعمت", "gratitude")):
        key = "gratitude"
    elif any(k in text for k in ("راستی", "صداقت", "امانت", "دروغ", "honest")):
        key = "honesty"
    elif any(k in text for k in ("بخش", "گذشت", "عفو", "forgiveness")):
        key = "forgiveness"
    elif any(k in text for k in ("کمک", "نیازمند", "بخشش", "انفاق", "charity")):
        key = "charity"
    elif any(k in text for k in ("خدا", "ایمان", "معنوی", "قرآن", "امام علی", "توحید", "شیر", "faith")):
        key = "faith"
    else:
        key = "faith"
    sequence = VISUAL_SEQUENCES[key]
    visual = sequence[index % len(sequence)]
    return f"{visual}. {BASE_STYLE}. Theme: {title}. Avoid literal on-screen text."


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
