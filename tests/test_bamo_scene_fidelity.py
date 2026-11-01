from pathlib import Path
import ast

from app.bamo_scene_director import plan_scene


def test_notebook_prompt_selects_notebook_not_growth_steps():
    plan = plan_scene("او در دفتر می‌نویسد", "open notebook with a moving pen")
    assert plan["motif"] == "notebook"
    assert plan["camera"] == "push_in"


def test_sunrise_prompt_selects_literal_sunrise_scene():
    plan = plan_scene("خورشید طلوع می‌کند", "sunrise over a mountain horizon")
    assert plan["motif"] == "sunrise"


def test_notebook_narration_does_not_map_to_staircase():
    plan = plan_scene("او یادداشت می‌نویسد", "writing in a notebook")
    assert plan["motif"] == "notebook"
    assert plan["motif"] != "growth_steps"


def test_unknown_visual_prompt_fails_closed():
    import pytest
    with pytest.raises(ValueError, match="No subject-specific"):
        plan_scene("موضوع تازه", "underwater coral reef ecosystem")


def test_blender_builder_contains_real_subject_specific_scene_builders_and_orbit_camera():
    source = Path("scripts/bamo_blender_scene.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {"scene_notebook", "scene_sunrise", "add_camera"} <= functions
    assert "true multi-point orbit" in source
    assert 'elif motif == "notebook"' in source
    assert 'elif motif == "sunrise"' in source
