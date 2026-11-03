import json

import pytest

from app.bamo_ai_director import _parse_json, direct_scene, validate_scene_graph


def valid_graph():
    return {
        "visual_thesis": "Two objects exchange energy across a visible connection",
        "camera": {"move": "orbit", "angle": "high", "focus": "central sphere"},
        "palette": {"background": "#07111f", "key": "#35b8e8", "accent": "#e6ad52"},
        "objects": [
            {"id": "source_a", "kind": "sphere", "role": "first source", "position": [-2, 0, 1], "scale": [0.8, 0.8, 0.8], "rotation": [0, 0, 0], "material": "key", "action": "pulse", "action_amount": 1},
            {"id": "source_b", "kind": "sphere", "role": "second source", "position": [2, 0, 1], "scale": [0.8, 0.8, 0.8], "rotation": [0, 0, 0], "material": "accent", "action": "pulse", "action_amount": 1},
            {"id": "field", "kind": "torus", "role": "shared field", "position": [0, 0, 1], "scale": [2, 2, 0.08], "rotation": [0, 0, 0], "material": "neutral", "action": "rotate", "action_amount": 1.2},
        ],
        "relationships": [{"from": "source_a", "to": "field", "kind": "connect"}],
    }


def test_scene_graph_validation_accepts_semantic_composition():
    plan = validate_scene_graph(valid_graph())
    assert len(plan["objects"]) == 3
    assert plan["camera"]["move"] == "orbit"
    assert plan["relationships"][0]["kind"] == "connect"


def test_scene_graph_rejects_unsafe_or_unsupported_commands():
    graph = valid_graph()
    graph["objects"][0]["kind"] = "execute_python"
    with pytest.raises(ValueError, match="unsupported object kind"):
        validate_scene_graph(graph)


def test_scene_graph_rejects_duplicate_ids():
    graph = valid_graph()
    graph["objects"][1]["id"] = graph["objects"][0]["id"]
    with pytest.raises(ValueError, match="unique snake_case"):
        validate_scene_graph(graph)


def test_scene_graph_rejects_relationships_to_missing_objects():
    graph = valid_graph()
    graph["relationships"][0]["to"] = "missing"
    with pytest.raises(ValueError, match="invalid objects"):
        validate_scene_graph(graph)


def test_json_parser_accepts_fenced_json():
    fence = chr(96) * 3
    assert _parse_json(fence + "json\n" + json.dumps(valid_graph()) + "\n" + fence)["visual_thesis"].startswith("Two objects")


def test_director_generates_per_scene_graph(monkeypatch):
    response = json.dumps(valid_graph())
    monkeypatch.setattr("app.bamo_ai_director.generate_text", lambda *a, **k: (response, "test:director"))
    plan = direct_scene(narration="دو منبع انرژی با هم برهم‌کنش دارند", visual_brief="two energy sources interact")
    assert plan["motif"] == "ai_scene"
    assert plan["provider"] == "test:director"
    assert plan["narration_exact"] == "دو منبع انرژی با هم برهم‌کنش دارند"