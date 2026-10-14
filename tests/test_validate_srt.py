import pytest

from scripts.validate_srt import validate_srt_text


def test_valid_srt_with_two_cues_passes():
    srt = """1
00:00:00,000 --> 00:00:01,200
سلام

2
00:00:01,300 --> 00:00:02,000
خداحافظ
"""
    assert validate_srt_text(srt, 2.0) == 2


def test_zero_duration_cue_is_rejected():
    srt = "1\n00:00:00,000 --> 00:00:00,000\nمتن\n"
    with pytest.raises(ValueError, match="zero or negative"):
        validate_srt_text(srt, 10.0)


def test_cue_beyond_video_duration_is_rejected():
    srt = "1\n00:00:09,500 --> 00:00:11,000\nمتن\n"
    with pytest.raises(ValueError, match="beyond video duration"):
        validate_srt_text(srt, 10.0, tolerance_ms=0)


def test_malformed_timestamp_is_rejected():
    srt = "1\n00:60:00,000 --> 00:60:01,000\nمتن\n"
    with pytest.raises(ValueError, match="out-of-range"):
        validate_srt_text(srt, 4000.0)


def test_missing_caption_text_is_rejected():
    srt = "1\n00:00:00,000 --> 00:00:01,000\n"
    with pytest.raises(ValueError, match="timing or caption text"):
        validate_srt_text(srt, 2.0)
