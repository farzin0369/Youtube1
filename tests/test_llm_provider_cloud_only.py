from __future__ import annotations

import pytest

from app.llm_provider import LLMUnavailable, generate_text, provider_chain


def test_provider_chain_never_uses_local_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("GROQ_API_KEY", "GROQ_MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    # Even if stale local-model settings exist, they must not enable a local fallback.
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "qwen2.5:7b")

    assert provider_chain() == []
    with pytest.raises(LLMUnavailable, match="no cloud LLM provider configured"):
        generate_text("system", "prompt")


def test_cloud_provider_order_is_groq_then_generic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-generic-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    names = [name for name, _ in provider_chain()]
    assert names == ["groq:openai/gpt-oss-20b", "openai-compatible:test-model"]
    assert all("test-groq-key" not in name and "test-generic-key" not in name for name in names)
