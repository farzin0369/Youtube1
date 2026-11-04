import json

import pytest

from app.bamo_ai_director import (
    _parse_json, direct_scene, ensure_distinct_camera_moves, normalize_scene_graph, validate_scene_graph,
)


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


def test_scene_graph_soft_drops_relationships_to_missing_objects():
    """Local LLMs often emit stale relationship IDs; drop the edge, keep the graph."""
    graph = valid_graph()
    graph["relationships"][0]["to"] = "missing"
    plan = validate_scene_graph(graph)
    assert plan["relationships"] == []
    assert len(plan["objects"]) == 3


def test_normalize_drops_only_stale_relationship_edges():
    graph = valid_graph()
    graph["relationships"].append({"from": "source_a", "to": "stale_shell_id", "kind": "orbit"})
    normalized = normalize_scene_graph(graph)
    plan = validate_scene_graph(normalized)
    assert normalized["relationships"] == [{"from": "source_a", "to": "field", "kind": "connect"}]


def test_normalize_maps_construction_material_to_supported_neutral_role():
    graph = valid_graph()
    graph["objects"][0]["material"] = "construction"
    plan = validate_scene_graph(normalize_scene_graph(graph))
    assert plan["objects"][0]["material"] == "neutral"


def test_json_parser_accepts_fenced_json():
    fence = chr(96) * 3
    assert _parse_json(fence + "json\n" + json.dumps(valid_graph()) + "\n" + fence)["visual_thesis"].startswith("Two objects")


def test_director_generates_per_scene_graph(monkeypatch):
    response = json.dumps(valid_graph())
    replies = iter([
        (response, "test:director"),
        (json.dumps({"score": 94, "verdict": "pass", "issues": [], "revision_brief": ""}), "test:critic"),
    ])
    monkeypatch.setattr("app.bamo_ai_director.generate_text", lambda *a, **k: next(replies))
    plan = direct_scene(narration="دو منبع انرژی با هم برهم‌کنش دارند", visual_brief="two energy sources interact")
    assert plan["motif"] == "ai_scene"
    assert plan["provider"] == "test:director"
    assert plan["semantic_review_score"] == 94
    assert plan["critic_provider"] == "test:critic"
    assert plan["narration_exact"] == "دو منبع انرژی با هم برهم‌کنش دارند"


def test_director_rejects_semantic_score_below_prompt_threshold(monkeypatch):
    response = json.dumps(valid_graph())
    low = json.dumps({"score": 84, "verdict": "pass", "issues": ["mechanism missing"], "revision_brief": "show the exchange"})
    replies = iter([
        (response, "test:director"),
        (low, "test:critic"),
        (response, "test:revision"),
        (low, "test:critic-2"),
    ])
    monkeypatch.setattr("app.bamo_ai_director.generate_text", lambda *a, **k: next(replies))
    with pytest.raises(ValueError, match="rejected its own semantic composition"):
        direct_scene(narration="دو منبع انرژی با هم برهم‌کنش دارند", visual_brief="two energy sources interact")


def test_parser_repairs_missing_comma_seen_in_actions_run():
    graph = valid_graph()
    raw = json.dumps(graph, ensure_ascii=False, indent=2)
    broken = raw.replace(',\n  "palette"', '\n  "palette"', 1)
    assert broken != raw
    parsed = _parse_json(broken)
    assert parsed["palette"]["key"] == "#35b8e8"


def test_parser_accepts_trailing_commas():
    raw = json.dumps(valid_graph())
    broken = raw.replace("[-2, 0, 1]", "[-2, 0, 1,]", 1)
    assert _parse_json(broken)["camera"]["move"] == "orbit"


def test_director_clamps_out_of_range_action_amount_without_second_model_call(monkeypatch):
    graph = valid_graph()
    graph["objects"][0]["action_amount"] = 12.5
    graph["objects"][0]["position"] = [9, -8, 1]
    graph["objects"][2]["id"] = "Shell-3"
    graph["relationships"][0]["to"] = "Shell-3"
    calls = {"n": 0}

    def fake_generate(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return json.dumps(graph), "ollama:qwen2.5:7b"
        return json.dumps({"score": 91, "verdict": "pass", "revision_brief": ""}), "ollama:qwen2.5:7b"

    monkeypatch.setattr("app.bamo_ai_director.generate_text", fake_generate)
    plan = direct_scene(
        narration="پوسته‌های ستاره‌ای دور ناظر می‌چرخند",
        visual_brief="3D astronomical star distribution shells",
    )
    assert calls["n"] == 2
    assert plan["objects"][0]["action_amount"] == 4
    assert plan["objects"][0]["position"] == [6, -6, 1]
    assert plan["objects"][2]["id"] == "shell_3"
    assert plan["relationships"][0]["to"] == "shell_3"
    assert plan["semantic_review_score"] == 91


def test_normalize_does_not_invent_objects_or_accept_code_execution():
    graph = valid_graph()
    graph["objects"] = graph["objects"][:2]
    with pytest.raises(ValueError, match="3-12"):
        validate_scene_graph(normalize_scene_graph(graph))
    unsafe = valid_graph()
    unsafe["objects"][0]["kind"] = "execute_python"
    with pytest.raises(ValueError, match="unsupported object kind"):
        validate_scene_graph(normalize_scene_graph(unsafe))


def test_duplicate_camera_moves_are_reassigned_without_dropping_the_first_choice():
    plans = []
    for _ in range(4):
        graph = valid_graph()
        graph["camera"]["move"] = "orbit"
        plans.append(validate_scene_graph(graph))
    ensure_distinct_camera_moves(plans)
    moves = [plan["camera"]["move"] for plan in plans]
    assert moves[0] == "orbit"
    assert len(set(moves)) == 4
    assert "camera_diversified_from" not in plans[0]
    assert plans[1]["camera_diversified_from"] == "orbit"
