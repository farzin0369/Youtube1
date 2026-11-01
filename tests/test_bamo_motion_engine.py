import pytest

from app.bamo_motion_engine import validate_project
from app.bamo_scene_director import plan_scene
from scripts.run_bamo_first_film import ROLE_KEYS, validate_brief


def test_bamo_project_requires_authored_scenes():
    with pytest.raises(ValueError, match="non-empty scenes"):
        validate_project({"format": "short", "scenes": []})


def test_bamo_project_rejects_invalid_scene_duration():
    with pytest.raises(ValueError, match="between 0.5 and 60"):
        validate_project({"format": "short", "scenes": [{"duration": 0.1}]})


def test_scene_director_maps_physics_caption_to_3d_atom_and_orbit():
    plan = plan_scene("الکترون در اتم حرکت می‌کند")
    assert plan["motif"] == "atom"
    assert plan["camera"] == "orbit"


def test_scene_director_maps_geometry_caption_to_camera_sweep():
    plan = plan_scene("ساخت یک شکل هندسی در سه بعد")
    assert plan["motif"] == "geometry"
    assert plan["camera"] == "sweep"


def test_bamo_first_film_requires_all_eleven_role_handoffs():
    roles = {key: f"completed: {key}" for key in ROLE_KEYS}
    brief = {
        "title": "آزمایش BAMO",
        "hook": "یک پرسش شگفت‌انگیز",
        "narration": "متن آزمایشی",
        "scenes": [{"duration": 4, "text": f"صحنه {i}"} for i in range(4)],
        "roles": roles,
    }
    validate_brief(brief)
    assert len(ROLE_KEYS) == 11


def test_bamo_first_film_rejects_missing_role():
    roles = {key: f"completed: {key}" for key in ROLE_KEYS}
    roles.pop("analytics")
    brief = {
        "title": "آزمایش BAMO",
        "hook": "یک پرسش شگفت‌انگیز",
        "narration": "متن آزمایشی",
        "scenes": [{"duration": 4, "text": f"صحنه {i}"} for i in range(4)],
        "roles": roles,
    }
    with pytest.raises(ValueError, match="Exactly the 11"):
        validate_brief(brief)
