#!/usr/bin/env python3
"""Render three domain scenes (ellipse, water, interference) with Blender.

BAMO_FORCE_PROCEDURAL=1 uses procedural domain graphs only (CI-safe).
Otherwise uses direct_scene (LLM + procedural fallback after restore).
"""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

from app.bamo_ai_director import ensure_distinct_camera_moves, normalize_scene_graph, validate_scene_graph
from app.bamo_motion_engine import render_project
from app.spiritual_tts import synthesize_with_captions

OUT = Path("output/bamo-ai-three-domain")
OUT.mkdir(parents=True, exist_ok=True)
AUDIO = OUT / "voice-fa.mp3"
CAPTIONS = OUT / "captions.srt"

SCENES = [
    {
        "domain": "mathematics",
        "spoken_text": "در یک بیضی، مجموع فاصله هر نقطه تا دو کانون همیشه ثابت می‌ماند.",
        "visual_query": "3D ellipse with two foci, construction lines, and a moving point",
        "on_screen_text": "بیضی: مجموع دو فاصله ثابت است",
    },
    {
        "domain": "chemistry",
        "spoken_text": "در مولکول آب، دو اتم هیدروژن با پیوند به یک اتم اکسیژن وصل می‌شوند.",
        "visual_query": "three-dimensional water molecule H2O with visible bonds",
        "on_screen_text": "پیوند مولکول آب",
    },
    {
        "domain": "physics",
        "spoken_text": "وقتی دو موج هم‌فاز به هم می‌رسند، نوارهای روشن تداخل سازنده ساخته می‌شود.",
        "visual_query": "two coherent wave sources constructive interference",
        "on_screen_text": "تداخل سازنده دو موج",
    },
]

ALLOWED_MATCH = {"semantic_ai_director", "procedural_domain_author"}


def _durations(timings: list[dict], audio_duration: float) -> list[float]:
    starts = [float(row["start_seconds"]) for row in timings]
    if len(starts) != len(SCENES) or starts[0] < 0 or any(b <= a for a, b in zip(starts, starts[1:])):
        raise SystemExit("TTS did not return one increasing timing per domain scene.")
    boundaries = starts[1:] + [audio_duration]
    durations = [end - start for start, end in zip(starts, boundaries)]
    if any(duration < 0.5 for duration in durations):
        raise SystemExit("A domain scene is shorter than 0.5 seconds.")
    return durations


def _plan(scene: dict, duration: float, story: str, prior_theses: list, prior_cameras: list) -> dict:
    force = os.environ.get("BAMO_FORCE_PROCEDURAL", "").strip().lower() in {"1", "true", "yes", "on"}
    if force:
        from app.bamo_procedural_domains import try_procedural_domain

        raw = try_procedural_domain(
            narration=scene["spoken_text"],
            visual_brief=scene["visual_query"],
            overlay=scene["on_screen_text"],
            duration_seconds=duration,
        )
        if raw is None:
            raise SystemExit(f"no procedural plan for {scene['domain']}")
        plan = validate_scene_graph(normalize_scene_graph(raw))
        plan["matched_by"] = "procedural_domain_author"
        plan["provider"] = raw.get("provider", "procedural")
        plan["semantic_review_score"] = int(raw.get("semantic_review_score") or 90)
        plan["narration_exact"] = scene["spoken_text"]
        plan["visual_brief"] = scene["visual_query"]
        plan["overlay"] = scene["on_screen_text"]
        plan["duration_seconds"] = float(duration)
        plan["critic_provider"] = "skipped:forced_procedural"
        return plan

    from app.bamo_ai_director import direct_scene

    return direct_scene(
        narration=scene["spoken_text"],
        visual_brief=scene["visual_query"],
        overlay=scene["on_screen_text"],
        duration_seconds=duration,
        story_context=story,
        previous_visual_theses=prior_theses,
        previous_camera_moves=prior_cameras,
    )


def main() -> None:
    script = " ".join(scene["spoken_text"] for scene in SCENES)
    tts = synthesize_with_captions(script, AUDIO, CAPTIONS, scenes=SCENES)
    if not tts.get("ok") or tts.get("provider") not in {"edge-tts", "elevenlabs"}:
        raise SystemExit("Persian narration synthesis failed; refusing a silent proof.")
    if not AUDIO.exists() or AUDIO.stat().st_size < 8_000:
        raise SystemExit("Persian narration audio is missing or unexpectedly small.")
    from app.spiritual_video import probe_duration

    audio_duration = probe_duration(AUDIO)
    durations = _durations(tts.get("scene_timings") or [], audio_duration)
    story = " | ".join(scene["spoken_text"] for scene in SCENES)
    plans = []
    prior_theses: list[str] = []
    prior_cameras: list[str] = []
    try:
        for scene, duration in zip(SCENES, durations):
            plan = _plan(scene, duration, story, prior_theses, prior_cameras)
            plan["domain"] = scene["domain"]
            plans.append(plan)
            prior_theses.append(plan["visual_thesis"])
            prior_cameras.append(plan["camera"]["move"])
            (OUT / "ai-scene-graphs.json").write_text(
                json.dumps(plans, ensure_ascii=False, indent=2), encoding="utf-8",
            )
    except Exception:
        (OUT / "director-failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    ensure_distinct_camera_moves(plans)
    (OUT / "ai-scene-graphs.json").write_text(json.dumps(plans, ensure_ascii=False, indent=2), encoding="utf-8")
    if len({tuple(obj["id"] for obj in p["objects"]) for p in plans}) != len(plans):
        raise SystemExit("Director repeated the same object set across domains.")
    if any(p.get("matched_by") not in ALLOWED_MATCH for p in plans):
        raise SystemExit(f"Unexpected matched_by: {[p.get('matched_by') for p in plans]}")
    project = {
        "format": "short",
        "fps": 24,
        "scenes": [
            {
                "duration": duration,
                "text": scene["on_screen_text"],
                "narration": scene["spoken_text"],
                "visual_prompt": scene["visual_query"],
                "scene_graph": {
                    k: plan[k]
                    for k in ("camera", "palette", "objects", "relationships", "visual_thesis")
                },
            }
            for scene, duration, plan in zip(SCENES, durations, plans)
        ],
    }
    video = render_project(project, OUT / "bamo-ai-three-domain.mp4", audio=AUDIO)
    evidence = {
        "kind": "three_domain_scientific_proof",
        "public_upload": False,
        "forced_procedural": os.environ.get("BAMO_FORCE_PROCEDURAL", ""),
        "tts_provider": tts.get("provider"),
        "video_path": str(video),
        "video_bytes": video.stat().st_size,
        "domains": [
            {
                "domain": plan["domain"],
                "matched_by": plan.get("matched_by"),
                "provider": plan.get("provider"),
                "visual_thesis": plan.get("visual_thesis"),
                "object_ids": [o["id"] for o in plan["objects"]],
            }
            for plan in plans
        ],
    }
    (OUT / "ai-domain-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)
    if video.stat().st_size < 100_000:
        raise SystemExit("Domain proof MP4 is unexpectedly small.")


if __name__ == "__main__":
    main()
