"""LTX video backend stub — requires CUDA GPU (not available on GitHub Actions).

When AI_VIDEO_ENGINE=ltx is set on a machine with GPU and LTX installed,
replace generate_ltx_clips with a real call into Lightricks LTX pipeline.
Until then this module fails clearly so Mixkit fallback can run.
"""
from __future__ import annotations

from pathlib import Path


def generate_ltx_clips(
    prompts: list[str],
    out_dir: Path,
    *,
    width: int = 512,
    height: int = 896,
    num_frames: int = 121,
    fps: int = 24,
) -> list[Path]:
    raise RuntimeError(
        "AI_VIDEO_ENGINE=ltx requires a local/Colab CUDA GPU and LTX-2 weights. "
        "GitHub-hosted runners are CPU-only. Use Mixkit (default) or run notebooks/colab_ai_video_shorts.md on Colab."
    )
