from app import llm_provider


def test_cpu_ollama_is_preferred_when_explicitly_enabled(monkeypatch):
    monkeypatch.setattr(llm_provider, "_groq_config", lambda: None)
    monkeypatch.setattr(llm_provider, "_generic_config", lambda: None)
    monkeypatch.setattr(
        llm_provider, "env",
        lambda name, default=None: {
            "USE_LOCAL_LLM": "1",
            "LOCAL_LLM_MODEL": "qwen2.5:7b",
        }.get(name, default),
    )

    names = [name for name, _ in llm_provider.provider_chain()]
    assert names[0] == "ollama:qwen2.5:7b"
    assert names[-1] == "pollinations:openai"


def test_pollinations_remains_fallback_when_cpu_model_is_disabled(monkeypatch):
    monkeypatch.setattr(llm_provider, "_groq_config", lambda: None)
    monkeypatch.setattr(llm_provider, "_generic_config", lambda: None)
    monkeypatch.setattr(
        llm_provider, "env",
        lambda name, default=None: {"USE_LOCAL_LLM": "0"}.get(name, default),
    )

    names = [name for name, _ in llm_provider.provider_chain()]
    assert names == ["pollinations:openai"]
