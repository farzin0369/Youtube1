#!/usr/bin/env python3
"""CPU QA metrics: clip fraction, mean luma, inter-frame MSE proxy."""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow required")
    raise SystemExit(2)


def metrics(frames_dir: Path) -> dict:
    frames = sorted(frames_dir.glob("*.png")) or sorted(frames_dir.glob("frame_*.png"))
    if len(frames) < 2:
        raise SystemExit(f"need >=2 frames in {frames_dir}")
    clip_fracs = []
    means = []
    mses = []
    prev = None
    for path in frames:
        im = Image.open(path).convert("RGB")
        pixels = list(im.getdata())
        n = len(pixels)
        clipped = sum(1 for r, g, b in pixels if r >= 250 and g >= 250 and b >= 250)
        clip_fracs.append(clipped / max(1, n))
        means.append(sum((r + g + b) / 3 for r, g, b in pixels) / n)
        if prev is not None:
            mse = sum((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2 for a, b in zip(prev, pixels)) / (n * 3)
            mses.append(mse)
        prev = pixels
    report = {
        "frames": len(frames),
        "mean_luma": sum(means) / len(means),
        "max_clip_frac": max(clip_fracs),
        "avg_clip_frac": sum(clip_fracs) / len(clip_fracs),
        "mean_interframe_mse": (sum(mses) / len(mses)) if mses else 0.0,
        "gates": {
            "clip_ok": max(clip_fracs) < 0.02,
            "not_black": (sum(means) / len(means)) > 8.0,
            "not_white": (sum(means) / len(means)) < 240.0,
        },
    }
    report["pass"] = all(report["gates"].values())
    return report


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: bamo_qa_frame_metrics.py <frames_dir>")
        return 2
    report = metrics(Path(sys.argv[1]))
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
