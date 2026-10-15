"""Regression tests for staged script generation and provider fallback."""
import json

import pytest

from app import llm_provider, spiritual_content
from app.spiritual_content import (
    SECTION_COUNT,
    extract_json_object,
    generate_content,
    word_count,
)


def _persian_text(words: int, marker: str) -> str:
    """Build distinct Persian filler whose word count is exactly ``words``."""
    if not words:
        return ""
    marker = str(marker)
    hook = "فرض کن آخرِ ماه است؛ آیا می‌شود امروز یک قدم برداشت؟" if marker == "0" else ""
    tokens = [f"واژه{marker}نشان{index}" for index in range(max(0, words - len(hook.split())))]
    sentences = [hook] if hook else []
    sentences.extend(" ".join(tokens[index:index + 8]) + "." for index in range(0, len(tokens), 8))
    return " ".join(sentence for sentence in sentences if sentence)


def test_extract_json_object_tolerates_fences_prose_and_truncation():
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json_object('در اینجا خروجی است:\n{"a": [1, 2]}\nامیدوارم مفید باشد.') == {"a": [1, 2]}
    truncated = '{"title": "سلام", "sections": [{"heading": "یک"}, {"heading": "دو"'
    assert extract_json_object(truncated)["title"] == "سلام"
    with pytest.raises(ValueError):
        extract_json_object("هیچ شیء جیسونی اینجا نیست")


def test_generate_content_assembles_a_passing_script(monkeypatch):
    headings = [f"سرفصل شماره {index}" for index in range(SECTION_COUNT)]
    outline = {
        "title": "چگونه با توکل آرام‌تر پیش برویم",
        "thumbnail_text": "قدم آرام امروز",
        "description": "یک ویدئوی تأملی و کاربردی.",
        "tags": ["رشد فردی"],
        "visual_keywords": ["sunrise forest"],
        "sections": [{"heading": heading} for heading in headings],
    }

    def fake_generate_text(system, prompt, *, max_tokens=1200, temperature=0.6, json_mode=False, timeout=None):
        if json_mode:
            return json.dumps(outline, ensure_ascii=False), "stub"
        # Every section returns its own 130-word block, so the total is ~780 words.
        for index, heading in enumerate(headings):
            if heading in prompt:
                return _persian_text(130, index), "stub"
        return _persian_text(130, 99), "stub"

    monkeypatch.setattr(spiritual_content, "generate_text", fake_generate_text)
    content = generate_content({"recent": []})

    assert content["title"].startswith("Imam Ali ✨ ")
    assert len(content["sections"]) == SECTION_COUNT
    assert 650 <= content["word_count"] <= 900
    assert word_count(content["script"]) == content["word_count"]
    assert "ImamAli110" in content["tags"]


def test_generate_content_fails_closed_without_a_title(monkeypatch):
    def fake_generate_text(system, prompt, *, max_tokens=1200, temperature=0.6, json_mode=False, timeout=None):
        return json.dumps({"sections": [{"heading": "یک"}]}, ensure_ascii=False), "stub"

    monkeypatch.setattr(spiritual_content, "generate_text", fake_generate_text)
    with pytest.raises(ValueError, match="outline generation failed"):
        generate_content({"recent": []})


def test_word_budget_expands_a_section_that_is_too_short(monkeypatch):
    calls = {"count": 0}

    def fake_generate_text(system, prompt, *, max_tokens=1200, temperature=0.6, json_mode=False, timeout=None):
        calls["count"] += 1
        return _persian_text(130, calls["count"]), "stub"

    monkeypatch.setattr(spiritual_content, "generate_text", fake_generate_text)
    short = _persian_text(40, "x")
    fitted = spiritual_content._fit_word_budget("system", short, 130, rounds=1)
    assert word_count(fitted) >= 106
    assert calls["count"] == 1


