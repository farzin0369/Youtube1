"""BAMO Brain — metacognition and self-score (not AGI).

Aggregates heal health, council gates, render evidence, and research notes
into a single 0..100 self-score. Autonomous publish is allowed only when
score == 100 AND operator env gates are open.

This module never executes arbitrary cloned code and never scrapes the web
without an explicit offline/research note pipeline.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state" / "autopilot"
STATE.mkdir(parents=True, exist_ok=True)
RESEARCH = ROOT / "state" / "research"
RESEARCH.mkdir(parents=True, exist_ok=True)

# Publish autonomy requires perfect self-score by policy.
PUBLISH_SCORE_REQUIRED = int(os.getenv("BAMO_BRAIN_PUBLISH_SCORE", "100"))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def assess() -> dict[str, Any]:
    """Compute self-score from real artifacts, not vibes."""
    components: dict[str, float] = {}
    notes: list[str] = []

    # 1) Heal rules present and director compiles (via last cycle / files)
    rules = _read_json(ROOT / "app" / "bamo_heal_rules.json")
    rule_count = len(rules.get("rules") or [])
    components["heal_rules"] = min(20.0, 5.0 + rule_count * 2.0)
    notes.append(f"heal_rules={rule_count}")

    # 2) Council gates
    pre = _read_json(STATE / "last_council_preflight.json")
    post = _read_json(STATE / "last_council_post_render.json")
    council_pts = 0.0
    if pre.get("gate") == "PASS":
        council_pts += 20.0
    elif pre.get("gate") == "SKIPPED":
        council_pts += 5.0
    elif pre.get("gate") == "BLOCKED":
        council_pts += 0.0
        notes.append("council_preflight_BLOCKED")
    else:
        council_pts += 2.0
        notes.append("council_preflight_missing")
    if post.get("gate") == "PASS":
        council_pts += 20.0
    elif post.get("gate") in {None, ""}:
        council_pts += 0.0
        notes.append("council_post_missing")
    elif post.get("gate") == "BLOCKED":
        notes.append("council_post_BLOCKED")
    components["council"] = council_pts

    # 3) Render evidence 1080x1920
    evidence = _read_json(ROOT / "output" / "bamo-3d-smoke" / "smoke-evidence.json")
    render_pts = 0.0
    if evidence.get("video_width") == 1080 and evidence.get("video_height") == 1920:
        render_pts += 15.0
        notes.append("render_1080x1920")
    if (evidence.get("visual_plans") or evidence.get("ok")):
        render_pts += 10.0
    video = ROOT / "output" / "bamo-3d-smoke" / "video.mp4"
    if video.is_file() and video.stat().st_size > 100_000:
        render_pts += 10.0
        notes.append(f"video_bytes={video.stat().st_size}")
    components["render"] = min(35.0, render_pts)

    # 4) Research notes (continuous learning log)
    research_files = list(RESEARCH.glob("*.json"))
    components["research"] = min(15.0, float(len(research_files) * 3))
    notes.append(f"research_notes={len(research_files)}")

    # 5) Autopilot cycle freshness
    last_cycle = _read_json(STATE / "last_cycle.json")
    components["cycle"] = 10.0 if last_cycle else 0.0

    total = round(sum(components.values()), 1)
    total = max(0.0, min(100.0, total))
    publish_ready = total >= PUBLISH_SCORE_REQUIRED and all(
        [
            pre.get("gate") == "PASS" or post.get("gate") == "PASS",
            components["render"] >= 25.0,
        ]
    )
    report = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "score": total,
        "components": components,
        "notes": notes,
        "publish_score_required": PUBLISH_SCORE_REQUIRED,
        "publish_ready_by_brain": publish_ready,
        "honest_limits": {
            "is_agi": False,
            "studies_all_github": False,
            "auto_merges_foreign_code": False,
            "second_by_second": False,
            "million_subs_guaranteed": False,
        },
    }
    (STATE / "brain_score.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def write_research_note(topic: str, findings: list[str], sources: list[str] | None = None) -> Path:
    """Append a structured research note (no code execution from sources)."""
    note = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "topic": topic,
        "findings": findings,
        "sources": sources or [],
        "policy": "notes_only_no_auto_merge",
    }
    path = RESEARCH / f"note_{int(time.time())}.json"
    path.write_text(json.dumps(note, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def seed_baseline_research() -> list[str]:
    """Seed high-signal motion-graphics research directions (offline, curated)."""
    written: list[str] = []
    seeds = [
        (
            "cinematic_camera",
            [
                "Prefer multi-point Catmull-Rom paths over linear A→B moves",
                "Keep DOF aperture in 2.8–5.6 range for readable subjects",
                "Micro handheld shake must stay deterministic for CI reproducibility",
            ],
            ["internal:bamo_blender_primitives", "practice:film_camera_language"],
        ),
        (
            "vertical_shorts_packaging",
            [
                "Hook text in first 1s; avoid delayed branding",
                "1080x1920 native; do not upscale soft 720 previews for publish",
                "One visual thesis per scene matching narration clause",
            ],
            ["internal:bamo_production_renderer", "practice:shorts_retention"],
        ),
        (
            "self_heal_policy",
            [
                "Only regex/multi_replace/collapse repairs with compile verify",
                "Never eval model-written patches",
                "Promote successful repairs into bamo_heal_rules.json",
            ],
            ["internal:bamo_heal_engine"],
        ),
    ]
    if list(RESEARCH.glob("note_*.json")):
        return written
    for topic, findings, sources in seeds:
        path = write_research_note(topic, findings, sources)
        written.append(str(path.relative_to(ROOT)))
    return written
