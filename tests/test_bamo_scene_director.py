import pytest

from app.bamo_scene_director import plan_scene


def test_notebook_visual_query_uses_a_literal_notebook_scene():
    plan = plan_scene("او در دفترش می‌نویسد", "open notebook with a moving pen")
    assert plan["motif"] == "notebook"
    assert plan["camera"] == "push_in"


def test_sunrise_visual_query_does_not_use_abstract_portal():
    plan = plan_scene("خورشید طلوع می‌کند", "sunrise over a mountain horizon")
    assert plan["motif"] == "sunrise"


def test_growth_steps_are_not_selected_for_notebook_narration():
    plan = plan_scene("او هر روز یادداشت می‌نویسد", "writing in a notebook")
    assert plan["motif"] == "notebook"
    assert plan["motif"] != "growth_steps"


def test_unknown_visual_topic_fails_closed():
    with pytest.raises(ValueError, match="No subject-specific"):
        plan_scene("یک موضوع کاملاً تازه", "underwater coral reef ecosystem")


def test_neon_ellipse_query_selects_dedicated_3d_builder():
    plan = plan_scene("نقطه‌ها روی مدار حرکت می‌کنند", "neon ellipse with orbiting particles and geometric web")
    assert plan["motif"] == "neon_ellipse_mesh"
    assert plan["camera"] == "orbit"


def test_wave_interference_query_selects_two_source_scene():
    plan = plan_scene("دو موج با هم برخورد می‌کنند", "two wave sources and constructive destructive interference")
    assert plan["motif"] == "wave_interference"
    assert plan["camera"] == "orbit"
