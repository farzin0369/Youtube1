import logging

from app import spiritual_tts


def test_configured_female_piper_falls_back_to_male_neural_voice(monkeypatch, caplog):
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    monkeypatch.delenv("ALLOW_FEMALE_TTS", raising=False)
    monkeypatch.delenv("TTS_VOICE", raising=False)
    monkeypatch.setattr(
        spiritual_tts,
        "load_channel_config",
        lambda: {"channel": {"tts_model": "piper", "tts_voice": "fa-IR-FaridNeural"}},
    )

    with caplog.at_level(logging.WARNING):
        assert spiritual_tts._provider() == "edge-tts"

    assert "female" in caplog.text.lower()
    assert spiritual_tts._voice("edge-tts") == "fa-IR-FaridNeural"


def test_piper_requires_explicit_opt_in_for_female_voice(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "piper")
    monkeypatch.delenv("ALLOW_FEMALE_TTS", raising=False)
    assert spiritual_tts._provider() == "edge-tts"

    monkeypatch.setenv("ALLOW_FEMALE_TTS", "true")
    assert spiritual_tts._provider() == "piper"


def test_provider_aliases_still_resolve(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "edge")
    assert spiritual_tts._provider() == "edge-tts"

    monkeypatch.setenv("TTS_PROVIDER", "eleven")
    assert spiritual_tts._provider() == "elevenlabs"
