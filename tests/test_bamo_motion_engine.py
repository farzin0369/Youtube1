from pathlib import Path
import pytest
from app.bamo_motion_engine import FORMATS, _ass_time, _write_ass, validate_project

def test_accepts_hybrid_short_project_and_defaults():
    result=validate_project({"scenes":[{"text":"سلام"}]})
    assert result["format"]=="short"
    assert result["scenes"][0]["duration"]==4
    assert FORMATS[result["format"]]==(720,1280)

def test_rejects_empty_scenes_and_bad_durations():
    with pytest.raises(ValueError): validate_project({"scenes":[]})
    with pytest.raises(ValueError): validate_project({"scenes":[{"duration":.1}]})
    with pytest.raises(ValueError): validate_project({"format":"cinema","scenes":[{"text":"x"}]})

def test_ass_timing_and_persian_text(tmp_path: Path):
    assert _ass_time(1.25)=="0:00:01.25"
    path=tmp_path/"captions.ass"
    _write_ass([{"duration":2.0,"text":"سلام دنیا"}],path,720,1280)
    data=path.read_text(encoding="utf-8")
    assert "سلام دنیا" in data
    assert "0:00:00.15" in data
