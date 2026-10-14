from app.emotion_tagger import classify_emotion, scene_delivery_hint, segment_and_tag
from app.spiritual_tts import _delivery


def test_segment_and_tag_splits_on_punctuation():
    segments = segment_and_tag("آرام باش. امید داشته باش!")
    assert len(segments) >= 2
    assert all("emotion" in row and "text" in row for row in segments)


def test_classify_emotion_detects_calm_language():
    result = classify_emotion("آرام باش و نفس عمیق بکش.")
    assert result["emotion"] in {"calm", "reassuring", "neutral"}


def test_classify_emotion_detects_motivational_language():
    result = classify_emotion("با اراده جلو برو و امیدت را نگه دار.")
    assert result["emotion"] in {"motivational", "joyful", "neutral"}


def test_scene_delivery_hint_aggregates_segments():
    segments = [
        {"text": "آرام باش.", "emotion": "calm", "intensity": 0.6, "confidence": 0.8, "pace": "steady"},
        {"text": "امید داشته باش.", "emotion": "motivational", "intensity": 0.7, "confidence": 0.7, "pace": "up"},
    ]
    hint = scene_delivery_hint(segments)
    assert "emotion" in hint
    assert "pause_after_ms" in hint


def test_ambiguous_text_defaults_to_neutral():
    result = classify_emotion("کتاب روی میز است.")
    assert result["emotion"] == "neutral"
    assert result["intensity"] <= 0.4


def test_short_emotion_label_changes_tts_controls_conservatively():
    angry = _delivery("calm", {"emotion": "angry", "intensity": 0.8, "confidence": 0.9})
    calm = _delivery("calm", {"emotion": "calm", "intensity": 0.8, "confidence": 0.9})
    neutral = _delivery("calm", {"emotion": "neutral", "intensity": 0.0, "confidence": 0.0})
    assert angry != calm
    # Edge TTS rejects fractional rates like +4.4%; production uses integers.
    assert neutral == ("-8%", "-2Hz")
    assert abs(float(angry[0].rstrip("%"))) <= 10
    assert abs(float(angry[1].rstrip("Hz"))) <= 3
