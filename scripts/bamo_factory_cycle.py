#!/usr/bin/env python3
"""One factory cycle: research → script → domain/procedural scene → TTS → render → QA.

Does not upload to YouTube unless brain score is 100 and env gates are open.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.bamo_factory_bus import (
    agent_note,
    is_duplicate_topic,
    new_job,
    remember_content,
    set_status,
)
from app.bamo_brain import assess, seed_baseline_research


# Curated seed topics for autonomous selection when research APIs are offline.
SEED_TOPICS = [
    {
        "topic": "بیضی و دو کانون",
        "domain": "mathematics",
        "spoken_text": "در یک بیضی، مجموع فاصله هر نقطه تا دو کانون همیشه ثابت می‌ماند.",
        "visual_query": "3D ellipse with two foci and a moving point",
        "on_screen_text": "بیضی: مجموع دو فاصله ثابت است",
    },
    {
        "topic": "مولکول آب",
        "domain": "chemistry",
        "spoken_text": "در مولکول آب، دو اتم هیدروژن با پیوند به یک اتم اکسیژن وصل می‌شوند.",
        "visual_query": "three-dimensional water molecule H2O",
        "on_screen_text": "پیوند مولکول آب",
    },
    {
        "topic": "تداخل سازنده موج",
        "domain": "physics",
        "spoken_text": "وقتی دو موج هم‌فاز به هم می‌رسند، نوارهای روشن تداخل سازنده ساخته می‌شود.",
        "visual_query": "two wave sources constructive interference",
        "on_screen_text": "تداخل سازنده دو موج",
    },
]


def _pick_topic() -> dict:
    for item in SEED_TOPICS:
        if not is_duplicate_topic(item["topic"]):
            return item
    return SEED_TOPICS[0]


def main() -> int:
    seed_baseline_research()
    job = new_job("factory_cycle")
    agent_note(job, "operations", "cycle_started")

    # Research + editorial (offline-capable seed pool)
    pick = _pick_topic()
    agent_note(job, "research", "selected_seed_topic", topic=pick["topic"], domain=pick["domain"])
    if is_duplicate_topic(pick["topic"]):
        agent_note(job, "editorial", "duplicate_warning", topic=pick["topic"])
    job["topic"] = pick["topic"]
    job["script"] = pick["spoken_text"]
    job["scenes"] = [{
        "spoken_text": pick["spoken_text"],
        "visual_query": pick["visual_query"],
        "on_screen_text": pick["on_screen_text"],
        "domain": pick["domain"],
    }]
    agent_note(job, "scriptwriter", "script_locked", length=len(pick["spoken_text"]))
    agent_note(job, "fact_checker", "seed_scientific_topic_accepted", domain=pick["domain"])
    set_status(job, "scripted")

    # Scene graph via director (LLM or procedural domain)
    from app.bamo_ai_director import direct_scene

    try:
        plan = direct_scene(
            narration=pick["spoken_text"],
            visual_brief=pick["visual_query"],
            overlay=pick["on_screen_text"],
            duration_seconds=6.0,
            story_context=pick["spoken_text"],
        )
        job["scene_graphs"] = [plan]
        agent_note(
            job,
            "motion_director",
            "scene_graph_ready",
            matched_by=plan.get("matched_by"),
            provider=plan.get("provider"),
            objects=len(plan.get("objects") or []),
        )
        set_status(job, "directed")
    except Exception as exc:  # noqa: BLE001
        job["errors"].append(f"director:{exc}")
        agent_note(job, "operations", "director_failed", error=str(exc))
        set_status(job, "failed_director")
        print(json.dumps(job, ensure_ascii=False, indent=2))
        return 1

    agent_note(job, "art_director", "palette_locked", palette=(plan.get("palette") or {}))

    # Voice
    out = ROOT / "output" / "factory" / job["id"]
    out.mkdir(parents=True, exist_ok=True)
    audio = out / "voice.mp3"
    captions = out / "captions.srt"
    try:
        from app.spiritual_tts import synthesize_with_captions

        tts = synthesize_with_captions(
            pick["spoken_text"],
            audio,
            captions,
            scenes=[{
                "spoken_text": pick["spoken_text"],
                "on_screen_text": pick["on_screen_text"],
            }],
        )
        if not tts.get("ok"):
            raise RuntimeError(f"tts_failed:{tts}")
        job["audio_path"] = str(audio)
        agent_note(job, "voice_audio", "tts_ok", provider=tts.get("provider"), voice=tts.get("voice"))
        set_status(job, "voiced")
    except Exception as exc:  # noqa: BLE001
        job["errors"].append(f"tts:{exc}")
        agent_note(job, "operations", "tts_failed", error=str(exc))
        set_status(job, "failed_tts")
        print(json.dumps({"id": job["id"], "status": job["status"], "errors": job["errors"]}, ensure_ascii=False))
        return 1

    # Render
    try:
        from app.bamo_motion_engine import render_project

        project = {
            "format": "short",
            "fps": 24,
            "scenes": [{
                "duration": 6.0,
                "text": pick["on_screen_text"],
                "narration": pick["spoken_text"],
                "visual_prompt": pick["visual_query"],
                "scene_graph": {
                    k: plan[k]
                    for k in ("camera", "palette", "objects", "relationships", "visual_thesis")
                    if k in plan
                },
            }],
        }
        video = render_project(project, out / "video.mp4", audio=audio)
        job["video_path"] = str(video)
        agent_note(job, "video_production", "render_ok", bytes=video.stat().st_size)
        set_status(job, "rendered")
    except Exception as exc:  # noqa: BLE001
        job["errors"].append(f"render:{exc}")
        agent_note(job, "operations", "render_failed", error=str(exc))
        set_status(job, "failed_render")
        print(json.dumps({"id": job["id"], "status": job["status"], "errors": job["errors"]}, ensure_ascii=False))
        return 1

    # QA score (structural; vision QA still required for production claim)
    score = 0
    breakdown = {}
    if job.get("scene_graphs"):
        breakdown["semantic_plan"] = 20
        score += 20
    if Path(job["video_path"]).stat().st_size > 50_000:
        breakdown["file_health"] = 5
        score += 5
    if job.get("audio_path") and Path(job["audio_path"]).stat().st_size > 5_000:
        breakdown["audio"] = 10
        score += 10
    if plan.get("matched_by") in {"semantic_ai_director", "procedural_domain_author"}:
        breakdown["motion_authorship"] = 20
        score += 20
    breakdown["camera"] = 10 if plan.get("camera") else 0
    score += breakdown["camera"]
    breakdown["non_duplicate"] = 10 if not is_duplicate_topic(pick["topic"], threshold_tokens=5) else 0
    score += breakdown["non_duplicate"]
    # Remaining points reserved for frame vision / scientific QA (not claimed here)
    breakdown["reserved_vision_science"] = 0
    job["qa_score"] = score
    job["qa_breakdown"] = breakdown
    agent_note(job, "quality_assurance", "scored", score=score, breakdown=breakdown)
    if score < 100:
        set_status(job, "qa_hold")
        agent_note(job, "operations", "hold_below_100", score=score)
    else:
        set_status(job, "qa_pass")

    remember_content({"topic": pick["topic"], "title": pick["on_screen_text"], "job_id": job["id"]})
    brain = assess()
    agent_note(job, "operations", "brain_assessed", brain_score=brain.get("score"), publish_ready=brain.get("publish_ready_by_brain"))

    print(json.dumps({
        "job_id": job["id"],
        "status": job["status"],
        "qa_score": score,
        "qa_breakdown": breakdown,
        "video_path": job.get("video_path"),
        "matched_by": plan.get("matched_by"),
        "brain_score": brain.get("score"),
        "publish_ready_by_brain": brain.get("publish_ready_by_brain"),
    }, ensure_ascii=False, indent=2))
    return 0 if job["status"] in {"qa_hold", "qa_pass", "rendered"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
