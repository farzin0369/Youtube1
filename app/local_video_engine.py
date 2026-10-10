"""Local text-to-video film engine using CogVideoX text-to-video.
Scene prompts are mapped from the narration's meaning, not pasted as raw Persian text.
"""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from app.utils import env, split_sentences


def _load():
    import torch
    from diffusers import CogVideoXPipeline
    if not torch.cuda.is_available():
        raise RuntimeError("Local text-to-video requires a CUDA GPU. In Colab select Runtime → Change runtime type → T4 GPU.")
    model_id = env("LOCAL_VIDEO_MODEL") or "THUDM/CogVideoX-2b"
    pipe = CogVideoXPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    if hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_tiling"):
        pipe.vae.enable_tiling()
    return pipe, torch, model_id


# Short visual sequences keyed to the meaning of the spoken Persian narration.
# The prompts are English because the video model follows English visual direction more reliably.
VISUAL_SEQUENCES = {
    "kindness": [
        "A young adult gently helping an elderly man cross a quiet street, natural respectful interaction, close-up of a supportive hand, golden-hour cinematic documentary",
        "A woman placing a warm meal into the hands of a person in need, humble community kitchen, genuine kindness, realistic faces and hands",
        "A friend sitting beside a distressed person on a park bench and listening with compassion, subtle reassuring gesture, natural light",
        "A neighbor carrying grocery bags upstairs for an elderly neighbor, candid human moment, handheld documentary camera",
        "Several people from different backgrounds sharing food at a community table, warm sunlight, sincere smiles, realistic cinematic film",
        "A person quietly leaving groceries at a struggling family's doorstep and walking away, compassionate understated action",
        "A child offering water to a tired worker on a hot day, close-up of the exchange, natural documentary realism",
        "Two people reconciling after a disagreement with a sincere handshake and gentle smile, peaceful atmosphere",
    ],
    "patience": [
        "A person waiting calmly beside a hospital garden window, breathing slowly, soft morning light, quiet cinematic documentary",
        "A gardener carefully tending a small plant in rich soil, close-up of patient hands, sunlight and shallow depth of field",
        "A craftsperson patiently repairing a handmade object at a wooden workbench, detailed hands, calm warm light",
        "A person walking slowly through a rain-soaked city street without rushing, reflective mood, cinematic tracking shot",
        "A farmer waiting beside a field at sunrise, wind moving the crops, wide peaceful landscape shot",
        "A person listening attentively during a difficult conversation instead of interrupting, realistic subtle expressions",
    ],
    "gratitude": [
        "Sunlight falling across a simple breakfast table as hands gently pour tea, quiet everyday gratitude, cinematic close-up",
        "A person opening curtains to a beautiful sunrise and pausing in quiet appreciation, natural realistic film",
        "A family sharing a modest meal together, grateful smiles and gentle conversation, warm documentary style",
        "Hands watering a small garden after rain, sparkling droplets and new leaves, contemplative cinematic macro shot",
        "A person thanking a street cleaner with a sincere smile and respectful nod, authentic everyday kindness",
        "A wide sunrise over a peaceful landscape, soft golden light, slow cinematic camera movement",
    ],
    "honesty": [
        "A shopkeeper returning a lost wallet to its relieved owner in a busy market, sincere eye contact, documentary realism",
        "A worker openly admitting a mistake to a colleague and taking responsibility, calm respectful conversation",
        "A person carefully counting change and returning the extra coins to a customer, close-up on hands",
        "Two colleagues discussing a difficult decision honestly at a simple table, natural light, realistic expressions",
        "A person finding a dropped envelope and handing it back to its owner on a city sidewalk",
    ],
    "forgiveness": [
        "Two old friends meeting after a long disagreement, one offers a sincere apology, the other listens and softens, realistic cinematic scene",
        "A person taking a deep breath and choosing not to argue during a tense conversation, restrained natural acting",
        "Two family members reconciling at a doorway with a gentle embrace, warm natural light, documentary realism",
        "A person walking away from a heated argument into a peaceful garden, reflective slow tracking shot",
    ],
    "charity": [
        "Volunteers carefully packing fresh food into paper bags at a community aid center, teamwork, cinematic documentary",
        "A volunteer handing a warm blanket to a person sleeping outdoors on a cold evening, respectful framing, no sensationalism",
        "Hands placing bread, fruit and water into a donation box at a neighborhood center, close-up, natural light",
        "A group of neighbors distributing food parcels to families with dignity and warmth, realistic documentary film",
    ],
    "faith": [
        "A solitary person walking at dawn through a quiet stone courtyard, sunlight entering through arches, contemplative spiritual mood",
        "Close-up of hands resting peacefully on a wooden table beside a small beam of sunlight, quiet reflective moment",
        "A wide landscape at sunrise with birds distant in the sky, gentle wind across grasses, reverent cinematic documentary",
        "An empty historic stone courtyard with intricate geometric architecture, warm light and long shadows, no readable text",
    ],
}
BASE_STYLE = (
    "photorealistic premium cinematic documentary, natural human motion, anatomically correct hands, "
    "authentic candid behavior, realistic skin and fabric, subtle film grain, soft volumetric golden light, "
    "shallow depth of field when appropriate, slow controlled dolly or tracking camera, vertical 9:16 composition, "
    "consistent warm-neutral color grade, no subtitles, no written text, no logos, no watermark, "
    "no fantasy effects, no cartoon, no slideshow, no depiction of prophets or sacred faces"
)


