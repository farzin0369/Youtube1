from pathlib import Path

import pytest

from app import bamo_agent_council as council


def _good_review(*args, **kwargs):
    return (
        '{"score": 92, "verdict": "approve", "critical_issues": [], '
        '"major_issues": [], "minor_issues": [], "evidence": ["reviewed package"], '
        '"suggestions": [], "confidence": 0.9}',
        "mock-provider:test-model",
    )


def test_council_runs_all_eleven_independent_roles(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(council, "generate_text", _good_review)
    report = council.review_with_council(
        {"title": "BAMO | Test", "scenes": []},
        render={"visual_scene_count": 4, "visual_source": "bamo-cpu-3d-motion"},
        media_qa={"ok": True}, memory_dir=tmp_path,
    )
    assert report["ok"] is True
    assert report["agents_expected"] == report["agents_completed"] == 11
    assert report["approvals"] == 11
    assert report["distinct_provider_models_observed"] == 1
    assert len(list(tmp_path.glob("*.json"))) == 11


def test_council_blocks_on_critical_issue(monkeypatch, tmp_path: Path):
    def critical(*args, **kwargs):
        raw, provider = _good_review()
        raw = raw.replace('"critical_issues": []', '"critical_issues": ["visual does not match narration"]')
        return raw, provider

    monkeypatch.setattr(council, "generate_text", critical)
    with pytest.raises(RuntimeError, match="council blocked"):
        council.review_with_council(
            {"title": "BAMO | Test"}, render={}, media_qa={"ok": True}, memory_dir=tmp_path
        )


def test_council_blocks_if_any_agent_fails(monkeypatch, tmp_path: Path):
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("offline")
        return _good_review()

    monkeypatch.setattr(council, "generate_text", flaky)
    with pytest.raises(RuntimeError, match="council blocked"):
        council.review_with_council(
            {"title": "BAMO | Test"}, render={}, media_qa={"ok": True}, memory_dir=tmp_path
        )
