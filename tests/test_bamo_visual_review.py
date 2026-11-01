from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from app.bamo_visual_review import validate_visual_review


def _manifest(tmp_path: Path) -> Path:
    scenes = []
    for index in range(4):
        frame = tmp_path / f"scene-{index}.png"
        Image.new("RGB", (64, 64), color=(index * 40, 30, 80)).save(frame)
        scenes.append({
            "scene_id": f"scene-{index}",
            "visual_query": f"subject-specific scene {index}",
            "motif": f"motif-{index}",
            "camera_motion": "push_in",
            "frame_path": frame.name,
            "reviewed": True,
            "review_method": "human_frame_review",
            "alignment_score": 0.96,
        })
    path = tmp_path / "visual-review.json"
    path.write_text(json.dumps({
        "version": 1,
        "reviewer": "BAMO visual QA reviewer",
        "reviewed_at": "2026-11-02T10:00:00+03:30",
        "scenes": scenes,
    }), encoding="utf-8")
    return path


def test_all_four_distinct_human_reviewed_frames_pass(tmp_path: Path):
    result = validate_visual_review(_manifest(tmp_path))
    assert result["ok"], result["errors"]
    assert len(result["scenes"]) == 4


def test_missing_manifest_fails_closed(tmp_path: Path):
    result = validate_visual_review(tmp_path / "missing.json")
    assert not result["ok"]
    assert "visual_review_manifest_missing" in result["errors"]


def test_unreviewed_scene_fails_closed(tmp_path: Path):
    path = _manifest(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scenes"][2]["reviewed"] = False
    path.write_text(json.dumps(data), encoding="utf-8")
    result = validate_visual_review(path)
    assert not result["ok"]
    assert "visual_review_scene_3_not_human_reviewed" in result["errors"]


def test_duplicate_frame_reuse_fails_closed(tmp_path: Path):
    path = _manifest(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scenes"][1]["frame_path"] = data["scenes"][0]["frame_path"]
    path.write_text(json.dumps(data), encoding="utf-8")
    result = validate_visual_review(path)
    assert not result["ok"]
    assert "visual_review_scene_2_frame_reused" in result["errors"]


def test_low_alignment_score_fails_closed(tmp_path: Path):
    path = _manifest(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scenes"][0]["alignment_score"] = 0.72
    path.write_text(json.dumps(data), encoding="utf-8")
    result = validate_visual_review(path)
    assert not result["ok"]
    assert "visual_review_scene_1_alignment_below_threshold" in result["errors"]
