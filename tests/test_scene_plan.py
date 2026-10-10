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


def test_authored_scene_plan_must_match_exact_narration():
    from app.scene_plan import build_scene_plan_from_scenes

    scenes = [
        {"spoken_text": "سلام.", "visual_prompt": "A person greeting a neighbor", "on_screen_text": "سلام", "duration_hint_seconds": 3},
        {"spoken_text": "مهربانی مهم است.", "visual_prompt": "Two people helping each other", "on_screen_text": "مهربانی مهم است", "duration_hint_seconds": 4},
    ]
    plan = build_scene_plan_from_scenes("سلام. مهربانی مهم است.", "title", scenes)
    assert [s["visual_prompt"] for s in plan["scenes"]] == [s["visual_prompt"] for s in scenes]
    with pytest.raises(ValueError, match="exactly equal"):
        build_scene_plan_from_scenes("سلام. متن دیگری.", "title", scenes)


def test_fallback_news_script_has_scene_contract_and_quality_gate_blocks_short_bulletin():
    from app.script_gen import _fallback_script
    from app.agent_guard import validate_package

    stories = [
        {
            "title": "World leaders meet for climate talks",
            "description": "Officials discussed a proposed climate framework.",
            "publisher": "Example World",
            "published_at": "2026-10-10T12:00:00+00:00",
            "category": "world",
            "category_fa": "جهان",
            "url": "https://example.com/world",
        },
        {
            "title": "New computing research announced",
            "description": "Researchers published a new technical study.",
            "publisher": "Example Tech",
            "published_at": "2026-10-10T11:00:00+00:00",
            "category": "technology",
            "category_fa": "فناوری",
            "url": "https://example.com/technology",
        },
        {
            "title": "Markets close after a volatile session",
            "description": "Financial markets moved during the trading session.",
            "publisher": "Example Business",
            "published_at": "2026-10-10T10:00:00+00:00",
            "category": "business",
            "category_fa": "اقتصاد",
            "url": "https://example.com/business",
        },
    ]
    data = _fallback_script({"title_hint": stories[0]["title"], "stories": stories}, "long")
    assert data["title"].startswith("TT خبر |")
    assert data["scene_plan"]
    assert " ".join(scene["spoken_text"] for scene in data["scene_plan"]) == data["script"]
    result = validate_package(data, "long")
    assert not result["ok"]
    assert any(error.startswith("news_script_word_count_outside") for error in result["errors"])
