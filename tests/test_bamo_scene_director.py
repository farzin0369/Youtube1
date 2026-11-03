from app.bamo_scene_director import plan_scene


def test_notebook_and_writing_get_concrete_notebook_visuals():
    plan = plan_scene("دفتر و نوشتن", "notebook journal")
    assert plan["motif"] == "writing"


def test_sunrise_gets_horizon_visual_not_generic_launch_rings():
    plan = plan_scene("طلوع و امید", "sunrise light")
    assert plan["motif"] == "sunrise"


def test_atomic_subject_keeps_atomic_visual():
    plan = plan_scene("اتم و الکترون", "atomic orbit")
    assert plan["motif"] == "atom"


def test_decision_gets_diverging_paths():
    plan = plan_scene("یک تصمیم مهم", "two diverging paths")
    assert plan["motif"] == "choice_paths"


def test_physics_uses_wave_and_force_visuals():
    assert plan_scene("قانون حرکت و نیرو", "physics force vectors")["motif"] == "physics"


def test_chemistry_is_not_misclassified_as_atomic_orbit():
    assert plan_scene("پیوند مولکولی", "chemistry molecule bonds")["motif"] == "molecule"


def test_history_uses_architecture_and_terrain():
    assert plan_scene("تمدن باستانی", "ancient civilization")["motif"] == "history"


def test_story_uses_character_stage_visuals():
    assert plan_scene("داستان یک قهرمان", "hero character narrative")["motif"] == "story"
