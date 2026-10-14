from __future__ import annotations

import pytest

from scripts.openclaw_manager import (
    ManagerError, _has_cloud_model_credentials, parse_json_object, validate_brief,
)


def test_manager_accepts_cloudflare_credentials_only_when_both_values_are_present(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    assert _has_cloud_model_credentials()
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID")
    assert not _has_cloud_model_credentials()


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
