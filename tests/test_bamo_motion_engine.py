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
    assert plan_scene("ساختن عادت", "writing in notebook")["motif"] == "writing"
    assert plan_scene("اتم و الکترون", "atomic orbit")["motif"] == "atom"
    assert plan_scene("هندسه و دایره", "geometry circle")["motif"] == "geometry"
    assert plan_scene("طلوع و امید", "sunrise light")["camera"] == "push_in"


def test_unmatched_visual_prompt_is_not_claimed_as_verified():
    plan = plan_scene("یک موضوع ناشناخته", "unclassified visual subject")
    assert plan["motif"] == "abstract"


def test_project_validation_preserves_omnivision_render_directives():
    directive = {"motif": "geometry", "camera": "sweep", "description": "A 3D curve"}
    project = validate_project({
        "format": "short",
        "scenes": [{"duration": 2, "text": "", "visual_plan": directive}],
    })
    assert project["scenes"][0]["visual_plan"] == directive



def test_omnivision_adapter_passes_measured_audio_captions_and_pause(monkeypatch, tmp_path):
    import app.bamo_motion_engine as engine

    captured = {}
    def fake_render(project, output, audio=None, timeline=None):
        captured["project"] = project
        captured["output"] = output
        captured["audio"] = audio
        captured["timeline"] = timeline
        return tmp_path / "rendered.mp4"

    monkeypatch.setattr(engine, "render_project", fake_render)
    pipeline = {
        "schema": "bamo.omnivision-pipeline/1.0",
        "audio": {"path": str(tmp_path / "voice.wav"), "duration": 3.0},
        "validation": {"ok": True},
        "graph": {
            "aspect": "9:16",
            "fps": 30,
            "scenes": [{
                "id": "scene-1", "start": 0.8, "end": 3.0,
                "narration": "یک منحنی",
                "visual": {"subject": "parametric-curve", "semanticPrompt": "A glowing parametric curve"},
                "animation": {"camera": [
                    {"position": [0, 1, 8]}, {"position": [0, 1, 4]}
                ]},
            }],
        },
        "timeline": {
            "validation": {"ok": True},
            "captions": [{"start": 1.0, "end": 1.8, "text": "یک منحنی", "sceneId": "scene-1"}],
            "wordCues": [
                {"time": 1.0, "word": "یک"}, {"time": 1.4, "word": "منحنی"}
            ],
        },
    }

    result = engine.render_omnivision_pipeline(pipeline, tmp_path / "out.mp4")

    assert result == tmp_path / "rendered.mp4"
    assert captured["audio"] == str(tmp_path / "voice.wav")
    assert captured["timeline"]["captions"][0]["start"] == 1.0
    assert captured["project"]["scenes"][0]["duration"] == 0.8
    assert captured["project"]["scenes"][1]["visual_plan"]["motif"] == "geometry"
    assert captured["project"]["scenes"][1]["visual_plan"]["camera"] == "sweep"
    assert captured["project"]["scenes"][1]["duration"] == 2.2
