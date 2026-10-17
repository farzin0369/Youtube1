from pathlib import Path

from app.media_qa import validate_render_package


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


def test_shorts_quality_gate_blocks_landscape_frame_and_abstract_fallback(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["video_width"], meta["video_height"] = 1280, 720
    meta["visual_source"] = "generated abstract fallback"
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "shorts_must_be_vertical_9_16_at_least_720x1280" in result["errors"]
    assert "shorts_visual_source_not_approved_portrait_stock" in result["errors"]


def test_shorts_quality_gate_blocks_too_short_or_unreadable_package(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["duration"] = 12.0
    meta["caption_font_size"] = 28
    meta["music_ducking"] = False
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "shorts_duration_outside_15_40_seconds" in result["errors"]
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


def test_provided_stills_cannot_pass_publish_qa_without_preview_only_marker(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["visual_source"] = "provided stills"
    meta.pop("duration", None)
    meta["duration_seconds"] = 24.0
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



def test_local_topic_matched_portrait_clips_can_pass_shorts_qa(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    rows = []
    for index, topic in enumerate(("sunrise", "mountain", "water", "walking")):
        folder = tmp_path / "assets" / "fallback_videos" / topic
        folder.mkdir(parents=True)
        clip = folder / f"clip_{index}.mp4"
        clip.write_bytes(b"test-clip")
        rows.append({
            "query": f"scene about {topic}",
            "source": str(clip),
            "topic": topic,
            "portrait": True,
            "topic_matched": True,
        })
    meta["visual_source"] = "local topic-matched portrait footage"
    meta["scene_visuals"] = rows
    meta["scene_query_match"] = True
    result = validate_render_package(meta, audio, video_format="shorts")
    assert result["ok"]
    assert "local clips" in result["checks"]["visual_source_note"]


def test_local_topic_matched_footage_requires_four_existing_topic_files(tmp_path: Path):
    meta, audio = _short_package(tmp_path)
    meta["visual_source"] = "local topic-matched portrait footage"
    meta["scene_visuals"] = [{
        "query": "sunrise",
        "source": str(tmp_path / "missing.mp4"),
        "topic": "sunrise",
        "portrait": True,
        "topic_matched": True,
    }] * 4
    meta["scene_query_match"] = True
    result = validate_render_package(meta, audio, video_format="shorts")
    assert not result["ok"]
    assert "shorts_visual_source_not_approved_portrait_stock" in result["errors"]
