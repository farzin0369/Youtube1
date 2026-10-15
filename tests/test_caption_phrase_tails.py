import logging

from app import spiritual_tts
from app.spiritual_tts import absorb_orphan_caption_tails


def test_piper_setting_keeps_the_male_farid_voice(monkeypatch, caplog):
    monkeypatch.setenv("TTS_PROVIDER", "piper")
    monkeypatch.delenv("ALLOW_FEMALE_TTS", raising=False)
    with caplog.at_level(logging.WARNING):
        assert spiritual_tts._provider() == "edge-tts"
    assert "female" in caplog.text.lower()
    assert spiritual_tts._voice("edge-tts") == "fa-IR-FaridNeural"


def test_channel_yaml_piper_also_falls_back_to_farid(monkeypatch):
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    monkeypatch.delenv("ALLOW_FEMALE_TTS", raising=False)
    monkeypatch.setattr(
        spiritual_tts,
        "load_channel_config",
        lambda: {"channel": {"tts_model": "piper", "tts_voice": "fa-IR-FaridNeural"}},
    )
    assert spiritual_tts._provider() == "edge-tts"


def test_female_piper_requires_an_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "piper")
    monkeypatch.setenv("ALLOW_FEMALE_TTS", "true")
    assert spiritual_tts._provider() == "piper"


def test_single_word_tails_rejoin_the_previous_phrase():
    cues = [
        (1.486, 2.972, "آیا تلاشت بی معنا"),
        (2.972, 3.344, "بوده؟"),
        (4.979, 6.314, "از کار خوب می"),
        (6.314, 6.648, "گیرد."),
        (13.812, 15.600, "دل سپاری همراه تلاش"),
        (15.600, 16.047, "است."),
    ]
    merged = absorb_orphan_caption_tails(cues)
    assert [text for _, _, text in merged] == [
        "آیا تلاشت بی معنا بوده؟",
        "از کار خوب می گیرد.",
        "دل سپاری همراه تلاش است.",
    ]


def test_sentence_break_and_pause_stay_separate():
    cues = [
        (0.0, 1.2, "توکل، عجله نیست."),
        (1.2, 2.4, "است."),
        (3.0, 4.0, "یک مکث"),
        (4.4, 4.8, "کوتاه"),
    ]
    merged = absorb_orphan_caption_tails(cues)
    assert [text for _, _, text in merged] == [
        "توکل، عجله نیست.",
        "است.",
        "یک مکث",
        "کوتاه",
    ]
