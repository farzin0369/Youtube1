from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.scene_plan import (
    atomic_write_json,
    build_scene_plan,
    completed_scene_indices,
    load_or_create_plan,
    mark_scene,
    validate_scene_plan,
)


def test_scene_plan_uses_persian_sentence_boundaries_and_shared_text():
    plan = build_scene_plan("سلام. مهربانی مهم است! با هم بهتر می‌شویم؟", "Imam Ali ✨ مهربانی", scene_count=2)
    assert plan["scene_count"] == 2
    assert "".join(scene["spoken_text"] for scene in plan["scenes"]).replace(" ", "") == "سلام.مهربانی مهم است!با هم بهتر می‌شویم؟".replace(" ", "")
    assert all(scene["spoken_text"] and scene["on_screen_text"] for scene in plan["scenes"])
    assert sum(scene["duration_hint_seconds"] for scene in plan["scenes"]) == pytest.approx(45)


def test_empty_script_and_invalid_scene_count_are_rejected():
    with pytest.raises(ValueError):
        build_scene_plan("   ", "title")
    with pytest.raises(ValueError):
        build_scene_plan("سلام.", "title", scene_count=0)


def test_validation_rejects_duplicate_ids_and_empty_spoken_text():
    plan = build_scene_plan("اول. دوم.", "title", scene_count=2)
    plan["scenes"][1]["scene_id"] = plan["scenes"][0]["scene_id"]
    with pytest.raises(ValueError, match="duplicate"):
        validate_scene_plan(plan)


def test_checkpoint_round_trip_and_resume(tmp_path: Path):
    path = tmp_path / "scene_plan.json"
    plan = load_or_create_plan(path, "صحنهٔ اول. صحنهٔ دوم.", "title", scene_count=2)
    mark_scene(plan, 0, status="complete", clip_path="clips/scene_001.mp4")
    atomic_write_json(path, plan)
    restored = load_or_create_plan(path, "صحنهٔ اول. صحنهٔ دوم.", "title", scene_count=2)
    assert completed_scene_indices(restored) == {0}
    assert restored["title"] == "title"
    assert json.loads(path.read_text(encoding="utf-8"))["scenes"][0]["status"] == "complete"


def test_invalid_checkpoint_is_preserved_for_debugging(tmp_path: Path):
    path = tmp_path / "scene_plan.json"
    path.write_text("{broken", encoding="utf-8")
    plan = load_or_create_plan(path, "یک صحنه.", "title")
    assert plan["scene_count"] == 1
    assert path.with_suffix(".json.invalid").exists()


def test_changed_script_does_not_reuse_stale_scene_plan(tmp_path: Path):
    path = tmp_path / "scene_plan.json"
    first = load_or_create_plan(path, "متن اول.", "title")
    mark_scene(first, 0, status="complete", clip_path="clips/scene_001.mp4")
    atomic_write_json(path, first)
    second = load_or_create_plan(path, "متن دوم.", "title")
    assert second["scenes"][0]["spoken_text"] == "متن دوم."
    assert second["scenes"][0]["status"] == "pending"
    assert path.with_suffix(".json.stale").exists()


def test_srt_uses_scene_plan_and_finishes_at_media_duration(tmp_path: Path):
    from app.video_render import write_srt

    plan_path = tmp_path / "scene_plan.json"
    plan = build_scene_plan("آغاز. پایان.", "title", scene_count=2)
    plan["scenes"][0]["on_screen_text"] = "آغاز"
    plan["scenes"][1]["on_screen_text"] = "پایان"
    atomic_write_json(plan_path, plan)
    srt_path = write_srt("متن کلی", tmp_path / "captions.srt", 12.0, scene_plan_path=plan_path)
    output = srt_path.read_text(encoding="utf-8")
    assert "آغاز" in output and "پایان" in output
    assert "00:00:12,000" in output
