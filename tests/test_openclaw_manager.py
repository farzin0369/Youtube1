from __future__ import annotations

import json

import pytest

from scripts.openclaw_manager import (
    BRIEF_RESPONSE_FORMAT, REVIEW_PROMPT, REVIEW_RESPONSE_FORMAT, ManagerError, _agent_json,
    _configure_local_gateway, _has_cloud_model_credentials, _redact_secrets, _run_agent,
    _validated_agent_brief, parse_json_object, validate_brief,
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

    def fake_run_agent(_agent_id, _prompt, *, role, response_format, timeout=150):
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


def test_reviewer_uses_a_single_boolean_json_schema_and_cannot_skip_approval():
    assert "one JSON object" in REVIEW_PROMPT
    assert "only if every criterion passes" in REVIEW_PROMPT
    assert REVIEW_RESPONSE_FORMAT["json_schema"]["required"] == ["approved"]
    assert REVIEW_RESPONSE_FORMAT["json_schema"]["properties"]["approved"] == {"type": "boolean"}


def test_run_agent_routes_to_loopback_gateway_with_cloudflare_json_schema(monkeypatch):
    captured = {}
    expected = {"topic": "توکل آرام", "hook_angle": "یک پرسش کوتاه؟", "visual_direction": "تصویر عمودی",
                "emotional_arc": "کنجکاوی؛ اقدام؛ امید", "audience_value": "یک تمرین"}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": json.dumps(expected, ensure_ascii=False)}}]}).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["model_header"] = request.get_header("X-openclaw-model") or request.get_header("x-openclaw-model")
        return FakeResponse()

    monkeypatch.setenv("OPENCLAW_MODEL", "cloudflare/@cf/meta/llama-3.1-8b-instruct-fast")
    monkeypatch.setattr("scripts.openclaw_manager.urllib.request.urlopen", fake_urlopen)
    raw = _run_agent(
        "editorial-researcher", "prepare a brief", role="researcher",
        response_format=BRIEF_RESPONSE_FORMAT, timeout=25,
    )
    assert json.loads(raw) == expected
    assert captured["url"] == "http://127.0.0.1:18789/v1/chat/completions"
    assert captured["body"]["model"] == "openclaw/editorial-researcher"
    assert captured["body"]["response_format"] == BRIEF_RESPONSE_FORMAT
    assert captured["model_header"] == "cloudflare/@cf/meta/llama-3.1-8b-instruct-fast"
    assert captured["timeout"] == 25


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
