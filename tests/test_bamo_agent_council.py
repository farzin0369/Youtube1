from pathlib import Path

import pytest

from app import bamo_agent_council as council


def _good_review():
    return (
        '{"score": 92, "verdict": "approve", "critical_issues": [], '
        '"major_issues": [], "minor_issues": [], "evidence": ["reviewed package"], '
        '"suggestions": [], "confidence": 0.9}'
    )


def _fake_completion(base_url, api_key, model, system, prompt, **kwargs):
    return _good_review()


def test_council_uses_eleven_distinct_pinned_models(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setattr(council, "_chat_completions", _fake_completion)
    report = council.review_with_council(
        {"title": "BAMO | Test", "scenes": []},
        render={"visual_scene_count": 4, "visual_source": "bamo-cpu-3d-motion"},
        media_qa={"ok": True}, memory_dir=tmp_path,
    )
    assert report["ok"] is True
    assert report["agents_expected"] == report["agents_completed"] == 11
    assert report["approvals"] == 11
    assert report["distinct_base_models_observed"] == 11
    assert len(list(tmp_path.glob("*.json"))) == 11


def test_council_blocks_if_required_provider_key_missing(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(council, "_chat_completions", _fake_completion)
    with pytest.raises(RuntimeError, match="council blocked"):
        council.review_with_council(
            {"title": "BAMO | Test"}, render={}, media_qa={"ok": True}, memory_dir=tmp_path
        )


def test_council_blocks_on_critical_issue(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

    def critical(*args, **kwargs):
        return _good_review().replace(
            '"critical_issues": []',
            '"critical_issues": ["visual does not match narration"]'
        )

    monkeypatch.setattr(council, "_chat_completions", critical)
    with pytest.raises(RuntimeError, match="council blocked"):
        council.review_with_council(
            {"title": "BAMO | Test"}, render={}, media_qa={"ok": True}, memory_dir=tmp_path
        )
