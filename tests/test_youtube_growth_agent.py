from app.youtube_growth_agent import review_package


def _short_package():
    scenes = [
        {"spoken_text": "چرا امیدت گاهی کم می‌شود؟", "on_screen_text": "چرا امیدت کم می‌شود؟"},
        {"spoken_text": "گاهی نگرانی ذهن را خسته می‌کند.", "on_screen_text": "نگرانی ذهن را خسته می‌کند"},
        {"spoken_text": "امروز فقط یک قدم کوچک بردار.", "on_screen_text": "یک قدم کوچک"},
        {"spoken_text": "آرامش با قدم‌های کوچک برمی‌گردد.", "on_screen_text": "آرامش برمی‌گردد"},
    ]
    return {
        "format": "shorts",
        "title": "Imam Ali ✨ چرا امیدت کم می‌شود؟",
        "description": "یک تأمل کوتاه برای امروز.",
        "tags": ["ImamAli110", "The110Path", "معنویت اسلامی"],
        "thumbnail_text": "یک قدم کوچک",
        "hook": scenes[0]["spoken_text"],
        "scenes": scenes,
        "script": " ".join(scene["spoken_text"] for scene in scenes),
    }


def _render():
    return {
        "scene_mapping": "exact-narration-scene-plan",
        "visual_source": "ltx-video",
        "visual_scene_count": 4,
        "video_format": "shorts",
        "scene_plan_path": "scene_plan.json",
    }


def test_growth_review_accepts_complete_ltx_package():
    result = review_package(_short_package(), _render(), {"ok": True}, {"recent": []})
    assert result["ok"] is True
    assert result["publish_allowed"] is True
    assert result["hook_score"] >= 3
    assert result["seo_pack_score"] == 5
    assert len(result["checked_capabilities"]) == 11


def test_growth_review_blocks_missing_ltx_mapping_or_media_qa():
    render = _render()
    render["scene_mapping"] = "unverified"
    result = review_package(_short_package(), render, {"ok": False}, {"recent": []})
    assert result["ok"] is False
    assert "media_qa_failed" in result["blockers"]
    assert "scene_narration_mapping_unverified" in result["blockers"]


def test_growth_review_warns_about_duplicate_recent_titles():
    content = _short_package()
    result = review_package(content, _render(), {"ok": True}, {"recent": [{"title": content["title"]}]})
    assert any("۳۰ ویدئوی اخیر" in warning for warning in result["warnings"])
