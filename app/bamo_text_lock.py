"""BAMO text lock rules.

User requirement: on-screen text and narrator speech must be identical,
and visuals must be derived from that same text.
"""
from __future__ import annotations

from typing import Any


def lock_scene_text(scene: dict[str, Any]) -> dict[str, Any]:
    """Force on-screen text == spoken narration; seed visual from that text."""
    out = dict(scene)
    spoken = str(
        out.get("spoken_text")
        or out.get("narration")
        or out.get("on_screen_text")
        or out.get("text")
        or ""
    ).strip()
    if not spoken:
        return out

    # Single source of truth
    out["spoken_text"] = spoken
    out["narration"] = spoken
    out["on_screen_text"] = spoken
    out["text"] = spoken

    # Visual query must come from the same words (no unrelated stock prompt)
    visual = str(out.get("visual_query") or out.get("visual_prompt") or "").strip()
    if not visual or visual.lower() in {"abstract", "none", "n/a"}:
        visual = spoken
    out["visual_query"] = visual
    out["visual_prompt"] = visual
    out["text_locked"] = True
    return out


def lock_project_scenes(project: dict[str, Any]) -> dict[str, Any]:
    scenes = project.get("scenes") or []
    out = dict(project)
    out["scenes"] = [lock_scene_text(s) for s in scenes]
    out["text_lock"] = True
    return out
