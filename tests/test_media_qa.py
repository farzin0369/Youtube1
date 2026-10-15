from pathlib import Path
import pytest

from app.media_qa import ensure_upload_eligible, validate_render_package


def _package(tmp_path: Path):
    from PIL import Image

    video = tmp_path / "video.mp4"
    thumb = tmp_path / "thumbnail.jpg"
    captions = tmp_path / "captions.srt"
    audio = tmp_path / "audio.wav"
    for path in (video, audio):
        path.write_bytes(b"test-media")
    Image.new("RGB", (1280, 720), color=(20, 30, 40)).save(thumb, format="JPEG")
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nسلام\n\n"
        "2\n00:00:02,000 --> 00:00:04,000\nمهربانی\n",
        encoding="utf-8",
    )
    meta = {
        "ok": True,
        "video_path": str(video),
        "thumbnail_path": str(thumb),
        "captions_path": str(captions),
        "duration": 4.0,
        "on_screen_captions": True,
        "video_width": 1280,
        "video_height": 720,
    }
    return meta, audio


def test_valid_media_package_passes(tmp_path: Path):
    meta, audio = _package(tmp_path)
    result = validate_render_package(meta, audio)
    assert result["ok"]
    assert result["checks"]["caption_cues"] == 2


def test_missing_video_blocks_upload(tmp_path: Path):
    meta, audio = _package(tmp_path)
    Path(meta["video_path"]).unlink()
    result = validate_render_package(meta, audio)
    assert not result["ok"]
    assert "missing_or_empty_video" in result["errors"]


def test_captions_outside_video_duration_fail(tmp_path: Path):
    meta, audio = _package(tmp_path)
    meta["duration"] = 2.0
    result = validate_render_package(meta, audio)
    assert not result["ok"]
    assert "captions_exceed_video_duration" in result["errors"]


def test_preview_only_assets_cannot_be_uploaded():
    for meta in (
        {"test_visuals_only": True, "visual_source": "pexels"},
        {"test_visuals_only": False, "visual_source": "provided stills"},
        {"test_visuals_only": False, "visual_source": "generated abstract fallback"},
        {"test_visuals_only": False, "visual_source": "pollinations"},
    ):
        with pytest.raises(ValueError, match="preview_only_media_not_eligible_for_upload"):
            ensure_upload_eligible(meta)


def test_caption_end_within_muxing_rounding_tolerance_passes(tmp_path: Path):
    meta, audio = _package(tmp_path)
    captions = Path(meta["captions_path"])
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nسلام\n\n"
        "2\n00:00:02,000 --> 00:00:04,080\nمهربانی\n",
        encoding="utf-8",
    )
    result = validate_render_package(meta, audio)
    assert result["ok"]


def test_caption_end_over_100ms_after_video_fails(tmp_path: Path):
    meta, audio = _package(tmp_path)
    captions = Path(meta["captions_path"])
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nسلام\n\n"
        "2\n00:00:02,000 --> 00:00:04,170\nمهربانی\n",
        encoding="utf-8",
    )
    result = validate_render_package(meta, audio)
    assert not result["ok"]
    assert "captions_exceed_video_duration" in result["errors"]


def test_low_resolution_thumbnail_fails_qa(tmp_path: Path):
    from PIL import Image

    meta, audio = _package(tmp_path)
    Image.new("RGB", (320, 180), color=(20, 30, 40)).save(meta["thumbnail_path"], format="JPEG")
    result = validate_render_package(meta, audio)
    assert not result["ok"]
    assert "thumbnail_invalid_dimensions_or_aspect_ratio" in result["errors"]


def test_portrait_video_is_rejected_for_long_form(tmp_path: Path):
    meta, audio = _package(tmp_path)
    meta["video_width"], meta["video_height"] = 720, 1280
    result = validate_render_package(meta, audio)
    assert not result["ok"]
    assert "video_must_be_landscape_at_least_640x360" in result["errors"]


def _short_package(tmp_path: Path):
    meta, audio = _package(tmp_path)
    meta.update({
        "video_format": "shorts", "duration": 24.0,
        "audio_duration_seconds": 24.0,
        "video_width": 720, "video_height": 1280,
        "caption_font_size": 48, "hook_overlay": "یک قدم واقعی",
        "caption_animation_profile": "phrase-pop-fade-v1",
        "persian_text_shaping": "noto-naskh-unicode-rtl",
        "scene_query_match": True, "visual_source": "pexels",
        "music_ducking": True, "visual_scene_count": 4,
    })
    srt = []
    for index in range(6):
        start, end = index * 2, index * 2 + 1.6
        srt.append(f"{index+1}\n00:00:{start:02d},000 --> 00:00:{end:02.0f},000\nزیرنویس خوانا\n")
    Path(meta["captions_path"]).write_text("\n".join(srt), encoding="utf-8")
    burned = tmp_path / "captions.ass"
    burned.write_text(
        "[Script Info]\nWrapStyle: 0\nKerning: yes\n"
        "Style: Default,Noto Naskh Arabic,48\nDialogue: 0,,,{\\fad(90,70)\\fscx100}سلام\n",
        encoding="utf-8",
    )
    meta["burned_captions_path"] = str(burned)
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
    meta["duration"] = 10.0  # below the 12s floor
    meta["caption_font_size"] = 28
    meta["music_ducking"] = False
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert any("duration" in e for e in result["errors"]) or "shorts_duration_outside_12_45_seconds" in result["errors"] or any("duration" in e for e in result["errors"])
    assert "shorts_caption_font_too_small" in result["errors"]
    assert "shorts_background_music_not_ducked_under_voice" in result["errors"]


def test_explicit_scene_stills_pass_only_as_non_uploadable_preview_media(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["visual_source"] = "provided stills"
    meta["test_visuals_only"] = True
    meta["duration_seconds"] = meta.pop("duration")
    result = validate_render_package(meta, audio, video_format="shorts")
    assert result["ok"]
    assert "not eligible for upload" in result["checks"]["visual_source_note"]


def test_preview_stills_and_abstract_pass_visual_source_gate(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["visual_source"] = "provided stills"
    meta["test_visuals_only"] = True
    meta.pop("duration", None)
    meta["duration_seconds"] = 24.0
    result = validate_render_package(meta, audio, video_format="shorts")
    assert result["ok"]
    meta2, audio2 = _short_package(tmp_path)
    meta2["visual_source"] = "generated abstract fallback"
    meta2["test_visuals_only"] = True
    meta2.pop("duration", None)
    meta2["duration_seconds"] = 24.0
    result2 = validate_render_package(meta2, audio2, video_format="shorts")
    assert result2["ok"]


def test_provided_stills_without_preview_flag_fail_short_qa(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["visual_source"] = "provided stills"
    meta["test_visuals_only"] = False
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "shorts_visual_source_not_approved_portrait_stock" in result["errors"]


def test_shorts_audio_shorter_than_video_fails_qa(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["audio_duration_seconds"] = 15.3
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "audio_video_duration_mismatch" in result["errors"]


def test_shorts_audio_duration_is_required(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta.pop("audio_duration_seconds")
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "shorts_audio_duration_missing" in result["errors"]


def test_shorts_quality_gate_rejects_missing_caption_animation_or_shaping(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["caption_animation_profile"] = "static"
    meta["persian_text_shaping"] = "reversed-or-unknown"
    Path(meta["burned_captions_path"]).write_text("[Script Info]\n", encoding="utf-8")
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "shorts_caption_animation_missing_or_invalid" in result["errors"]
    assert "shorts_persian_text_shaping_not_configured" in result["errors"]
