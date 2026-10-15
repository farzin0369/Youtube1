from app.emotion_tagger import classify_emotion, segment_and_tag
from app.spiritual_tts import _delivery


def test_sentence_segmentation_preserves_source_and_offsets():
    text = "خسته‌ای؟ امشب فقط یک کار کوچک انجام بده. فردا ادامه بده!"
    segments = segment_and_tag(text)
    assert [row["text"] for row in segments] == [
        "خسته‌ای؟", "امشب فقط یک کار کوچک انجام بده.", "فردا ادامه بده!",
    ]
    assert all(text[row["start_char"]:row["end_char"]] == row["text"] for row in segments)


def test_classifier_detects_motivational_language_and_intensity():
    result = classify_emotion("تسلیم نشو، بلند شو و ادامه بده!")
    assert result["emotion"] == "motivational"
    assert 0.0 <= result["intensity"] <= 1.0
    assert result["confidence"] > 0.5
    assert result["pace"] == "brisk"


def test_classifier_detects_reassuring_and_calm_language():
    reassuring = classify_emotion("نگران نباش، لازم نیست کامل باشی.")
    calm = classify_emotion("آرام نفس بکش و کمی مکث کن.")
    assert reassuring["emotion"] == "reassuring"
    assert calm["emotion"] == "calm"
    assert reassuring["pause_after_ms"] >= 300


def test_ambiguous_text_defaults_to_neutral():
    result = classify_emotion("کتاب روی میز است.")
    assert result["emotion"] == "neutral"
    assert result["intensity"] <= 0.4


def test_short_emotion_label_changes_tts_controls_conservatively():
    angry = _delivery("calm", {"emotion": "angry", "intensity": 0.8, "confidence": 0.9})
    calm = _delivery("calm", {"emotion": "calm", "intensity": 0.8, "confidence": 0.9})
    neutral = _delivery("calm", {"emotion": "neutral", "intensity": 0.0, "confidence": 0.0})
    assert angry != calm
    # clearer_v3 calm baseline
    assert neutral == ("-8%", "-1Hz")
    assert abs(float(angry[0].rstrip("%"))) <= 10
    assert abs(float(angry[1].rstrip("Hz"))) <= 3
