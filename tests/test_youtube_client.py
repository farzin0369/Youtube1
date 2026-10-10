from app.youtube_client import _contains_synthetic_media


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
