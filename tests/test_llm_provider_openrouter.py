from app import llm_provider


def test_openrouter_free_model_is_configured_from_secret(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-secret")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    config = llm_provider._openrouter_config()

    assert config == (
        "https://openrouter.ai/api/v1",
        "test-secret",
        "minimax/minimax-m3.1-flash:free",
    )


def test_openrouter_provider_is_in_chain_without_logging_secret(monkeypatch, caplog):
    monkeypatch.setenv("OPENROUTER_API_KEY", "never-log-this-secret")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    chain = llm_provider.provider_chain()

    assert chain[0][0] == "openrouter:minimax/minimax-m3.1-flash:free"
    assert "never-log-this-secret" not in caplog.text
