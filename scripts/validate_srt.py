#!/usr/bin/env python3
"""Fail-closed validation for SRT captions before YouTube upload."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

TIMESTAMP = re.compile(r"^(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})$")
TIMING_LINE = re.compile(r"^\s*(\S+)\s*-->\s*(\S+)(?:\s+.*)?$")


def _to_milliseconds(value: str) -> int:
    match = TIMESTAMP.fullmatch(value)
    if not match:
        raise ValueError(f"invalid SRT timestamp: {value!r}")
    hours, minutes, seconds, millis = (int(part) for part in match.groups())
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"out-of-range SRT timestamp: {value!r}")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def validate_srt_text(text: str, duration_seconds: float, *, tolerance_ms: int = 1000) -> int:
    """Return cue count or raise ValueError for malformed/out-of-range cues."""
    if duration_seconds <= 0:
        raise ValueError("video duration must be positive")
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n")) if block.strip()]
    if not blocks:
        raise ValueError("SRT contains no caption cues")

    duration_ms = int(duration_seconds * 1000)
    count = 0
    for block_index, block in enumerate(blocks, start=1):
        lines = [line.strip("\ufeff") for line in block.split("\n")]
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None or timing_index + 1 >= len(lines):
            raise ValueError(f"cue {block_index} is missing timing or caption text")
        timing_match = TIMING_LINE.fullmatch(lines[timing_index])
        if not timing_match:
            raise ValueError(f"cue {block_index} has a malformed timing line")
        start_ms = _to_milliseconds(timing_match.group(1))
        end_ms = _to_milliseconds(timing_match.group(2))
        caption = "\n".join(lines[timing_index + 1:]).strip()
        if not caption:
            raise ValueError(f"cue {block_index} has empty caption text")
        if end_ms <= start_ms:
            raise ValueError(f"cue {block_index} has zero or negative duration")
        if end_ms > duration_ms + tolerance_ms:
            raise ValueError(f"cue {block_index} ends beyond video duration")
        count += 1
    return count


def _probe_duration(video_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        check=True, capture_output=True, text=True,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise ValueError("ffprobe returned a non-positive video duration")
    return duration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("srt", type=Path)
    parser.add_argument("--video", type=Path, required=True, help="MP4 used to check cue bounds")
    args = parser.parse_args()
    count = validate_srt_text(args.srt.read_text(encoding="utf-8-sig"), _probe_duration(args.video))
    print(f"SRT validation passed: {count} cues within video duration")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"SRT validation failed: {exc}") from None
