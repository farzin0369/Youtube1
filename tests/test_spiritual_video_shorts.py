import shutil
import wave
from pathlib import Path

import pytest

from app import spiritual_video as video
from app.spiritual_tts import _delivery


def test_portrait_stock_picker_rejects_landscape_only_sources():
    landscape = {"video_files": [{"file_type": "video/mp4", "link": "landscape.mp4", "width": 1920, "height": 1080}]}
    portrait = {"video_files": [{"file_type": "video/mp4", "link": "portrait.mp4", "width": 720, "height": 1280}]}
    assert video._choose_file(landscape, orientation="portrait") is None
    assert video._choose_file(portrait, orientation="portrait")["link"] == "portrait.mp4"


def test_short_caption_ass_includes_a_separate_large_hook(tmp_path: Path):
    srt = tmp_path / "captions.srt"
    srt.write_text(
        "1\n00:00:00,150 --> 00:00:01,400\nتا حالا شده؟\n\n"
        "2\n00:00:01,500 --> 00:00:02,500\nفقط یک قدم\n",
        encoding="utf-8",
    )
    ass = video._write_shorts_ass(srt, tmp_path / "captions.ass", hook="یک قدم کافیست", duration=20)
    text = ass.read_text(encoding="utf-8")
    assert any(f"Style: Hook,Noto Naskh Arabic,{n}" in text for n in (92, 72, 70))
    assert any(f"Style: Default,Noto Naskh Arabic,{n}" in text for n in (72, 68, 64))
    assert "Dialogue: 1,0:00:00.00,0:00:02.80,Hook" in text
    assert "یک قدم کافیست" in text
    assert "Dialogue: 0,0:00:00.15,0:00:01.40,Default" in text
    assert "WrapStyle: 0" in text and "Kerning: yes" in text
    assert r"\fad(100,130)" in text and r"\fscx108\fscy108" in text
    assert r"\fad(90,70)" in text and r"\fscx104\fscy104" in text
    assert "تا حالا شده؟" in text and "فقط یک قدم" in text
    assert "؟ شده حالا تا" not in text


def test_scene_moods_have_audibly_distinct_tts_profiles():
    profiles = [_delivery(mood) for mood in ("hook", "calm", "reassuring", "motivational")]
    assert len(set(profiles)) == 4
    # clearer_v3: all slightly slow; calm is slowest
    assert profiles[1][0].startswith("-")
    rates = [float(p[0].rstrip("%")) for p in profiles]
    assert rates[1] <= rates[0]  # calm <= hook


def test_shorts_score_has_four_audio_beats(tmp_path: Path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    track = video._ambient_track(
        tmp_path / "score.wav", 4.0, 110, profile="shorts", scene_durations=[1, 1, 1, 1],
    )
    assert track.is_file() and track.stat().st_size > 10_000
    assert video.probe_duration(track) == pytest.approx(4.0, abs=0.1)


def test_short_renderer_falls_back_to_free_stills_when_stock_missing(tmp_path: Path, monkeypatch):
    audio = tmp_path / "audio.wav"
    with wave.open(str(audio), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(22_050)
        output.writeframes(b"\0\0" * 22_050)
    monkeypatch.setattr(video, "probe_duration", lambda path: 1.0)
    monkeypatch.setattr(video, "fetch_stock", lambda *args, **kwargs: ([], []))
    if hasattr(video, "fetch_mixkit_stock"):
        monkeypatch.setattr(video, "fetch_mixkit_stock", lambda *args, **kwargs: ([], []))
    if hasattr(video, "fetch_pollinations_stills"):
        monkeypatch.setattr(video, "fetch_pollinations_stills", lambda *args, **kwargs: ([], []))
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    (tmp_path / "captions.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nتست\n",
        encoding="utf-8",
    )
    result = video.render_video(
        title="test",
        thumbnail_text="تست کوتاه",
        keywords=[],
        audio_path=audio,
        captions_path=tmp_path / "captions.srt",
        out_dir=tmp_path / "render",
        run_id="test",
        video_format="shorts",
        scene_queries=["one scene query"] * 4,
    )
    assert Path(result["video_path"]).is_file()
    assert result.get("visual_scene_count") == 4
