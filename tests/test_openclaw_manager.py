from __future__ import annotations

import json

import pytest

from scripts.openclaw_manager import (
    ManagerError, _agent_json, _agent_review_decision, _configure_local_gateway, _has_cloud_model_credentials,
    _redact_secrets, _validated_agent_brief, REVIEW_PROMPT, parse_json_object, validate_brief,
    _parse_reviewer_decision,
)


def test_manager_accepts_cloudflare_credentials_only_when_both_values_are_present(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    assert _has_cloud_model_credentials()
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID")
    assert not _has_cloud_model_credentials()


def test_local_gateway_is_loopback_only_and_does_not_create_a_token(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return ""

    monkeypatch.setattr("scripts.openclaw_manager._run_command", fake_run)
    _configure_local_gateway()
    config = json.loads(captured["command"][4])
    assert config == {"mode": "local", "bind": "loopback", "auth": {"mode": "none"}}
    assert "token" not in config["auth"]


def test_gateway_diagnostic_redacts_cloudflare_secret(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-cloudflare-secret")
    assert _redact_secrets("failed token=test-cloudflare-secret") == "failed token=[REDACTED]"


def test_parse_json_object_accepts_a_fenced_object() -> None:
    assert parse_json_object('```json\n{"topic":"توکل آرام"}\n```') == {"topic": "توکل آرام"}


def test_parse_json_object_extracts_object_from_model_preamble_and_trailer() -> None:
    assert parse_json_object('پاسخ پیشنهادی:\n{"topic":"توکل آرام"}\nموفق باشید.') == {"topic": "توکل آرام"}


def test_agent_json_retries_once_after_non_json_response(monkeypatch):
    outputs = iter(["متن بدون JSON", '{"topic":"توکل آرام"}'])
    roles = []

    def fake_run_agent(_agent_id, _prompt, *, role, timeout=150):
        roles.append(role)
        return next(outputs)

    monkeypatch.setattr("scripts.openclaw_manager._run_agent", fake_run_agent)
    assert _agent_json("editorial-writer", "return JSON", role="writer") == {"topic": "توکل آرام"}
    assert roles == ["writer", "writer JSON retry"]


def test_invalid_brief_gets_one_repair_without_weakening_validation(monkeypatch):
    invalid = {
        "topic": "این یک موضوع فارسی با تعداد واژه‌های بسیار زیاد است",
        "hook_angle": "یک پرسش کوتاه؟",
        "visual_direction": "تصویر عمودی از نوشتن برنامهٔ روز",
        "emotional_arc": "کنجکاوی؛ همدلی؛ اقدام؛ امید",
        "audience_value": "یک تمرین کوتاه",
    }
    repaired = {**invalid, "topic": "آرامش در کار روزانه"}
    monkeypatch.setattr("scripts.openclaw_manager._agent_json", lambda *_args, **_kwargs: repaired)
    assert _validated_agent_brief("editorial-writer", invalid, role="writer")["topic"] == "آرامش در کار روزانه"


def test_reviewer_uses_a_single_decision_token_and_cannot_skip_approval():
    assert "APPROVE or REJECT" in REVIEW_PROMPT
    assert "only if every criterion passes" in REVIEW_PROMPT
    assert _parse_reviewer_decision("APPROVE") is True
    assert _parse_reviewer_decision("REJECT") is False
    with pytest.raises(ManagerError, match="exactly APPROVE or REJECT"):
        _parse_reviewer_decision("APPROVE because the brief is good")


def test_reviewer_retries_once_for_non_token_response(monkeypatch):
    outputs = iter(["The brief looks good.", "APPROVE"])
    roles = []

    def fake_run_agent(_agent_id, _prompt, *, role, timeout=150):
        roles.append(role)
        return next(outputs)

    monkeypatch.setattr("scripts.openclaw_manager._run_agent", fake_run_agent)
    assert _agent_review_decision("editorial-reviewer", "review", timeout=20) is True
    assert roles == ["reviewer", "reviewer decision retry"]


def test_validate_brief_requires_all_short_fields() -> None:
    valid = {
        "topic": "توکل در کار روزانه",
        "hook_angle": "وقتی نتیجه دیر می‌رسد، چطور آرام بمانیم؟",
        "visual_direction": "Vertical footage of a person planning their day in a notebook",
        "emotional_arc": "curiosity; empathy; action; hope",
        "audience_value": "یک تمرین کوتاه برای شروع روز",
    }
    assert validate_brief(valid) == valid


def test_validate_brief_rejects_non_persian_topic():
    valid = {
        "topic": "Daily Calm",
        "hook_angle": "A short question?",
        "visual_direction": "Vertical footage",
        "emotional_arc": "curiosity; empathy; action; hope",
        "audience_value": "One practical step",
    }
    with pytest.raises(ManagerError, match="written in Persian"):
        validate_brief(valid)


def test_validate_brief_rejects_missing_or_oversized_fields() -> None:
    with pytest.raises(ManagerError, match="field missing or invalid"):
        validate_brief({"topic": "توکل"})
    valid = {
        "topic": "توکل آرام",
        "hook_angle": "x" * 221,
        "visual_direction": "Vertical footage",
        "emotional_arc": "curiosity; empathy; action; hope",
        "audience_value": "one practical benefit",
    }
    with pytest.raises(ManagerError, match="hook or visual direction"):
        validate_brief(valid)
