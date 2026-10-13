from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import spiritual_tts


def test_fallback_creates_audio_captions_and_does_not_log_signed_url(tmp_path, monkeypatch, caplog):
    secret_url = "wss://speech.invalid/?Sec-MS-GEC=private-hash"

    async def edge_fails(_text, _audio_path):
        raise RuntimeError(secret_url)

    def fake_gtts(_text: str, audio_path: Path) -> None:
        audio_path.write_bytes(b"x" * 2048)

    monkeypatch.setattr(spiritual_tts, "_render_edge", edge_fails)
    monkeypatch.setattr(spiritual_tts, "_save_gtts", fake_gtts)
    monkeypatch.setattr(spiritual_tts, "_save_elevenlabs", lambda *_: (_ for _ in ()).throw(RuntimeError("not configured")))
    monkeypatch.setattr(spiritual_tts, "_save_pyttsx3", lambda *_: (_ for _ in ()).throw(RuntimeError("unavailable")))
    monkeypatch.setattr(spiritual_tts, "_audio_duration", lambda _path: 12.0)

    with caplog.at_level(logging.WARNING):
        result = spiritual_tts.synthesize_with_captions(
            "سلام، این فقط یک متن آزمایشی برای صدای فارسی است.",
            tmp_path / "voice.mp3",
            tmp_path / "voice.srt",
        )

    assert result["ok"] is True
    assert result["provider"] == "gtts"
    assert result["caption_mode"].startswith("estimated")
    assert result["caption_count"] > 0
    assert (tmp_path / "voice.mp3").stat().st_size == 2048
    assert "-->" in (tmp_path / "voice.srt").read_text(encoding="utf-8")
    assert secret_url not in caplog.text


def test_approximate_cues_cover_audio_duration():
    cues = spiritual_tts._approximate_phrase_cues("یک دو سه چهار پنج شش هفت", 9.0, max_words=3)
    assert cues[0][0] == 0.0
    assert cues[-1][1] == 9.0
    assert all(end > start for start, end, _ in cues)


def test_edge_tts_proxy_is_passed_to_client(tmp_path, monkeypatch):
    captured = {}

    class FakeCommunicate:
        def __init__(self, text, **kwargs):
            captured["text"] = text
            captured.update(kwargs)

        async def stream(self):
            yield {"type": "audio", "data": b"a" * 2048}
            yield {"type": "WordBoundary", "offset": 0, "duration": 5_000_000, "text": "سلام"}

    monkeypatch.setitem(sys.modules, "edge_tts", SimpleNamespace(Communicate=FakeCommunicate))
    monkeypatch.setattr(spiritual_tts, "_voice", lambda: "fa-IR-FaridNeural")
    monkeypatch.setattr(spiritual_tts, "env", lambda key: "http://127.0.0.1:8080" if key == "EDGE_TTS_PROXY" else "")

    import asyncio
    events = asyncio.run(spiritual_tts._render_edge("سلام", tmp_path / "voice.mp3"))

    assert captured["proxy"] == "http://127.0.0.1:8080"
    assert captured["boundary"] == "WordBoundary"
    assert len(events) == 1
    assert (tmp_path / "voice.mp3").stat().st_size == 2048
