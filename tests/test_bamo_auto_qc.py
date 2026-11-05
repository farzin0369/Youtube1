import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app import bamo_auto_qc as qc

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")


def _make(path, *, black=False, silent=False, seconds=10, size="270x480"):
    src = f"color=c=black:size={size}:rate=24" if black else f"testsrc2=size={size}:rate=24"
    audio = "anullsrc=r=44100:cl=mono" if silent else "sine=frequency=330:sample_rate=44100"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", src,
           "-f", "lavfi", "-i", audio, "-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", str(path)]
    assert subprocess.run(cmd).returncode == 0


def test_parsers():
    assert qc.parse_volumedetect("... mean_volume: -17.3 dB\n") == -17.3
    text = "silence_duration: 1.5\n...silence_duration: 0.5"
    assert qc.parse_silence_ratio(text, 10.0) == 0.2


def test_good_video_passes_and_bad_ones_fail_with_reasons():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        good, black, mute = tmp / "g.mp4", tmp / "b.mp4", tmp / "m.mp4"
        _make(good); _make(black, black=True, silent=True); _make(mute, silent=True)
        cap = tmp / "c.ass"; cap.write_text("[Script Info]\nTitle: x\nDialogue: 0,0:00:00.00", encoding="utf-8")
        ok = qc.qc_video(good, captions=cap, limits={"mean_volume_db": (-40.0, -3.0)})
        assert ok["ok"], ok["reasons"]
        bad = qc.qc_video(black, limits={"mean_volume_db": (-40.0, -3.0), "min_bytes": 1000})
        assert not bad["ok"] and {"frames_not_blank", "picture_changes", "hook_frame_visible"} <= set(bad["reasons"])
        quiet = qc.qc_video(mute, limits={"mean_volume_db": (-40.0, -3.0), "min_bytes": 1000})
        assert "dead_air" in quiet["reasons"] or "loudness" in quiet["reasons"]
        wide = tmp / "w.mp4"; _make(wide, size="480x270")
        assert "aspect" in qc.qc_video(wide, limits={"mean_volume_db": (-40.0, -3.0), "min_bytes": 1000})["reasons"]


def test_missing_or_tiny_file():
    assert qc.qc_video(Path("/nonexistent.mp4"))["reasons"] == ["file_missing_or_tiny"]
