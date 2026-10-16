from __future__ import annotations

import pytest

from app import channel_ops
from app.llm_provider import LLMUnavailable


def test_comment_reply_uses_configured_cloud_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(channel_ops, "provider_chain", lambda: [("groq:test-model", lambda **_: "unused")])
    captured = {}

    def fake_generate(system: str, prompt: str, **kwargs: object) -> tuple[str, str]:
        captured["system"] = system
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "پاسخ محترمانه", "groq:test-model"

    monkeypatch.setattr(channel_ops, "generate_text", fake_generate)
    assert channel_ops._generate_reply("نظر آزمایشی") == "پاسخ محترمانه"
    assert "ImamAli110" in captured["system"]
    assert captured["kwargs"]["max_tokens"] == 220


def test_comment_reply_fails_closed_without_cloud_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(channel_ops, "provider_chain", lambda: [])
    with pytest.raises(LLMUnavailable, match="No cloud LLM configured"):
        channel_ops._generate_reply("نظر آزمایشی")
