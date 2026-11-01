import json
from pathlib import Path

from scripts.run_bamo_first_film import ROLE_KEYS, validate_brief

ROOT = Path(__file__).resolve().parents[1]


def test_first_film_brief_runs_through_all_eleven_role_handoffs():
    brief = json.loads((ROOT / "examples/bamo_first_film.json").read_text(encoding="utf-8"))
    validate_brief(brief)
    assert tuple(brief["roles"].keys()) == ROLE_KEYS
    assert sum(scene["duration"] for scene in brief["scenes"]) == 20


def test_pipeline_rejects_missing_role_output():
    brief = {
        "title": "x", "hook": "x", "narration": "x",
        "scenes": [{"duration": 5}] * 4,
        "roles": {key: "ok" for key in ROLE_KEYS},
    }
    brief["roles"].pop("analytics")
    try:
        validate_brief(brief)
    except ValueError as exc:
        assert "11 documented" in str(exc)
    else:
        raise AssertionError("missing role must fail closed")
