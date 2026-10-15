from app import spiritual_tts


def test_piper_environment_setting_falls_back_to_male_voice_by_default(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "piper")
    monkeypatch.delenv("ALLOW_FEMALE_TTS", raising=False)
    assert spiritual_tts._provider() == "edge-tts"
    assert spiritual_tts._voice("edge-tts") == "fa-IR-FaridNeural"


def test_piper_from_channel_config_also_respects_male_voice_policy(monkeypatch):
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    monkeypatch.delenv("ALLOW_FEMALE_TTS", raising=False)
    monkeypatch.setattr(
        spiritual_tts,
        "load_channel_config",
        lambda: {"channel": {"tts_model": "piper", "tts_voice": "fa-IR-FaridNeural"}},
    )
    assert spiritual_tts._provider() == "edge-tts"


def test_piper_requires_explicit_opt_in_to_female_mana_voice(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "piper")
    monkeypatch.setenv("ALLOW_FEMALE_TTS", "true")
    assert spiritual_tts._provider() == "piper"
