from __future__ import annotations

import pytest

from app.ltx_video_engine import generate_ltx_clips


def test_ltx_rejects_empty_prompt_list_before_loading_models(tmp_path):
    with pytest.raises(ValueError, match="one non-empty visual prompt"):
        generate_ltx_clips([], tmp_path)


def test_ltx_rejects_empty_scene_prompt_before_loading_models(tmp_path):
    with pytest.raises(ValueError, match="one non-empty visual prompt"):
        generate_ltx_clips(["forest", "  "], tmp_path)


def test_ltx_requires_valid_frame_count_before_loading_models(tmp_path):
    with pytest.raises(ValueError, match="8n\+1"):
        generate_ltx_clips(["misty mountain at sunrise"], tmp_path, num_frames=48)


def test_ltx_requires_vae_compatible_dimensions_before_loading_models(tmp_path):
    with pytest.raises(ValueError, match="divisible by 32"):
        generate_ltx_clips(["misty mountain at sunrise"], tmp_path, width=513)
