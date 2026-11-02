from pathlib import Path
import shutil
import pytest
from app.bamo_neon_engine import validate, render_project

def test_validates_reference_math_project():
    spec = validate({"format":"short","fps":24,"scenes":[{"duration":4,"motif":"ellipse_mesh","text":"بیضی"}]})
    assert spec["format"] == "short"
    assert spec["scenes"][0]["motif"] == "ellipse_mesh"

def test_rejects_bad_projects_and_palette():
    with pytest.raises(ValueError): validate({"scenes":[]})
    with pytest.raises(ValueError): validate({"format":"ultrawide","scenes":[{"duration":4}]})
    with pytest.raises(ValueError): validate({"scenes":[{"duration":0.2}]})
    with pytest.raises(ValueError): validate({"scenes":[{"duration":4,"palette":"unknown"}]})

def test_cpu_render_produces_valid_mp4(tmp_path: Path):
    if not shutil.which("ffmpeg"): pytest.skip("FFmpeg is unavailable")
    output = tmp_path / "neon-smoke.mp4"
    render_project({"format":"short","fps":24,"scenes":[
        {"duration":1,"motif":"ellipse_mesh","text":"بیضی و مدار"},
        {"duration":1,"motif":"radial","text":"تبدیل به پرتوهای نور"}
    ]}, output)
    assert output.is_file()
    assert output.stat().st_size > 10_000
