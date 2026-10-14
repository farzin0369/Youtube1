import json
import subprocess
from pathlib import Path

import pytest

from scripts.validate_video_dimensions import probe_video_dimensions, validate_shorts_dimensions


def test_accepts_standard_shorts_portrait_sizes():
    assert validate_shorts_dimensions(720, 1280) == {
        "width": 720, "height": 1280, "aspect_ratio": 0.5625,
    }
    assert validate_shorts_dimensions(1080, 1920)["aspect_ratio"] == 0.5625


@pytest.mark.parametrize(
    ("width", "height"),
    [(1920, 1080), (1280, 720), (720, 1200), (540, 960), (0, 0)],
)
def test_rejects_landscape_wrong_ratio_or_too_small(width, height):
    with pytest.raises(ValueError, match="must be portrait 9:16 at least 720x1280"):
        validate_shorts_dimensions(width, height)


def test_probe_reads_and_validates_actual_video_dimensions(tmp_path: Path, monkeypatch):
    video = tmp_path / "vertical.mp4"
    video.write_bytes(b"placeholder")

    class Result:
        stdout = json.dumps({"streams": [{"width": 1080, "height": 1920}]})

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert probe_video_dimensions(video)["aspect_ratio"] == 0.5625
    assert "ffprobe" == captured["command"][0]
    assert str(video) == captured["command"][-1]


def test_probe_fails_if_video_stream_is_missing(tmp_path: Path, monkeypatch):
    video = tmp_path / "no-video.mp4"
    video.write_bytes(b"placeholder")

    class Result:
        stdout = '{"streams": []}'

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Result())
    with pytest.raises(ValueError, match="no video stream"):
        probe_video_dimensions(video)
