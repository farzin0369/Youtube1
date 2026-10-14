from __future__ import annotations

import json

import pytest

from scripts.openclaw_manager import (
    ManagerError, _configure_local_gateway, _has_cloud_model_credentials, _redact_secrets,
    parse_json_object, validate_brief,
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


def test_validate_brief_requires_all_short_fields() -> None:
    valid = {
        "topic": "توکل در کار روزانه",
        "hook_angle": "وقتی نتیجه دیر می‌رسد، چطور آرام بمانیم؟",
        "visual_direction": "Vertical footage of a person planning their day in a notebook",
        "emotional_arc": "curiosity; empathy; action; hope",
        "audience_value": "یک تمرین کوتاه برای شروع روز",
    }
    assert validate_brief(valid) == valid


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
