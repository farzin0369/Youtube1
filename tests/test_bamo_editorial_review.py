from pathlib import Path

import pytest

from app.bamo_editorial_review import ROLE_NAMES, review_package


def _candidate():
    scenes = [
        {"spoken_text": "چرا نور هنگام عبور از آب خم می‌شود؟", "visual_query": "laser beam refraction in glass", "on_screen_text": "شکست نور"},
        {"spoken_text": "سرعت نور در آب کمتر از هواست.", "visual_query": "light beam entering water tank", "on_screen_text": "سرعت متفاوت"},
        {"spoken_text": "به همین دلیل مسیر پرتو تغییر می‌کند.", "visual_query": "prism light refraction experiment", "on_screen_text": "تغییر مسیر"},
        {"spoken_text": "این پدیده را شکست نور می‌نامیم.", "visual_query": "scientific optics laboratory setup", "on_screen_text": "شکست نور"},
    ]
    return {
        "topic": "شکست نور",
        "title": "BAMO | چرا نور در آب خم می‌شود؟",
        "description": "این ویدئو پدیدهٔ شکست نور را توضیح می‌دهد. با یک آزمایش ساده می‌بینیم چرا مسیر نور هنگام ورود به آب تغییر می‌کند.",
        "thumbnail_text": "راز شکست نور",
        "tags": ["شکست نور", "فیزیک نور", "آزمایش نور", "نور در آب", "آزمایش فیزیک", "BAMO", "12bamo", "بامو"],
        "scenes": scenes,
        "script": " ".join(scene["spoken_text"] for scene in scenes),
    }


def test_all_eleven_specialist_roles_are_present():
    assert len(ROLE_NAMES) == 11
    assert len(set(ROLE_NAMES)) == 11


def test_editorial_review_passes_all_roles_with_relevant_metadata_and_captions(tmp_path):
    captions = tmp_path / "captions.srt"
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nچرا نور هنگام عبور از آب خم می‌شود؟\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\nسرعت نور در آب کمتر از هواست.\n\n"
        "3\n00:00:02,000 --> 00:00:03,000\nبه همین دلیل مسیر پرتو تغییر می‌کند.\n\n"
        "4\n00:00:03,000 --> 00:00:04,000\nاین پدیده را شکست نور می‌نامیم.\n",
        encoding="utf-8",
    )
    report = review_package(_candidate(), channel_videos=[], captions_path=captions, policy={})
    assert report["ok"] is True
    assert len(report["roles"]) == 11
    assert all(role["ok"] for role in report["roles"])


def test_editorial_review_fails_closed_when_captions_are_missing(tmp_path):
    with pytest.raises(ValueError, match="chapters"):
        review_package(_candidate(), channel_videos=[], captions_path=tmp_path / "missing.srt", policy={})
