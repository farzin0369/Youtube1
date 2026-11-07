#!/usr/bin/env python3
"""
BAMO → OpenMontage adapter
--------------------------
Takes a validated English idea from the idea bank and prepares an
OpenMontage-compatible project structure + brief for vertical Shorts.

This does NOT replace the OpenMontage agent. It prepares the inputs so
an agent (or a future autonomous runner) can drive the pipeline cleanly.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IDEAS_PATH = ROOT / "data" / "ideas" / "ideas.jsonl"
OUTPUT_ROOT = ROOT / "output" / "openmontage_projects"


def load_idea(idea_id: str | None = None) -> dict[str, Any]:
    if not IDEAS_PATH.exists():
        raise FileNotFoundError(f"Idea bank not found: {IDEAS_PATH}")
    ideas = []
    with IDEAS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ideas.append(json.loads(line))
    if not ideas:
        raise RuntimeError("Idea bank is empty")
    if idea_id:
        for idea in ideas:
            if idea.get("id") == idea_id:
                return idea
        raise KeyError(f"Idea not found: {idea_id}")
    # Prefer available ideas with highest virality
    available = [i for i in ideas if i.get("status") == "available"]
    if not available:
        available = ideas
    available.sort(key=lambda x: float(x.get("virality_score", 0)), reverse=True)
    return available[0]


def build_project_brief(idea: dict[str, Any]) -> dict[str, Any]:
    return {
        "brand": "BAMO",
        "handle": "@12bamo",
        "language": "en-US",
        "format": "youtube_shorts",
        "aspect_ratio": "9:16",
        "resolution": "1080x1920",
        "target_duration_seconds": idea.get("duration_seconds", 25),
        "pipeline_hint": "animated-explainer",  # or hybrid / short-form guided
        "idea_id": idea["id"],
        "title": idea.get("title"),
        "hook": idea.get("hook"),
        "narration": idea.get("narration"),
        "on_screen_text": idea.get("on_screen_text", []),
        "scenes": idea.get("scenes", []),
        "youtube_title": idea.get("youtube_title"),
        "youtube_description": idea.get("youtube_description"),
        "hashtags": idea.get("hashtags", []),
        "sources": idea.get("sources", []),
        "music_suggestion": idea.get("music_suggestion"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "constraints": {
            "no_persian_spiritual_content": True,
            "prefer_free_local_tools": True,
            "human_approval_default": False,  # experimental autonomous mode
            "vertical_only": True,
        },
    }


def write_project(idea: dict[str, Any], out_dir: Path | None = None) -> Path:
    brief = build_project_brief(idea)
    project_name = f"{idea['id']}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    project_dir = (out_dir or OUTPUT_ROOT) / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    (project_dir / "brief.json").write_text(
        json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (project_dir / "narration.txt").write_text(
        str(idea.get("narration", "")).strip() + "\n", encoding="utf-8"
    )
    (project_dir / "README.md").write_text(
        f"# OpenMontage project — {idea.get('title')}\n\n"
        f"Brand: BAMO · Handle: @12bamo\n"
        f"Idea ID: {idea['id']}\n\n"
        f"## Next steps for the agent\n\n"
        f"1. Read `vendor/openmontage/AGENT_GUIDE.md`\n"
        f"2. Run preflight and select pipeline (recommended: animated-explainer or hybrid)\n"
        f"3. Enforce vertical 1080x1920 and English narration\n"
        f"4. Prefer free/local tools; do not invent sources\n"
        f"5. Produce and inspect a real MP4 before claiming success\n",
        encoding="utf-8",
    )
    return project_dir


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    idea_id = argv[0] if argv else None
    idea = load_idea(idea_id)
    project_dir = write_project(idea)
    print(json.dumps({"ok": True, "project_dir": str(project_dir), "idea_id": idea["id"], "title": idea.get("title")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
