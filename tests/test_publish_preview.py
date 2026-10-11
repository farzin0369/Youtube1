import json
from pathlib import Path

import pytest

from scripts import publish_preview


def _artifact(tmp_path: Path, *, dry_run: bool = True) -> Path:
    run_dir = tmp_path / "output" / "spiritual" / "run-123"
    run_dir.mkdir(parents=True)
    for name in ("video.mp4", "thumbnail.jpg", "captions.srt", "narration.mp3"):
        (run_dir / name).write_bytes(b"test")
    content = {
        "title": "Imam Ali ✨ یک قدم آرام در روزهای دشوار",
        "description": "توضیح کوتاه ویدئو.",
        "tags": ["ImamAli110", "رشد فردی"],
        "sections": [{"heading": "شروع", "text": "این یک بخش آزمایشی برای محاسبهٔ فصل است."}],
    }
    render = {
        "ok": True,
        "video_path": "/runner/output/spiritual/run-123/video.mp4",
        "thumbnail_path": "/runner/output/spiritual/run-123/thumbnail.jpg",
        "captions_path": "/runner/output/spiritual/run-123/captions.srt",
        "duration_seconds": 360,
        "on_screen_captions": True,
        "pexels_credits": [],
    }
    result = {
        "dry_run": dry_run,
        "title": content["title"],
        "tts": {"duration_seconds": 360},
        "render": render,
        "media_qa": {"ok": True},
        "upload": {"skipped": True, "reason": "dry-run"},
    }
    (run_dir / "content.json").write_text(json.dumps(content), encoding="utf-8")
    (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    return tmp_path


def test_load_reviewed_package_revalidates_and_preserves_preview_metadata(tmp_path, monkeypatch):
    artifact_dir = _artifact(tmp_path)
    observed = {}

    def qa(metadata, audio_path):
        observed["metadata"] = metadata
        observed["audio_path"] = audio_path
        return {"ok": True}

    monkeypatch.setattr(publish_preview, "validate_render_package", qa)
    package = publish_preview.load_reviewed_package(artifact_dir)

    assert package["title"] == "Imam Ali ✨ یک قدم آرام در روزهای دشوار"
    assert package["video_path"].name == "video.mp4"
    assert package["thumbnail_path"].name == "thumbnail.jpg"
    assert package["captions_path"].name == "captions.srt"
    assert "فصل‌های ویدئو:" in package["description"]
    assert observed["metadata"]["video_path"].endswith("video.mp4")
    assert observed["audio_path"].name == "narration.mp3"


def test_load_reviewed_package_rejects_non_dry_run_artifacts(tmp_path, monkeypatch):
    artifact_dir = _artifact(tmp_path, dry_run=False)
    monkeypatch.setattr(publish_preview, "validate_render_package", lambda *args: {"ok": True})

    with pytest.raises(ValueError, match="exactly one complete reviewed package"):
        publish_preview.load_reviewed_package(artifact_dir)


def test_load_reviewed_package_rejects_media_that_fails_qa(tmp_path, monkeypatch):
    artifact_dir = _artifact(tmp_path)
    monkeypatch.setattr(publish_preview, "validate_render_package", lambda *args: {"ok": False})

    with pytest.raises(ValueError, match="exactly one complete reviewed package"):
        publish_preview.load_reviewed_package(artifact_dir)