def _scene_prompt(sentence: str, title: str, index: int) -> str:
    text = f"{title} {sentence}".lower()
    if any(k in text for k in ("مهربان", "رحمت", "محبت", " kindness")):
        key = "kindness"
    elif any(k in text for k in ("صبر", "شکیب", "تحمل", "صبور", "patience")):
        key = "patience"
    elif any(k in text for k in ("شکر", "سپاس", "نعمت", " gratitude")):
        key = "gratitude"
    elif any(k in text for k in ("راستی", "صداقت", "امانت", "دروغ", "honest")):
        key = "honesty"
    elif any(k in text for k in ("بخش", "گذشت", "عفو", " forgiveness")):
        key = "forgiveness"
    elif any(k in text for k in ("کمک", "نیازمند", "بخشش", "انفاق", " charity")):
        key = "charity"
    elif any(k in text for k in ("خدا", "ایمان", "معنوی", "قرآن", "امام علی", "توحید", " faith")):
        key = "faith"
    else:
        key = "faith"
    sequence = VISUAL_SEQUENCES[key]
    visual = sequence[index % len(sequence)]
    return f"{visual}. {BASE_STYLE}. This scene visually expresses the narration theme: {title}. Avoid literal text in the frame."


def generate_film(script: str, title: str, out_path: Path, kind: str = "short", seed: int = 110, scene_plan: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Generate clips from a durable scene plan and resume completed scenes when possible."""
    from diffusers.utils import export_to_video
    from app.scene_plan import (
        atomic_write_json, completed_scene_indices, load_or_create_plan, mark_scene,
    )

    pipe, torch, model_id = _load()
    count = int(env("VIDEO_CLIPS_SHORT") or "6") if kind == "short" else int(env("VIDEO_CLIPS_LONG") or "60")
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
    clips_dir = out_path.parent / "scene_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    steps = max(1, int(env("VIDEO_STEPS") or "25"))
    frames = max(9, int(env("VIDEO_FRAMES") or "49"))
    completed = completed_scene_indices(plan)

    try:
        for scene in plan["scenes"]:
            i = int(scene["index"])
            clip = clips_dir / f"{scene['scene_id']}.mp4"
            if i in completed and clip.exists() and clip.stat().st_size > 1024:
                print(f"[video] resume: reusing {scene['scene_id']}", flush=True)
                continue
            sentence = str(scene["spoken_text"])
            authored_prompt = str(scene.get("visual_prompt") or "").strip()
            prompt = f"{authored_prompt or _scene_prompt(sentence, title, i)}. {BASE_STYLE}. Directly visualize this narration meaning: {sentence}. Avoid unrelated imagery."
            scene["visual_prompt"] = prompt
            mark_scene(plan, i, status="running", clip_path=str(clip), error=None)
            atomic_write_json(plan_path, plan)
            print(f"[video] scene {i + 1}/{len(plan['scenes'])}: {prompt[:180]}", flush=True)
            try:
                result = pipe(
                    prompt=prompt,
                    num_videos_per_prompt=1,
                    num_inference_steps=steps,
                    num_frames=frames,
                    guidance_scale=float(env("VIDEO_GUIDANCE") or "6"),
                    generator=torch.Generator(device="cuda").manual_seed(seed + i),
                )
                export_to_video(result.frames[0], str(clip), fps=8)
                del result
                if not clip.exists() or clip.stat().st_size <= 1024:
                    raise RuntimeError("Generated clip is missing or unexpectedly small")
                mark_scene(plan, i, status="complete", clip_path=str(clip), error=None)
                atomic_write_json(plan_path, plan)
            except Exception as exc:
                mark_scene(plan, i, status="failed", clip_path=str(clip), error=repr(exc))
                atomic_write_json(plan_path, plan)
                raise
            finally:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

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
