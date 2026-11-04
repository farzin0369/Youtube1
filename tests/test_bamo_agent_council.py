from pathlib import Path

import pytest

from app import bamo_agent_council as council


def _good_review():
    return (
        '{"score": 92, "verdict": "approve", "critical_issues": [], '
        '"major_issues": [], "minor_issues": [], "evidence": ["reviewed package"], '
        '"suggestions": [], "confidence": 0.9}'
    )


def _fake_shared_completion(system, prompt, **kwargs):
    return _good_review(), "ollama:qwen2.5:3b"


def test_council_runs_eleven_independent_roles_without_paid_provider_keys(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("BAMO_USE_PINNED_AGENT_MODELS", "false")
    monkeypatch.setattr(council, "generate_text", _fake_shared_completion)
    monkeypatch.setattr(council, "_chat_completions", lambda *a, **kw: pytest.fail("pinned model must be opt-in"))

    report = council.review_with_council(
        {"title": "BAMO | Test", "scenes": []},
        render={"visual_scene_count": 4, "visual_source": "bamo-cpu-3d-motion"},
        media_qa={"ok": True}, memory_dir=tmp_path,
    )

    assert report["ok"] is True
    assert report["agents_expected"] == report["agents_completed"] == 11
    assert report["distinct_agent_roles_observed"] == 11
    assert report["approvals"] == 11
    assert report["distinct_model_ids_observed"] == 1
    assert {review["provider_model"] for review in report["independent_reviews"]} == {"ollama:qwen2.5:3b"}
    assert len(list(tmp_path.glob("*.json"))) == 11


def test_opted_in_pinned_models_use_credentials_when_available(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("BAMO_USE_PINNED_AGENT_MODELS", "true")
    monkeypatch.setattr(council, "_chat_completions", lambda *args, **kwargs: _good_review())
    monkeypatch.setattr(council, "generate_text", lambda *a, **kw: pytest.fail("pinned calls should succeed"))

    report = council.review_with_council(
        {"title": "BAMO | Test", "scenes": []},
        render={"visual_scene_count": 4, "visual_source": "bamo-cpu-3d-motion"},
        media_qa={"ok": True}, memory_dir=tmp_path,
    )
    assert report["ok"] is True
    assert report["distinct_agent_roles_observed"] == 11
    assert report["distinct_model_ids_observed"] == 11


def test_missing_optional_pinned_key_falls_back_instead_of_blocking(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("BAMO_USE_PINNED_AGENT_MODELS", "true")
    monkeypatch.setattr(council, "generate_text", _fake_shared_completion)
    monkeypatch.setattr(council, "_chat_completions", lambda *a, **kw: pytest.fail("must not call pinned model without a key"))

    report = council.review_with_council(
        {"title": "BAMO | Test"}, render={}, media_qa={"ok": True}, memory_dir=tmp_path
    )
    assert report["ok"] is True
    assert report["distinct_model_ids_observed"] == 1


def test_council_blocks_on_critical_issue_without_requiring_paid_keys(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    def critical(system, prompt, **kwargs):
        return _good_review().replace(
            '"critical_issues": []',
            '"critical_issues": ["visual does not match narration"]',
        ), "ollama:qwen2.5:3b"

    monkeypatch.setattr(council, "generate_text", critical)
    with pytest.raises(RuntimeError, match="council blocked"):
        council.review_with_council(
            {"title": "BAMO | Test"}, render={}, media_qa={"ok": True}, memory_dir=tmp_path
        )
