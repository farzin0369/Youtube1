from pathlib import Path

import pytest

from app.weave_client import WeaveClient, WeaveError, scene_prompt


def test_scene_prompt_requires_narration():
    with pytest.raises(ValueError):
        scene_prompt("  ")


def test_scene_prompt_includes_scene_and_aspect_ratio():
    prompt = scene_prompt("A person quietly writing a gratitude journal", format_name="shorts")
    assert "A person quietly writing a gratitude journal" in prompt
    assert "9:16 vertical" in prompt
    assert "no text" in prompt


def test_inputs_use_prompt_and_published_defaults():
    inspect = {
        "inputs": [
            {"id": "prompt-id", "name": "Prompt", "type": "string", "default_value": None},
            {"id": "style-id", "name": "Style", "type": "selector", "default_value": {"type": "selector", "value": "cinematic"}},
        ]
    }
    inputs = WeaveClient._inputs_for_prompt(inspect, "test prompt")
    assert inputs[0] == {"id": "prompt-id", "value": {"type": "string", "value": "test prompt"}}
    assert inputs[1] == {"id": "style-id", "use_default": True}


def test_unknown_required_input_fails_closed():
    inspect = {
        "inputs": [
            {"id": "prompt-id", "name": "Prompt", "type": "string", "default_value": None},
            {"id": "required-id", "name": "Reference image", "type": "media", "default_value": None},
        ]
    }
    with pytest.raises(WeaveError):
        WeaveClient._inputs_for_prompt(inspect, "test prompt")


def test_missing_prompt_input_fails_closed():
    inspect = {
        "inputs": [
            {"id": "style-id", "name": "Style", "type": "selector", "default_value": {"type": "selector", "value": "cinematic"}},
        ]
    }
    with pytest.raises(WeaveError):
        WeaveClient._inputs_for_prompt(inspect, "test prompt")


def test_client_refuses_missing_token(monkeypatch):
    monkeypatch.delenv("WEAVE_API_TOKEN", raising=False)
    with pytest.raises(WeaveError, match="WEAVE_API_TOKEN"):
        WeaveClient()


def test_generation_is_disabled_by_default(monkeypatch, tmp_path):
    from app.weave_client import generate_scene_stills

    monkeypatch.setenv("WEAVE_TOOL_ID", "published-tool")
    monkeypatch.setenv("WEAVE_AUTO_RUN", "false")
    monkeypatch.setenv("WEAVE_API_TOKEN", "test-token")
    assert generate_scene_stills(["A calm forest at sunrise"], tmp_path) == []
    assert list(tmp_path.rglob("*")) == []


def test_unknown_format_uses_landscape_prompt():
    prompt = scene_prompt("A candle burning beside an open book", format_name="long")
    assert "16:9 landscape" in prompt
