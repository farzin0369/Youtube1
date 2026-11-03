#!/usr/bin/env python3
"""Render three AI-authored domain scenes with Blender. Not a public upload.

The scene graphs must come from app.bamo_ai_director.direct_scene. Predefined
motif builders are not an acceptable substitute for this proof.
"""
from __future__ import annotations

# vector-hardening companion run for truncated Qwen scene graphs

import json
import traceback
from pathlib import Path

from app.bamo_ai_director import direct_scene, ensure_distinct_camera_moves
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
        "visual_query": "3D ellipse with two foci, construction lines, and a moving point that keeps the sum of distances constant",
        "on_screen_text": "بیضی: مجموع دو فاصله ثابت است",
    },
    {
        "domain": "chemistry",
        "spoken_text": "در مولکول آب، دو اتم هیدروژن با پیوند به یک اتم اکسیژن وصل می‌شوند.",
        "visual_query": "three-dimensional water molecule, oxygen atom bonded to two hydrogen atoms, visible bonds",
        "on_screen_text": "پیوند مولکول آب",
    },
    {
        "domain": "physics",
        "spoken_text": "وقتی دو موج هم‌فاز به هم می‌رسند، نوارهای روشن تداخل سازنده ساخته می‌شود.",
        "visual_query": "two coherent wave sources, expanding wavefronts, and a visible constructive interference pattern",
        "on_screen_text": "تداخل سازنده دو موج",
    },
]

def _durations(timings: list[dict], audio_duration: float) -> list[float]:
    starts = [float(row["start_seconds"]) for row in timings]
    if len(starts) != len(SCENES) or starts[0] < 0 or any(b <= a for a, b in zip(starts, starts[1:])):
        raise SystemExit("TTS did not return one increasing timing per domain scene.")
    boundaries = starts[1:] + [audio_duration]
    durations = [end - start for start, end in zip(starts, boundaries)]
    if any(duration < 0.5 for duration in durations):
        raise SystemExit("A domain scene is shorter than 0.5 seconds.")
    return durations


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
            plan = direct_scene(
                narration=scene["spoken_text"],
                visual_brief=scene["visual_query"],
                overlay=scene["on_screen_text"],
                duration_seconds=duration,
                story_context=story,
                previous_visual_theses=prior_theses,
                previous_camera_moves=prior_cameras,
            )
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
    signatures = [
        (plan["domain"], tuple(obj["id"] for obj in plan["objects"]), plan["visual_thesis"], plan["camera"]["move"])
        for plan in plans
    ]
    if len({item[1] for item in signatures}) != len(plans):
        raise SystemExit("AI director repeated the same object set across domains.")
    if any(plan.get("matched_by") != "semantic_ai_director" for plan in plans):
        raise SystemExit("A scene did not come from the semantic AI director.")
    project = {
        "format": "short",
        "fps": 24,
        "scenes": [
            {
                "duration": duration,
                "text": scene["on_screen_text"],
                "narration": scene["spoken_text"],
                "visual_prompt": scene["visual_query"],
                "scene_graph": {key: plan[key] for key in ("camera", "palette", "objects", "relationships", "visual_thesis")},
            }
            for scene, duration, plan in zip(SCENES, durations, plans)
        ],
    }
    video = render_project(project, OUT / "bamo-ai-three-domain.mp4", audio=AUDIO)
    evidence = {
        "kind": "ai_authored_three_domain_proof",
        "not_predefined_motif_demo": True,
        "public_upload": False,
        "production_visuals_approved": False,
        "limitation": "Renderer still executes geometric primitives, bonds, lights and camera moves. It is not a character, organic, or photoreal engine.",
        "tts_provider": tts.get("provider"),
        "tts_voice": tts.get("voice"),
        "narration_seconds": tts.get("duration_seconds"),
        "video_path": str(video),
        "video_bytes": video.stat().st_size,
        "domains": [
            {
                "domain": plan["domain"],
                "provider": plan.get("provider"),
                "critic_provider": plan.get("critic_provider"),
                "semantic_review_score": plan.get("semantic_review_score"),
                "visual_thesis": plan.get("visual_thesis"),
                "camera": plan.get("camera"),
                "narration_exact": plan.get("narration_exact"),
                "overlay": scene["on_screen_text"],
                "object_ids": [obj["id"] for obj in plan["objects"]],
                "object_kinds": [obj["kind"] for obj in plan["objects"]],
            }
            for plan, scene in zip(plans, SCENES)
        ],
    }
    (OUT / "ai-domain-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)
    if video.stat().st_size < 100_000:
        raise SystemExit("AI domain proof MP4 is unexpectedly small.")


if __name__ == "__main__":
    main()
