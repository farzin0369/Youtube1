from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.llm_provider import LLMUnavailable, _chat_completions, generate_text, provider_chain


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


def test_cloudflare_uses_max_tokens_parameter() -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data.decode())
        captured["gateway_id"] = request.get_header("Cf-aig-gateway-id")
        return FakeResponse()

    with patch("app.llm_provider.urllib.request.urlopen", side_effect=fake_urlopen):
        answer = _chat_completions(
            "https://api.cloudflare.com/client/v4/accounts/test-account/ai/v1",
            "not-a-real-secret",
            "@cf/meta/llama-3.1-8b-instruct-fast",
            "system",
            "prompt",
            max_tokens=128,
            temperature=0.2,
            json_mode=False,
            timeout=1,
        )

    assert answer == "ok"
    assert captured["gateway_id"] == "default"
    body = captured["body"]
    assert body["max_tokens"] == 128
    assert "max_completion_tokens" not in body
