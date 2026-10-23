from __future__ import annotations

import copy

import pytest

from app.ltx_video_engine import _frames_for_duration, _normalize_scene_durations
from app.ltx_spiritual_renderer import _scene_plan


def test_ltx_frame_counts_follow_eight_n_plus_one_temporal_rule():
    for seconds in (1, 2, 2.5, 4, 7.25, 30):
        frames = _frames_for_duration(seconds, fps=8)
        assert frames >= 9
        assert (frames - 1) % 8 == 0


def test_scene_duration_normalization_matches_narration_duration():
    scenes = [
        {"duration_hint_seconds": 1.0},
        {"duration_hint_seconds": 3.0},
        {"duration_hint_seconds": 2.0},
    ]
    _normalize_scene_durations(scenes, 30.0)
    assert sum(scene["duration_hint_seconds"] for scene in scenes) == pytest.approx(30.0)
    assert scenes[1]["duration_hint_seconds"] == pytest.approx(15.0)


def test_short_scene_plan_covers_exact_script_and_has_four_scenes():
    scenes = [
        {"spoken_text": "چرا گاهی امیدت کم می‌شود؟", "visual_query": "quiet dawn and open window", "on_screen_text": "چرا امیدت کم می‌شود؟"},
        {"spoken_text": "گاهی ذهن از نگرانی خسته می‌شود.", "visual_query": "person sitting beside window", "on_screen_text": "ذهن خسته می‌شود"},
        {"spoken_text": "امروز فقط یک قدم کوچک بردار.", "visual_query": "hands planting a seed", "on_screen_text": "یک قدم کوچک"},
        {"spoken_text": "آرامش با قدم‌های کوچک برمی‌گردد.", "visual_query": "sunlight over peaceful path", "on_screen_text": "آرامش برمی‌گردد"},
    ]
    script = " ".join(scene["spoken_text"] for scene in scenes)
    plan = _scene_plan({"script": script, "scenes": scenes}, "short")
    assert len(plan) == 4
    assert " ".join(scene["spoken_text"] for scene in plan) == script
    assert all(scene["visual_prompt"] and scene["duration_hint_seconds"] > 0 for scene in plan)


def test_short_scene_plan_fails_closed_when_narration_does_not_match():
    content = {
        "script": "متن متفاوت است.",
        "scenes": [
            {"spoken_text": "چرا این اتفاق می‌افتد؟", "visual_query": "quiet room", "on_screen_text": "چرا؟"},
            {"spoken_text": "این یک جمله است.", "visual_query": "morning sky", "on_screen_text": "یک جمله"},
            {"spoken_text": "امروز قدمی بردار.", "visual_query": "person walking", "on_screen_text": "قدم بردار"},
            {"spoken_text": "به خودت فرصت بده.", "visual_query": "sunlight through trees", "on_screen_text": "فرصت بده"},
        ],
    }
    with pytest.raises(RuntimeError, match="does not exactly cover"):
        _scene_plan(content, "short")


def test_long_scene_plan_preserves_all_section_narration():
    sections = [
        {"heading": "صبر", "text": "گاهی صبر یعنی مکث کردن. سپس با آرامش تصمیم بگیریم."},
        {"heading": "عمل", "text": "امروز یک کار کوچک را انجام بده. همین قدم کافی است."},
    ]
    script = " ".join(section["text"] for section in sections)
    plan = _scene_plan({"script": script, "sections": sections}, "long")
    assert len(plan) == 4
    assert " ".join(scene["spoken_text"] for scene in plan) == script
