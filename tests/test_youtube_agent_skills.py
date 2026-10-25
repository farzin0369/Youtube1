from __future__ import annotations

import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
EXPECTED = {
    "yt-audit", "yt-chapters", "yt-comment", "yt-edit", "yt-package",
    "yt-plan", "yt-retention", "yt-script", "yt-seo", "yt-shorts", "yt-viral",
}


def test_all_eleven_skill_instructions_exist():
    found = {p.parent.name for p in SKILLS.glob("yt-*/SKILL.md")}
    assert found == EXPECTED


def test_python_helpers_compile_without_importing_optional_dependencies():
    files = list(SKILLS.glob("yt-*/*.py"))
    assert len(files) == 6
    for path in files:
        py_compile.compile(str(path), doraise=True)


def test_hook_formula_data_is_valid_json():
    hooks = json.loads((SKILLS / "yt-script" / "hooks.json").read_text(encoding="utf-8"))
    assert isinstance(hooks, (dict, list))
    assert hooks
