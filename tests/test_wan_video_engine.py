from __future__ import annotations

import pytest

from app.wan_video_engine import generate_wan_clips


def test_wan_rejects_empty_prompt_list_before_loading_models(tmp_path):
    with pytest.raises(ValueError, match="one non-empty visual prompt"):
        generate_wan_clips([], tmp_path)


def test_wan_rejects_empty_scene_prompt_before_loading_models(tmp_path):
    with pytest.raises(ValueError, match="one non-empty visual prompt"):
        generate_wan_clips(["forest", "  "], tmp_path)


def test_wan_rejects_invalid_frame_count_before_loading_models(tmp_path):
    with pytest.raises(ValueError, match=r"4n\+1"):
        generate_wan_clips(["mountains at sunrise"], tmp_path, num_frames=80)


def test_wan_rejects_invalid_dimensions_before_loading_models(tmp_path):
    with pytest.raises(ValueError, match="divisible by 16"):
        generate_wan_clips(["mountains at sunrise"], tmp_path, width=481)
