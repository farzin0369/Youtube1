from pathlib import Path

from app.media_qa import validate_render_package


def _package(tmp_path: Path):
    video = tmp_path / "video.mp4"
    thumb = tmp_path / "thumbnail.jpg"
    captions = tmp_path / "captions.srt"
    audio = tmp_path / "audio.wav"
    for path in (video, thumb, audio):
        path.write_bytes(b"test-media")
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
