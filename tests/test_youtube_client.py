from datetime import datetime, timezone

import pytest

from app import youtube_client
from app.youtube_client import _build_upload_status, _contains_synthetic_media, _validate_publish_at


def test_cogvideox_defaults_to_synthetic_media_disclosure(monkeypatch):
    monkeypatch.setenv("VIDEO_ENGINE", "cogvideox")
    monkeypatch.delenv("YOUTUBE_CONTAINS_SYNTHETIC_MEDIA", raising=False)
    assert _contains_synthetic_media() is True


def test_cpu_fallback_does_not_default_to_synthetic_scene_disclosure(monkeypatch):
    monkeypatch.setenv("VIDEO_ENGINE", "cpu")
    monkeypatch.delenv("YOUTUBE_CONTAINS_SYNTHETIC_MEDIA", raising=False)
    assert _contains_synthetic_media() is False


def test_explicit_disclosure_override_is_respected(monkeypatch):
    monkeypatch.setenv("VIDEO_ENGINE", "cpu")
    monkeypatch.setenv("YOUTUBE_CONTAINS_SYNTHETIC_MEDIA", "yes")
    assert _contains_synthetic_media() is True
    monkeypatch.setenv("YOUTUBE_CONTAINS_SYNTHETIC_MEDIA", "false")
    assert _contains_synthetic_media() is False


def test_publish_at_keeps_the_exact_future_slot():
    now = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    value = _validate_publish_at("2026-10-10T02:30:00Z", now=now)
    assert value == "2026-10-10T02:30:00Z"


def test_publish_at_does_not_move_a_late_run_to_the_next_day():
    now = datetime(2026, 10, 10, 2, 20, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="wrong day|another day|too close"):
        _validate_publish_at("2026-10-10T02:30:00Z", now=now)


def test_scheduled_upload_is_private_until_publish_at():
    status = _build_upload_status(
        "public", "2026-11-01T14:30:00Z", contains_synthetic_media=False
    )
    assert status["privacyStatus"] == "private"
    assert status["publishAt"] == "2026-11-01T14:30:00Z"


def test_immediate_public_upload_uses_public_privacy():
    status = _build_upload_status("public", None, contains_synthetic_media=True)
    assert status["privacyStatus"] == "public"
    assert status["containsSyntheticMedia"] is True


def test_private_draft_does_not_receive_publish_at():
    status = _build_upload_status("private", None, contains_synthetic_media=False)
    assert status["privacyStatus"] == "private"
    assert "publishAt" not in status



def test_custom_thumbnail_is_uploaded_for_the_inserted_video(tmp_path):
    thumbnail = tmp_path / "thumbnail.jpg"
    thumbnail.write_bytes(b"jpeg-test")
    captured = {}

    class Request:
        def execute(self):
            return {"items": [{"default": {"url": "https://example.invalid/thumb.jpg"}}]}

    class Thumbnails:
        def set(self, *, videoId, media_body):
            captured["video_id"] = videoId
            captured["media_type"] = media_body.mimetype()
            return Request()

    class YouTube:
        def thumbnails(self):
            return Thumbnails()

    assert youtube_client._set_custom_thumbnail(YouTube(), "video-123", thumbnail) is True
    assert captured == {"video_id": "video-123", "media_type": "image/jpeg"}
