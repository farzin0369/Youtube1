import copy
import json

import pytest

from app import spiritual_shorts
from app.spiritual_shorts import validate_short_content


def _short_package_data():
    scenes = [
        {
            "spoken_text": "آخر شب، ذهنت می‌گوید باید همه‌چیز را درست کنی؟",
            "mood": "hook",
            "visual_query": "person thinking beside rainy window at night",
            "on_screen_text": "فشارِ آخر شب",
        },
        {
            "spoken_text": "خستگی، کارها را بزرگ‌تر از واقعیت نشان می‌دهد.",
            "mood": "calm",
            "visual_query": "quiet notebook beside warm desk lamp",
            "on_screen_text": "وقتی ذهنت شلوغه",
        },
        {
            "spoken_text": "امشب فقط یک کار کوچک بردار و آرام انجامش بده.",
            "mood": "reassuring",
            "visual_query": "hand writing one small task in notebook",
            "on_screen_text": "فقط یک کار کوچک",
        },
        {
            "spoken_text": "فردا یک قدم دیگر؛ لازم نیست کامل باشی، فقط ادامه بده.",
            "mood": "motivational",
            "visual_query": "sunrise behind fresh green leaves close up",
            "on_screen_text": "ادامه بده",
        },
    ]
    script = " ".join(scene["spoken_text"] for scene in scenes)
    return {
        "topic": "یک اقدام کوچک پیش از خواب",
        "title": "Imam Ali ✨ از فشارِ همه‌چیز، به یک قدم واقعی",
        "hook": scenes[0]["spoken_text"],
        "description": "یک یادآوری آرام برای شروع از یک قدم کوچک.",
        "thumbnail_text": "یک قدم کافیست",
        "tags": ["عادت کوچک"],
        "scenes": scenes,
        "script": script,
    }


@pytest.fixture
def short_package():
    return _short_package_data()


def test_short_package_has_fast_hook_four_distinct_scenes_and_emotional_arc(short_package):
    result = validate_short_content(short_package)
    assert result["format"] == "shorts"
    assert result["word_count"] in range(36, 49)
    assert len(result["scenes"]) == 4
    assert [scene["mood"] for scene in result["scenes"]] == ["hook", "calm", "reassuring", "motivational"]
    assert result["script"] == " ".join(scene["spoken_text"] for scene in result["scenes"])
    assert {"ImamAli110", "The110Path", "امام علی"}.issubset(result["tags"])


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda x: x.update(script="مقدمهٔ طولانی و بی‌ربط." + x["script"]), "match_scene_narration"),
        (lambda x: x.update(hook="یک هوک متفاوت"), "hook_must_match"),
        (lambda x: (x["scenes"][0].update(spoken_text="سلام، " + x["scenes"][0]["spoken_text"]), x.update(script=" ".join(scene["spoken_text"] for scene in x["scenes"]))), "opening_has_a_slow_generic_intro"),
        (lambda x: x["scenes"][2].update(visual_query=x["scenes"][1]["visual_query"]), "visual_queries_must_be_distinct"),
        (lambda x: x["scenes"][3].update(mood="calm"), "emotional_arc"),
    ],
)
def test_short_gate_rejects_mismatch_or_weak_retention_signals(short_package, mutate, message):
    package = copy.deepcopy(short_package)
    mutate(package)
    with pytest.raises(ValueError, match=message):
        validate_short_content(package)


def test_short_gate_rejects_recently_used_title(short_package):
    with pytest.raises(ValueError, match="recent_title_repetition"):
        validate_short_content(short_package, [short_package["title"]])


def test_short_hook_must_not_start_with_generic_intro(short_package):
    package = copy.deepcopy(short_package)
    package["scenes"][0]["spoken_text"] = "سلام، " + package["scenes"][0]["spoken_text"]
    package["hook"] = package["scenes"][0]["spoken_text"]
    package["script"] = " ".join(scene["spoken_text"] for scene in package["scenes"])
    with pytest.raises(ValueError, match="opening_has_a_slow_generic_intro"):
        validate_short_content(package)


def test_invalid_model_draft_gets_one_corrective_rewrite(short_package, monkeypatch):
    calls = []

    def fake_generate_text(system, prompt, **kwargs):
        calls.append(prompt)
        if len(calls) == 1:
            return "{bad JSON", "test-provider"
        return json.dumps(short_package, ensure_ascii=False), "test-provider"

    monkeypatch.setattr(spiritual_shorts, "generate_text", fake_generate_text)
    result = spiritual_shorts.generate_shorts_content({"recent": []})
    assert result["format"] == "shorts"
    assert len(calls) == 2
    assert "اصلاح اجباری" in calls[1]
