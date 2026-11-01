from app.bamo_engine_router import normalize_genre, route_for_genre, validate_agent_decision

def test_math_routes_to_manim():
    result = route_for_genre("mathematics")
    assert result["primary_engine"] == "manim"

def test_comedy_routes_to_blender():
    result = route_for_genre("humor")
    assert result["primary_engine"] == "blender"

def test_chemistry_routes_to_rdkit():
    assert route_for_genre("chemistry")["primary_engine"] == "rdkit"

def test_aliases_are_normalized():
    assert normalize_genre("math") == "mathematics"
    assert normalize_genre("funny") == "humor"

def test_unknown_genre_is_rejected():
    try:
        normalize_genre("random_visuals")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown genre must not silently fall back")

def test_agent_handoff_requires_visual_brief_and_narration():
    try:
        validate_agent_decision({"genre": "mathematics"})
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete director handoff must be rejected")
