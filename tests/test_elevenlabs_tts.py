import base64

import pytest

from app import spiritual_tts


def test_provider_is_opt_in_and_accepts_legacy_edge_alias(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "elevenlabs")
    assert spiritual_tts._provider() == "elevenlabs"
    monkeypatch.setenv("TTS_PROVIDER", "edge")
    assert spiritual_tts._provider() == "edge-tts"
    monkeypatch.setenv("TTS_PROVIDER", "unknown")
    with pytest.raises(ValueError, match="unsupported TTS_PROVIDER"):
        spiritual_tts._provider()


def test_emotion_tags_are_added_only_above_confidence_threshold():
    tag, applied = spiritual_tts._elevenlabs_tagged_text(
        "ادامه بده.", {"emotion": "motivational", "intensity": 0.7, "confidence": 0.8},
    )
    assert tag == "[encouraging] ادامه بده."
    assert applied == "[encouraging]"
    plain, applied = spiritual_tts._elevenlabs_tagged_text(
        "شاید فردا بهتر شود.", {"emotion": "motivational", "intensity": 0.8, "confidence": 0.3},
    )
    assert plain == "شاید فردا بهتر شود."
    assert applied == ""


def test_alignment_to_word_events_ignores_nonspoken_v4_tag():
    aligned = "[encouraging] سلام دنیا"
    alignment = {
        "characters": list(aligned),
        "character_start_times_seconds": [i * 0.01 for i in range(len(aligned))],
        "character_end_times_seconds": [(i + 1) * 0.01 for i in range(len(aligned))],
    }
    events = spiritual_tts._alignment_word_events(alignment, "سلام دنیا")
    assert [event["text"] for event in events] == ["سلام", "دنیا"]
    assert events[0]["offset"] < events[1]["offset"]
    assert all(event["type"] == "WordBoundary" for event in events)


def test_elevenlabs_adapter_builds_authenticated_v4_request_and_writes_audio(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-secret")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice-123")
    monkeypatch.setenv("ELEVENLABS_MODEL_ID", "eleven_v4")
    expected = "سلام دنیا"
    tagged = "[calm] " + expected
    audio = b"x" * 2048
    alignment = {
        "characters": list(tagged),
        "character_start_times_seconds": [i * 0.01 for i in range(len(tagged))],
        "character_end_times_seconds": [(i + 1) * 0.01 for i in range(len(tagged))],
    }

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"audio_base64": base64.b64encode(audio).decode(), "alignment": alignment}

    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    output = tmp_path / "speech.mp3"
    events = spiritual_tts._render_elevenlabs(
        expected, output,
        hint={"emotion": "calm", "intensity": 0.5, "confidence": 0.9},
        previous_text="قبلی.", next_text="بعدی.",
    )
    assert output.read_bytes() == audio
    assert captured["url"].endswith("/voice-123/with-timestamps")
    assert captured["headers"]["xi-api-key"] == "test-secret"
    assert captured["params"]["output_format"] == "mp3_44100_128"
    assert captured["json"]["model_id"] == "eleven_v4"
    assert captured["json"]["language_code"] == "fa"
    assert captured["json"]["text"] == tagged
    assert captured["json"]["previous_text"] == "قبلی."
    assert [event["text"] for event in events] == ["سلام", "دنیا"]


def test_elevenlabs_requires_explicit_credentials(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        spiritual_tts._render_elevenlabs("سلام", __import__("pathlib").Path("unused.mp3"))
