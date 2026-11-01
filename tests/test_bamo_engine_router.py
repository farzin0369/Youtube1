from app.bamo_engine_router import route_for_genre, validate_agent_decision

def test_hyperframes_is_the_only_renderer_for_every_genre():
    for genre in ("science", "mathematics", "history", "comedy", "motion_graphics", "general"):
        route = route_for_genre(genre)
        assert route["primary_engine"] == "hyperframes"
        assert route["selected_engine"] == "hyperframes"
        assert route["compositor"] == "ffmpeg"

def test_agent_handoff_keeps_narration_and_visual_brief():
    result = validate_agent_decision({
        "genre": "science",
        "visual_brief": "A three-dimensional atom with an orbiting camera",
        "narration": "The atom is mostly empty space."
    })
    assert result["selected_engine"] == "hyperframes"
    assert "camera_motion_present" in result["quality_gates"]

def test_missing_agent_handoff_fails_closed():
    try:
        validate_agent_decision({"genre": "science", "visual_brief": "3D scene"})
    except ValueError as exc:
        assert "narration" in str(exc)
    else:
        raise AssertionError("Missing narration must fail closed")
