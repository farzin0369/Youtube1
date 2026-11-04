import pytest

from app.bamo_motion_engine import _render_blender_scene, render_project, validate_project
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
    assert plan_scene("ساختن عادت", "writing in notebook")["motif"] == "notebook"
    assert plan_scene("اتم و الکترون", "atomic orbit")["motif"] == "atom"
    assert plan_scene("هندسه و دایره", "geometry circle")["motif"] == "geometry"
    assert plan_scene("طلوع و امید", "sunrise light")["camera"] == "push_in"
    assert plan_scene("مغز و مسیر عصبی", "neural pathways brain synapses")["motif"] == "neural_network"


def test_unmatched_visual_prompt_fails_closed_instead_of_using_generic_art():
    with pytest.raises(ValueError, match="No subject-specific 3D scene builder"):
        plan_scene("یک موضوع ناشناخته", "unclassified visual subject")


def test_3d_renderer_fails_closed_when_blender_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("app.bamo_motion_engine.shutil.which", lambda _name: None)
    with pytest.raises(RuntimeError, match="Blender is required"):
        _render_blender_scene(
            tmp_path / "scene.mp4", 2.0, 720, 1280, 24, 0,
            {"motif": "atom", "camera": "orbit"},
        )

def test_blender_shutdown_crash_is_recovered_only_when_all_frames_exist(tmp_path, monkeypatch):
    from types import SimpleNamespace

    def fake_which(name):
        return "/usr/bin/blender" if name == "blender" else None

    def fake_blender(command, **kwargs):
        frames_dir = __import__("pathlib").Path(command[-1])
        frames_dir.mkdir(parents=True, exist_ok=True)
        for frame in (1, 2):
            (frames_dir / f"frame_{frame:04d}.png").write_bytes(b"x" * 2048)
        return SimpleNamespace(returncode=139, stderr="Segmentation fault after final frame", stdout="")

    def fake_ffmpeg(command, **kwargs):
        __import__("pathlib").Path(command[-1]).write_bytes(b"m" * 20000)

    monkeypatch.setattr("app.bamo_motion_engine.shutil.which", fake_which)
    monkeypatch.setattr("app.bamo_motion_engine.subprocess.run", fake_blender)
    monkeypatch.setattr("app.bamo_motion_engine._run", fake_ffmpeg)
    monkeypatch.setenv("DISPLAY", ":99")
    monkeypatch.setenv("BAMO_BLENDER_RENDER_ATTEMPTS", "3")

    output = tmp_path / "recovered.mp4"
    _render_blender_scene(
        output, 1.0, 720, 1280, 2, 0,
        {"motif": "ai_scene", "camera": "orbit", "scene_graph": {"objects": []}},
    )

    assert output.is_file()
    assert output.stat().st_size == 20000


def test_blender_shutdown_crash_with_missing_frames_still_fails(tmp_path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "app.bamo_motion_engine.shutil.which",
        lambda name: "/usr/bin/blender" if name == "blender" else None,
    )
    monkeypatch.setattr(
        "app.bamo_motion_engine.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=139, stderr="Segmentation fault", stdout=""),
    )
    monkeypatch.setenv("DISPLAY", ":99")
    monkeypatch.setenv("BAMO_BLENDER_RENDER_ATTEMPTS", "1")

    with pytest.raises(RuntimeError, match="did not produce all expected frames"):
        _render_blender_scene(
            tmp_path / "partial.mp4", 1.0, 720, 1280, 2, 0,
            {"motif": "ai_scene", "camera": "orbit", "scene_graph": {"objects": []}},
        )



def test_still_image_scene_is_rejected_instead_of_using_2d_zoompan(tmp_path, monkeypatch):
    from pathlib import Path

    image = tmp_path / "still.png"
    image.write_bytes(b"placeholder")
    monkeypatch.setattr("app.bamo_motion_engine.shutil.which", lambda _name: "/usr/bin/ffmpeg")

    with pytest.raises(ValueError, match="static-image zoompan is disabled"):
        render_project(
            {
                "format": "short",
                "scenes": [{
                    "duration": 1,
                    "text": "موضوع آزمایشی",
                    "image": str(image),
                    "visual_prompt": "atomic orbit",
                }],
            },
            tmp_path / "out.mp4",
        )
