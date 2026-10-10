from datetime import datetime, timezone

import pytest

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
