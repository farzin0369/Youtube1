from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

from app import tts


def test_explicit_kitten_provider_writes_supported_language_wav(monkeypatch, tmp_path):
    calls = {}

    class FakeKittenTTS:
        sample_rate = 24000

        def __init__(self, model_name, **kwargs):
            calls["model_name"] = model_name
            calls["init_kwargs"] = kwargs

        def generate(self, text, **kwargs):
            calls["text"] = text
            calls["generate_kwargs"] = kwargs
            return np.full(2400, 0.1, dtype=np.float32)

    def fake_write(path, audio, sample_rate, subtype):
        calls["written_sample_rate"] = sample_rate
        calls["subtype"] = subtype
        with open(path, "wb") as target:
            target.write(b"RIFF" + (b"\x00" * 2048))

    monkeypatch.setitem(sys.modules, "kittenml", SimpleNamespace(KittenTTS=FakeKittenTTS))
    monkeypatch.setitem(sys.modules, "soundfile", SimpleNamespace(write=fake_write))
    monkeypatch.setenv("TTS_PROVIDER", "kitten")
    monkeypatch.delenv("KITTEN_TTS_MODEL", raising=False)
    monkeypatch.delenv("KITTEN_TTS_WEIGHTS", raising=False)
    monkeypatch.delenv("KITTEN_TTS_VOICE", raising=False)
    monkeypatch.delenv("KITTEN_TTS_PRESET", raising=False)

    result = tts.synthesize("Take a slow breath.", tmp_path / "sample.mp3")

    assert result["ok"] is True
    assert result["provider"] == "kitten-tts-2"
    assert result["path"].endswith("sample.wav")
    assert calls["model_name"] == "KittenML/kitten-tts-2"
    assert calls["init_kwargs"] == {"weights": "emb4"}
    assert calls["generate_kwargs"] == {"voice": "Bruno", "preset": "expressive"}
    assert calls["written_sample_rate"] == 24000
    assert (tmp_path / "sample.wav").stat().st_size > 1024


def test_kitten_provider_rejects_persian_instead_of_producing_bad_voice(monkeypatch, tmp_path):
    monkeypatch.setenv("TTS_PROVIDER", "kitten")

    with pytest.raises(RuntimeError, match="does not list Persian/Farsi"):
        tts.synthesize("به خدا توکل کن.", tmp_path / "persian.mp3")
