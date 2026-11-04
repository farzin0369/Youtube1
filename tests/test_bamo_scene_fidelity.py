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
    """Builder may be monolithic or modular; require the real camera + motif surface."""
    entry = Path("scripts/bamo_blender_scene.py").read_text(encoding="utf-8")
    primitives = Path("scripts/bamo_blender_primitives.py").read_text(encoding="utf-8") if Path("scripts/bamo_blender_primitives.py").is_file() else ""
    motifs_a = Path("scripts/bamo_blender_motifs_a.py").read_text(encoding="utf-8") if Path("scripts/bamo_blender_motifs_a.py").is_file() else ""
    motifs_b = Path("scripts/bamo_blender_motifs_b.py").read_text(encoding="utf-8") if Path("scripts/bamo_blender_motifs_b.py").is_file() else ""
    combined = "\n".join([entry, primitives, motifs_a, motifs_b])

    def function_names(source: str) -> set[str]:
        tree = ast.parse(source)
        return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    functions = function_names(entry) | function_names(primitives) | function_names(motifs_a) | function_names(motifs_b)
    assert {"scene_notebook", "scene_sunrise", "add_camera"} <= functions
    assert "scene_from_ai_graph" in functions or "scene_from_ai_graph" in combined
    assert 'elif motif == "notebook"' in entry or 'elif motif == "notebook"' in combined
    assert 'elif motif == "sunrise"' in entry or 'elif motif == "sunrise"' in combined
    assert "orbit" in combined
