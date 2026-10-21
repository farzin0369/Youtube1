"""Tests for strict cloud-only provider selection."""
from app import llm_provider


def test_cloud_required_disables_local_fallback(monkeypatch):
    values = {"LLM_REQUIRE_CLOUD": "true", "LOCAL_LLM_MODEL": "qwen2.5:7b"}
    monkeypatch.setattr(llm_provider, "env", lambda name: values.get(name, ""))
    assert llm_provider.provider_chain() == []


def test_cloud_required_keeps_configured_groq(monkeypatch):
    values = {
        "LLM_REQUIRE_CLOUD": "true",
        "GROQ_API_KEY": "fake-test-key",
        "GROQ_MODEL": "test-model",
    }
    monkeypatch.setattr(llm_provider, "env", lambda name: values.get(name, ""))
    chain = llm_provider.provider_chain()
    assert len(chain) == 1
    assert chain[0][0] == "groq:test-model"
