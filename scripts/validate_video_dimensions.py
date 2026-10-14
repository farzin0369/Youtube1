"""Fail-closed aspect-ratio validation for YouTube Shorts video files."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def validate_shorts_dimensions(width: int, height: int) -> dict[str, Any]:
    """Require portrait 9:16 video at a minimum of 720x1280 pixels."""
    width, height = int(width), int(height)
    ratio = width / height if height > 0 else 0.0
    if (
        width < 720
        or height < 1280
        or width >= height
        or abs(ratio - 9 / 16) > 0.015
    ):
        raise ValueError(
            "YouTube Shorts output must be portrait 9:16 at least 720x1280; "
            f"got {width}x{height} (aspect ratio {ratio:.4f})"
        )
    return {"width": width, "height": height, "aspect_ratio": round(ratio, 4)}


def probe_video_dimensions(video_path: Path) -> dict[str, Any]:
    """Read the first video stream's encoded dimensions using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", str(video_path),
        ],
        check=True, capture_output=True, text=True, timeout=30,
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    if not streams:
        raise ValueError("Video file has no video stream")
    stream = streams[0]
    return validate_shorts_dimensions(stream.get("width", 0), stream.get("height", 0))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="MP4 file to validate")
    parser.add_argument(
        "--format", choices=("shorts",), default="shorts",
        help="Target format (currently only Shorts is supported)",
    )
    args = parser.parse_args()
    dimensions = probe_video_dimensions(args.video)
    print(
        "Video dimensions passed: "
        f"{dimensions['width']}x{dimensions['height']} "
        f"(9:16, {args.format})"
    )


if __name__ == "__main__":
    main()
