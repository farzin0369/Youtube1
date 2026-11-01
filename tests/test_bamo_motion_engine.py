from app.bamo_motion_engine import validate_project
from app.bamo_scene_director import plan_scene


def test_project_validation_preserves_scene_narration_and_visual_brief():
    project = validate_project({
        "format": "short",
        "scenes": [{
            "duration": 4,
            "text": "یک قدم کوچک",
            "narration": "امروز فقط یک قدم بردار.",
            "visual_prompt": "rising steps in golden light",
        }],
    })
    assert project["scenes"][0]["narration"] == "امروز فقط یک قدم بردار."
    assert project["scenes"][0]["visual_prompt"] == "rising steps in golden light"


def test_scene_director_selects_topic_matched_3d_motifs_and_camera_moves():
    assert plan_scene("یک تصمیم مهم", "two diverging paths")["motif"] == "choice_paths"
    assert plan_scene("ساختن عادت", "writing in notebook")["motif"] == "growth_steps"
    assert plan_scene("اتم و الکترون", "atomic orbit")["motif"] == "atom"
    assert plan_scene("هندسه و دایره", "geometry circle")["motif"] == "geometry"
    assert plan_scene("طلوع و امید", "sunrise light")["camera"] == "push_in"


def test_unmatched_visual_prompt_is_not_claimed_as_verified():
    plan = plan_scene("یک موضوع ناشناخته", "unclassified visual subject")
    assert plan["motif"] == "abstract"
