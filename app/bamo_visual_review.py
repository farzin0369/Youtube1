"""Human frame-review manifest validation for publishable BAMO 3D scenes.

A keyword-to-motif plan is not proof that rendered pixels match narration. A 3D
Short is publishable only after a reviewer records all four actual scene frames.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def validate_visual_review(path: str | Path, *, expected_scenes: int = 4) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.is_file() or manifest_path.stat().st_size == 0:
        return {"ok": False, "errors": ["visual_review_manifest_missing"]}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"ok": False, "errors": ["visual_review_manifest_invalid_json"]}

    errors: list[str] = []
    if manifest.get("version") != 1:
        errors.append("visual_review_manifest_version_unsupported")
    if not str(manifest.get("reviewer") or "").strip():
        errors.append("visual_review_reviewer_missing")
    try:
        reviewed_at = datetime.fromisoformat(str(manifest.get("reviewed_at") or "").replace("Z", "+00:00"))
        if reviewed_at.tzinfo is None:
            errors.append("visual_review_timestamp_must_include_timezone")
    except ValueError:
        errors.append("visual_review_timestamp_invalid")

    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != expected_scenes:
        return {"ok": False, "errors": errors + ["visual_review_scene_count_mismatch"]}

    seen_ids: set[str] = set()
    seen_frames: set[str] = set()
    checked = []
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            errors.append(f"visual_review_scene_{index}_invalid")
            continue
        scene_id = str(scene.get("scene_id") or "").strip()
        if not scene_id or scene_id in seen_ids:
            errors.append(f"visual_review_scene_{index}_id_missing_or_duplicate")
        seen_ids.add(scene_id)
        for field in ("visual_query", "motif", "camera_motion"):
            if not str(scene.get(field) or "").strip():
                errors.append(f"visual_review_scene_{index}_{field}_missing")
        if scene.get("reviewed") is not True or scene.get("review_method") != "human_frame_review":
            errors.append(f"visual_review_scene_{index}_not_human_reviewed")
        try:
            score = float(scene.get("alignment_score"))
            if not 0.90 <= score <= 1.0:
                errors.append(f"visual_review_scene_{index}_alignment_below_threshold")
        except (TypeError, ValueError):
            errors.append(f"visual_review_scene_{index}_alignment_score_invalid")

        frame = Path(str(scene.get("frame_path") or ""))
        if not frame.is_absolute():
            frame = manifest_path.parent / frame
        frame_ok = frame.is_file() and frame.stat().st_size > 0
        if not frame_ok:
            errors.append(f"visual_review_scene_{index}_frame_missing")
        else:
            try:
                from PIL import Image
                with Image.open(frame) as image:
                    image.verify()
                digest = hashlib.sha256(frame.read_bytes()).hexdigest()
                if digest in seen_frames:
                    errors.append(f"visual_review_scene_{index}_frame_reused")
                seen_frames.add(digest)
            except Exception:
                errors.append(f"visual_review_scene_{index}_frame_invalid")
        checked.append({
            "scene_id": scene_id, "frame_path": str(frame), "frame_ok": frame_ok,
            "alignment_score": scene.get("alignment_score"),
        })
    return {"ok": not errors, "errors": errors, "reviewer": manifest.get("reviewer"), "scenes": checked}
