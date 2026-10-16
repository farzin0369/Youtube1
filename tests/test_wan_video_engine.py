from __future__ import annotations

import sys
from types import SimpleNamespace

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


def test_wan_rejects_insufficient_free_cuda_vram_before_loading_models(tmp_path, monkeypatch):
    class FakeCuda:
        @staticmethod
        def is_available():
            return True

        @staticmethod
        def mem_get_info(device=0):
            return 8_189_999_999, 16 * 1024**3

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=FakeCuda()))
    with pytest.raises(RuntimeError, match="needs at least 8.19 GB free CUDA VRAM"):
        generate_wan_clips(["mountains at sunrise"], tmp_path)
