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

 
def test_cloudflare_configured_is_selected_in_cloud_only_mode(monkeypatch):
    values = {
        "LLM_REQUIRE_CLOUD": "true",
        "CLOUDFLARE_API_TOKEN": "fake-test-token",
        "CLOUDFLARE_ACCOUNT_ID": "fake-account",
        "CLOUDFLARE_AI_MODEL": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    }
    monkeypatch.setattr(llm_provider, "env", lambda name: values.get(name, ""))
    chain = llm_provider.provider_chain()
    assert chain
    assert chain[0][0] == "cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast"
