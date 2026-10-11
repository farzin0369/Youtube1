from datetime import datetime, timezone
import sys
import types

import pytest

from app import youtube_client
from app.youtube_client import _contains_synthetic_media, _validate_publish_at


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


def test_public_upload_requires_a_custom_thumbnail_before_api_upload(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    monkeypatch.setattr(youtube_client, "has_youtube_creds", lambda: True)
    result = youtube_client.upload_video(video, "title", "description", [], privacy="public")
    assert not result["ok"]
    assert "thumbnail" in result["error"].lower()


def test_scheduled_upload_stays_private_when_caption_upload_fails(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    thumbnail = tmp_path / "thumbnail.jpg"
    captions = tmp_path / "captions.srt"
    video.write_bytes(b"video")
    thumbnail.write_bytes(b"thumbnail")
    captions.write_text("1\n00:00:00,000 --> 00:00:01,000\nسلام\n", encoding="utf-8")

    class VideoInsert:
        def next_chunk(self):
            return None, {"id": "video-id"}

    class FailedCaptionInsert:
        def execute(self):
            raise RuntimeError("caption API unavailable")

    class Videos:
        def __init__(self):
            self.updated = False

        def insert(self, **kwargs):
            return VideoInsert()

        def update(self, **kwargs):
            self.updated = True
            return self

        def execute(self):
            return {}

    class FakeYouTube:
        def __init__(self):
            self.video_api = Videos()

        def videos(self):
            return self.video_api

        def captions(self):
            return types.SimpleNamespace(insert=lambda **kwargs: FailedCaptionInsert())

        def thumbnails(self):
            return types.SimpleNamespace(set=lambda **kwargs: types.SimpleNamespace(execute=lambda: {}))

    fake_youtube = FakeYouTube()
    discovery = types.ModuleType("googleapiclient.discovery")
    discovery.build = lambda *args, **kwargs: fake_youtube
    http = types.ModuleType("googleapiclient.http")
    http.MediaFileUpload = lambda *args, **kwargs: object()
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", discovery)
    monkeypatch.setitem(sys.modules, "googleapiclient.http", http)
    monkeypatch.setattr(youtube_client, "has_youtube_creds", lambda: True)
    monkeypatch.setattr(youtube_client, "_build_credentials", lambda: object())
    monkeypatch.setattr(youtube_client, "_contains_synthetic_media", lambda: False)
    monkeypatch.setattr(youtube_client, "_validate_publish_at", lambda value: value)

    result = youtube_client.upload_video(
        video, "title", "description", [], privacy="public",
        thumbnail_path=thumbnail, publish_at="2026-10-12T14:30:00Z",
    )

    assert not result["ok"]
    assert result["privacy"] == "private"
    assert "caption" in result["error"].lower()
    assert not fake_youtube.video_api.updated
