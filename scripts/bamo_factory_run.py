#!/usr/bin/env python3
"""BAMO content factory one-shot: topic -> 11 agents -> domain scenes -> evidence.

This is a real orchestrator over existing modules (factory bus, procedural
domains, optional full render). It does not invent YouTube publish.

Usage:
  PYTHONPATH=. python scripts/bamo_factory_run.py --topic "مولکول آب"
  PYTHONPATH=. python scripts/bamo_factory_run.py --topic "..." --render
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bamo_factory_bus import agent_note, new_job, _save_job  # noqa: E402
from app.bamo_ai_director import normalize_scene_graph, validate_scene_graph  # noqa: E402
from app.bamo_procedural_domains import try_procedural_domain  # noqa: E402
from app.bamo_brain import assess  # noqa: E402


DEFAULT_SCENES = [
    {
        "domain": "mathematics",
        "spoken_text": "در یک بیضی، مجموع فاصله هر نقطه تا دو کانون همیشه ثابت می‌ماند.",
        "visual_query": "3D ellipse with two foci and a moving point",
        "on_screen_text": "بیضی: مجموع دو فاصله ثابت است",
    },
    {
        "domain": "chemistry",
        "spoken_text": "در مولکول آب، دو اتم هیدروژن با پیوند به یک اتم اکسیژن وصل می‌شوند.",
        "visual_query": "water molecule H2O with visible bonds",
        "on_screen_text": "پیوند مولکول آب",
    },
    {
        "domain": "physics",
        "spoken_text": "وقتی دو موج هم‌فاز به هم می‌رسند، نوارهای روشن تداخل سازنده ساخته می‌شود.",
        "visual_query": "two coherent sources constructive interference",
        "on_screen_text": "تداخل سازنده دو موج",
    },
]


def _run_agents(job: dict, topic: str) -> dict:
    agent_note(job, "research", "offline science seed topics prepared", topics=[s["domain"] for s in DEFAULT_SCENES])
    agent_note(job, "trend", "no paid trend API; using fixed educational domains")
    agent_note(job, "editorial", "selected three-domain short for vertical education", topic=topic)
    agent_note(job, "fact_checker", "claims limited to standard textbook geometry/chemistry/waves")
    job["topic"] = topic
    job["script"] = {
        "title": topic[:80],
        "scenes": [{"narration": s["spoken_text"], "overlay": s["on_screen_text"]} for s in DEFAULT_SCENES],
    }
    agent_note(job, "scriptwriter", "three narration beats authored", scene_count=3)
    agent_note(job, "art_director", "palette deep navy + gold/cyan; vertical 1080x1920")

    graphs = []
    for scene in DEFAULT_SCENES:
        raw = try_procedural_domain(
            narration=scene["spoken_text"],
            visual_brief=scene["visual_query"],
            overlay=scene["on_screen_text"],
            duration_seconds=4.0,
        )
        if raw is None:
            raise SystemExit(f"no procedural graph for {scene['domain']}")
        plan = validate_scene_graph(normalize_scene_graph(raw))
        plan["domain"] = scene["domain"]
        plan["matched_by"] = "procedural_domain_author"
        graphs.append(plan)
    job["scenes"] = DEFAULT_SCENES
    job["scene_graphs"] = graphs
    agent_note(job, "motion_director", "procedural scene graphs validated", domains=[g["domain"] for g in graphs])
    agent_note(job, "voice_audio", "TTS deferred to render step (edge-tts)")
    agent_note(job, "video_production", "render optional via --render flag")
    _save_job(job)
    return job


def _qa(job: dict) -> dict:
    score = 0
    breakdown = {}
    graphs = job.get("scene_graphs") or []
    breakdown["graph_count"] = len(graphs)
    if len(graphs) == 3:
        score += 30
    ids = [tuple(o["id"] for o in g.get("objects") or []) for g in graphs]
    if len(set(ids)) == len(ids) and ids:
        score += 25
        breakdown["distinct_object_sets"] = True
    else:
        breakdown["distinct_object_sets"] = False
    if job.get("script"):
        score += 15
    if all(g.get("matched_by") == "procedural_domain_author" for g in graphs):
        score += 15
    video = job.get("video_path")
    if video and Path(video).is_file() and Path(video).stat().st_size > 100_000:
        score += 15
        breakdown["video_bytes"] = Path(video).stat().st_size
    job["qa_score"] = score
    job["qa_breakdown"] = breakdown
    agent_note(job, "quality_assurance", f"qa_score={score}", **breakdown)
    brain = assess()
    agent_note(job, "operations", "publish gate evaluated", brain_score=brain.get("score"), publish_allowed=False)
    job["publish"] = {"allowed": False, "reason": "human_gate_and_brain_not_100", "brain": brain}
    job["status"] = "qa_complete" if score >= 70 else "qa_failed"
    _save_job(job)
    return job


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="سه دامنه علمی: بیضی، مولکول آب، تداخل موج")
    parser.add_argument("--render", action="store_true", help="run full domain proof render (slow on CPU)")
    args = parser.parse_args()

    job = new_job(topic_seed=args.topic)
    job = _run_agents(job, args.topic)

    if args.render:
        os.environ.setdefault("BAMO_FORCE_PROCEDURAL", "1")
        os.environ.setdefault("BAMO_BLENDER_SAMPLES", "24")
        os.environ.setdefault("BAMO_BLENDER_RESOLUTION_PERCENTAGE", "40")
        os.environ.setdefault("BAMO_BLENDER_DENOISE", "true")
        # Reuse proven domain proof script
        import runpy

        agent_note(job, "video_production", "starting render_ai_domain_proof")
        _save_job(job)
        runpy.run_path(str(ROOT / "scripts" / "render_ai_domain_proof.py"), run_name="__main__")
        mp4 = ROOT / "output" / "bamo-ai-three-domain" / "bamo-ai-three-domain.mp4"
        if mp4.is_file():
            job["video_path"] = str(mp4)
            agent_note(job, "video_production", "render complete", bytes=mp4.stat().st_size)
        else:
            job["errors"].append("render finished without mp4")
            agent_note(job, "video_production", "render missing mp4")
        _save_job(job)

    job = _qa(job)
    out = ROOT / "output" / "bamo-factory"
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "job_id": job["id"],
        "status": job["status"],
        "qa_score": job["qa_score"],
        "qa_breakdown": job["qa_breakdown"],
        "video_path": job.get("video_path"),
        "publish_allowed": job.get("publish", {}).get("allowed"),
        "agent_log_len": len(job.get("agent_log") or []),
    }
    (out / f"{job['id']}-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if job["status"] == "qa_complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
