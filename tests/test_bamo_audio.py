from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "add_bamo_audio.py"
SPEC = importlib.util.spec_from_file_location("add_bamo_audio", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    ("speed", "expected"),
    [
        (1.0, "atempo=1.00000"),
        (1.5, "atempo=1.50000"),
        (2.5, "atempo=2.0,atempo=1.25000"),
        (4.0, "atempo=2.0,atempo=2.00000"),
        (0.25, "atempo=0.5,atempo=0.50000"),
    ],
)
def test_atempo_chain_uses_supported_filter_ranges(speed: float, expected: str) -> None:
    assert MODULE.atempo_chain(speed) == expected


@pytest.mark.parametrize("speed", [0, -1, -0.25])
def test_atempo_chain_rejects_non_positive_speed(speed: float) -> None:
    with pytest.raises(ValueError):
        MODULE.atempo_chain(speed)


def test_audio_script_defaults_to_persian_farid_voice() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert 'default="fa-IR-FaridNeural"' in source
    assert '"--write-subtitles"' in source
    assert '"-c:a", "aac"' in source
    assert '"youtube_upload": "not_performed"' in source
