from app.agent_guard import validate_package


def _valid_news_package():
    script = " ".join(["گزارش"] * 350)
    urls = [
        "https://news.example/world",
        "https://news.example/technology",
        "https://news.example/economy",
    ]
    return {
        "title": "TT خبر | مرور خبرهای جهان",
        "description": "منابع خبری:\n" + "\n".join(urls),
        "script": script,
        "sources": urls,
        "tags": ["TT خبر", "اخبار جهان"],
        "duration_hint_seconds": 240,
        "scene_plan": [{
            "spoken_text": script,
            "visual_prompt": "Neutral global-news documentary B-roll, no text or logos",
            "on_screen_text": "مرور خبرهای جهان",
            "duration_hint_seconds": 240,
        }],
    }


def test_news_quality_gate_accepts_sourced_three_to_five_minute_script():
    result = validate_package(_valid_news_package(), "long")
    assert result["ok"] is True
    assert result["errors"] == []


def test_news_quality_gate_rejects_missing_source_urls():
    package = _valid_news_package()
    package["sources"] = ["news outlet"]
    result = validate_package(package, "long")
    assert result["ok"] is False
    assert "news_sources_must_be_urls" in result["errors"]


def test_news_quality_gate_rejects_short_news_script():
    package = _valid_news_package()
    package["script"] = "خبر کوتاه"
    package["scene_plan"][0]["spoken_text"] = "خبر کوتاه"
    result = validate_package(package, "long")
    assert result["ok"] is False
    assert any(error.startswith("news_script_word_count_outside") for error in result["errors"])