def test_section_prompt_carries_repetition_guard():
    prompt = spiritual_content._section_prompt(
        title="عنوان", heading="سرفصل", index=2, total=6, target=130,
        previous_headings=["سرفصل یک"], previous_tail="جملهٔ پایانی.", avoid=["یک جملهٔ تکراری بلند"],
    )
    assert "یک جملهٔ تکراری بلند" in prompt
    assert "سرفصل یک" in prompt


def test_prompt_echo_is_detected_and_dropped():
    leaked = (
        "قواعد: فقط متن گفتاری بده. "
        "هر روز صبح سه دقیقه بنشین و نفس عمیق بکش. "
        "هدف: یک متن گفتاری روان بنویس که از ۱۱۰ واژه کمتر نباشد."
    )
    assert spiritual_content.INSTRUCTION_LEAK.search(leaked)
    cleaned = spiritual_content._drop_leaks(leaked)
    assert cleaned == "هر روز صبح سه دقیقه بنشین و نفس عمیق بکش."
    assert not spiritual_content.INSTRUCTION_LEAK.search(cleaned)


def test_clean_prose_removes_markdown_and_heading_echo():
    raw = "**تمرین ۱: یک قدم کوچک**\nیک قدم کوچک: هر روز صبح دفترچه‌ات را باز کن."
    cleaned = spiritual_content._clean_prose(raw, heading="تمرین ۱: یک قدم کوچک")
    assert cleaned.startswith("هر روز صبح")
    assert "**" not in cleaned


def test_section_rules_are_not_placed_in_the_user_prompt():
    prompt = spiritual_content._section_prompt(
        title="عنوان", heading="سرفصل", index=1, total=6, target=130,
        previous_headings=[], previous_tail="", avoid=[],
    )
    assert "قواعد:" not in prompt
    assert "هدف:" not in prompt
    assert "قواعد نوشتن هر بخش" in spiritual_content.SECTION_RULES


def test_no_cloud_provider_fails_closed_without_local_fallback(monkeypatch):
    for name in ("GROQ_API_KEY", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "qwen2.5:7b")
    with pytest.raises(llm_provider.LLMUnavailable, match="no cloud LLM provider configured"):
        llm_provider.generate_text("system", "prompt")


def test_groq_is_preferred_when_configured(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://generic.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "generic-test-key")
    monkeypatch.setenv("LLM_MODEL", "generic-model")
    monkeypatch.setattr(llm_provider, "_chat_completions", lambda *a, **kw: "پاسخ ابری")
    text, provider = llm_provider.generate_text("system", "prompt")
    assert text == "پاسخ ابری"
    assert provider.startswith("groq:")


def test_cloud_failure_degrades_only_to_the_next_cloud_provider(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://generic.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "generic-test-key")
    monkeypatch.setenv("LLM_MODEL", "generic-model")

    def fail_groq_then_succeed_generic(base_url, api_key, model, *args, **kwargs):
        if base_url == llm_provider.GROQ_BASE_URL:
            raise RuntimeError("rate limited")
        return "پاسخ از جایگزین ابری"

    monkeypatch.setattr(llm_provider, "_chat_completions", fail_groq_then_succeed_generic)
    text, provider = llm_provider.generate_text("system", "prompt")
    assert text == "پاسخ از جایگزین ابری"
    assert provider == "openai-compatible:generic-model"


def test_every_cloud_provider_failing_raises(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://generic.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "generic-test-key")
    monkeypatch.setenv("LLM_MODEL", "generic-model")

    def broken(*args, **kwargs):
        raise RuntimeError("unavailable")

    monkeypatch.setattr(llm_provider, "_chat_completions", broken)
    with pytest.raises(llm_provider.LLMUnavailable, match="no LLM provider succeeded"):
        llm_provider.generate_text("system", "prompt")


def test_content_policy_file_is_valid_yaml():
    from app.utils import load_content_policy

    policy = load_content_policy()
    assert policy["brand"] == "ImamAli110"
    assert policy["secondary_brand"] == "#The110Path"
    assert isinstance(policy["rules"], list) and policy["rules"]
