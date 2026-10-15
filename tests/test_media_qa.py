from pathlib import Path

from app.media_qa import validate_render_package


def _short_package(tmp_path: Path):
    audio = tmp_path / "voice.mp3"
    audio.write_bytes(b"\0" * 2048)
    meta = {
        "video_path": str(tmp_path / "out.mp4"),
        "video_width": 1080,
        "video_height": 1920,
        "duration": 24.0,
        "duration_seconds": 24.0,
        "audio_duration_seconds": 24.0,
        "caption_cues": 6,
        "caption_font_size": 48,
        "music_ducking": True,
        "scene_query_match": True,
        "visual_source": "pexels",
        "visual_scene_count": 4,
        "stock_clip_count": 4,
        "test_visuals_only": False,
    }
    return meta, audio


def test_good_shorts_package_passes_all_vertical_mobile_gates(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["duration_seconds"] = meta.pop("duration")
    result = validate_render_package(meta, audio, video_format="shorts")
    assert result["ok"]
    assert result["checks"]["video_dimensions"]["aspect_ratio"] == 0.5625
    assert result["checks"]["caption_cues"] == 6


def test_wan_generated_shorts_pass_visual_source_gate_and_are_marked_ai(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["visual_source"] = "wan2.1"
    result = validate_render_package(meta, audio, video_format="shorts")
    assert result["ok"]
    assert "Wan2.1-generated AI video" in result["checks"]["visual_source_note"]


def test_shorts_quality_gate_blocks_landscape_frame(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["video_width"], meta["video_height"] = 1280, 720
    meta["visual_source"] = "generated abstract fallback"
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "shorts_must_be_vertical_9_16_at_least_720x1280" in result["errors"]


def test_shorts_quality_gate_blocks_too_short_or_unreadable_package(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["duration"] = 12.0
    meta["duration_seconds"] = 12.0
    meta["caption_font_size"] = 28
    meta["music_ducking"] = False
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "shorts_duration_outside_15_40_seconds" in result["errors"]
    assert "shorts_caption_font_too_small" in result["errors"]
    assert "shorts_background_music_not_ducked_under_voice" in result["errors"]


def test_explicit_scene_stills_pass_as_free_private_draft_visuals(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["visual_source"] = "provided stills"
    meta["test_visuals_only"] = True
    meta["duration_seconds"] = meta.pop("duration")
    result = validate_render_package(meta, audio, video_format="shorts")
    assert result["ok"]


def test_provided_stills_and_abstract_pass_visual_source_for_private_path(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["visual_source"] = "provided stills"
    meta.pop("duration", None)
    meta["duration_seconds"] = 24.0
    result = validate_render_package(meta, audio, video_format="shorts")
    assert result["ok"]
    meta2, audio2 = _short_package(tmp_path)
    meta2["visual_source"] = "generated abstract fallback"
    meta2.pop("duration", None)
    meta2["duration_seconds"] = 24.0
    result2 = validate_render_package(meta2, audio2, video_format="shorts")
    assert result2["ok"]


def test_shorts_audio_shorter_than_video_fails_qa(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["audio_duration_seconds"] = 15.3
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "audio_video_duration_mismatch" in result["errors"]
