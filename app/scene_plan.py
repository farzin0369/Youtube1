"""Structured scene planning and resumable per-scene state for video production.

This module deliberately has no model/API dependency so it can be tested on CPU.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable


def split_narration(text: str) -> list[str]:
    """Split narration at Persian/English sentence boundaries, preserving content."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?؟۔])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def build_scene_plan(
    script: str,
    title: str,
    *,
    kind: str = "short",
    scene_count: int | None = None,
    duration_hint_seconds: float | None = None,
) -> dict[str, Any]:
    """Create a stable scene contract shared by visuals, narration and captions."""
    if kind not in {"short", "long"}:
        raise ValueError("kind must be 'short' or 'long'")
    sentences = split_narration(script)
    if not sentences:
        raise ValueError("script must contain non-empty narration")
    default_count = min(6, len(sentences)) if kind == "short" else min(60, len(sentences))
    count = int(scene_count if scene_count is not None else default_count)
    if count < 1:
        raise ValueError("scene_count must be >= 1")
    # Keep scene count bounded by narration sentences; group adjacent sentences for longer scenes.
    count = min(count, len(sentences))
    groups: list[list[str]] = [[] for _ in range(count)]
    for idx, sentence in enumerate(sentences):
        groups[min(idx * count // len(sentences), count - 1)].append(sentence)
    full_duration = float(duration_hint_seconds or (45 if kind == "short" else 240))
    if full_duration <= 0:
        raise ValueError("duration_hint_seconds must be > 0")
    per_scene = full_duration / count
    scenes = []
    for idx, group in enumerate(groups):
        spoken = " ".join(group).strip()
        scenes.append({
            "scene_id": f"scene_{idx + 1:03d}",
            "index": idx,
            "spoken_text": spoken,
            "visual_prompt": "",
            "on_screen_text": spoken,
            "duration_hint_seconds": round(per_scene, 3),
            "status": "pending",
            "clip_path": None,
            "error": None,
        })
    plan = {
        "schema_version": 1,
        "title": str(title or "").strip(),
        "kind": kind,
        "language": "fa",
        "scene_count": len(scenes),
        "duration_hint_seconds": round(full_duration, 3),
        "scenes": scenes,
    }
    validate_scene_plan(plan)
    return plan


def validate_scene_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != 1:
        raise ValueError("unsupported scene plan schema_version")
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("scene plan must contain at least one scene")
    seen: set[str] = set()
    for expected_index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValueError(f"scene {expected_index} must be an object")
        scene_id = str(scene.get("scene_id") or "")
        if not scene_id or scene_id in seen:
            raise ValueError(f"scene {expected_index} has missing or duplicate scene_id")
        seen.add(scene_id)
        if scene.get("index") != expected_index:
            raise ValueError(f"scene {scene_id} has non-sequential index")
        if not str(scene.get("spoken_text") or "").strip():
            raise ValueError(f"scene {scene_id} has no spoken_text")
        if float(scene.get("duration_hint_seconds") or 0) <= 0:
            raise ValueError(f"scene {scene_id} has invalid duration")
        if scene.get("status", "pending") not in {"pending", "running", "complete", "failed"}:
            raise ValueError(f"scene {scene_id} has invalid status")


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically to avoid corrupting a checkpoint on interruption."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load_or_create_plan(path: Path, script: str, title: str, **kwargs: Any) -> dict[str, Any]:
    """Reuse a valid existing plan; create it once otherwise."""
    path = Path(path)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            validate_scene_plan(existing)
            return existing
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # Preserve the broken file for diagnosis before replacing it.
            backup = path.with_suffix(path.suffix + ".invalid")
            if not backup.exists():
                path.replace(backup)
    plan = build_scene_plan(script, title, **kwargs)
    atomic_write_json(path, plan)
    return plan


def mark_scene(
    plan: dict[str, Any],
    index: int,
    *,
    status: str,
    clip_path: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    if status not in {"pending", "running", "complete", "failed"}:
        raise ValueError("invalid scene status")
    scene = plan["scenes"][index]
    scene["status"] = status
    scene["clip_path"] = clip_path
    scene["error"] = (str(error)[:1000] if error else None)
    return plan


def completed_scene_indices(plan: dict[str, Any]) -> set[int]:
    """Return indices marked complete; caller must additionally verify clip files exist."""
    validate_scene_plan(plan)
    return {
        int(scene["index"])
        for scene in plan["scenes"]
        if scene.get("status") == "complete" and scene.get("clip_path")
    }
