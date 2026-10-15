import pytest

from app import spiritual_tts
from app.spiritual_tts import absorb_orphan_caption_tails, clamp_caption_cues_to_duration


def test_piper_setting_stays_offline_and_uses_mana_voice(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "piper")
    monkeypatch.delenv("ALLOW_FEMALE_TTS", raising=False)
    assert spiritual_tts._provider() == "piper"
    assert spiritual_tts._voice("piper") == "fa_IR-mana-medium.onnx"


def test_channel_yaml_piper_stays_offline(monkeypatch):
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    monkeypatch.delenv("ALLOW_FEMALE_TTS", raising=False)
    monkeypatch.setattr(
        spiritual_tts,
        "load_channel_config",
        lambda: {"channel": {"tts_model": "piper", "tts_voice": "fa_IR-mana-medium.onnx"}},
    )
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


def test_caption_end_is_clamped_to_actual_audio_duration():
    cues = [(15.600, 16.047, "دل سپاری همراه تلاش است.")]
    assert clamp_caption_cues_to_duration(cues, 15.840) == [
        (15.600, 15.840, "دل سپاری همراه تلاش است.")
    ]


def test_caption_start_past_audio_duration_fails_loudly():
    with pytest.raises(ValueError, match="starts after audio ends"):
        clamp_caption_cues_to_duration([(15.9, 16.1, "است.")], 15.84)


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
