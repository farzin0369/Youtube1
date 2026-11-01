#!/usr/bin/env python3
"""Run the 11-role BAMO production checklist, synthesize Persian narration and render MP4.

The 11 repository skills are role specifications, not 11 separately hosted LLMs.
This runner executes their production hand-offs deterministically and records each
role's deliverable. No paid model API or YouTube publishing is used.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from app.bamo_motion_engine import load_project, render_project

ROLE_KEYS = (
    "discovery", "strategy", "script_hook", "packaging", "seo",
    "production", "editing", "shorts", "chapters", "community", "analytics",
)


def validate_brief(brief: dict) -> None:
    missing = [key for key in ("title", "hook", "narration", "scenes", "roles") if not brief.get(key)]
    if missing:
        raise ValueError("Missing production brief fields: " + ", ".join(missing))
    roles = brief["roles"]
    if not isinstance(roles, dict) or set(roles) != set(ROLE_KEYS):
        raise ValueError("Exactly the 11 documented BAMO role hand-offs are required")
    if len(brief["scenes"]) != 4:
        raise ValueError("The first BAMO short must contain exactly four authored scenes")
    for key in ROLE_KEYS:
        if not str(roles[key]).strip():
            raise ValueError(f"Role {key} has no recorded deliverable")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--output-dir", default="output/bamo/first-film")
    parser.add_argument("--voice", default="fa-IR-FaridNeural")
    args = parser.parse_args()

    brief_path = Path(args.brief)
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    validate_brief(brief)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    project = {
        "format": "short",
        "fps": 24,
        "scenes": brief["scenes"],
    }
    project_path = out_dir / "motion_project.json"
    project_path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")

    narration_path = out_dir / "narration.mp3"
    if not shutil.which("edge-tts") and not _module_available("edge_tts"):
        raise RuntimeError("edge-tts is not installed; install it before rendering narration")
    command = [
        sys.executable, "-m", "edge_tts", "--voice", args.voice,
        "--text", brief["narration"], "--write-media", str(narration_path),
    ]
    subprocess.run(command, check=True, timeout=180)

    video_path = out_dir / "BAMO-first-film.mp4"
    render_project(load_project(project_path), video_path, narration_path)
    manifest = {
        "title": brief["title"],
        "hook": brief["hook"],
        "duration_seconds": sum(float(scene["duration"]) for scene in brief["scenes"]),
        "format": "9:16",
        "resolution": "720x1280",
        "voice": args.voice,
        "role_deliverables": brief["roles"],
        "youtube_upload": "not_performed_requires_owner_approval_and_oauth",
        "video": video_path.name,
        "bytes": video_path.stat().st_size,
    }
    (out_dir / "production_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[BAMO_11_ROLE_PIPELINE_OK] {video_path} ({video_path.stat().st_size} bytes)", flush=True)
    return 0


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
