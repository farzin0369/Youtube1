#!/usr/bin/env python3
"""Fail closed unless an MP4 is playable, correctly sized, long enough, and moving."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

MIN_BYTES = 200_000
MIN_SECONDS = 5.0
MIN_WIDTH = 640
MIN_HEIGHT = 960
FRAME_SIDE = 64
MIN_MEAN_FRAME_DELTA = 1.25


def run(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--min-seconds", type=float, default=MIN_SECONDS)
    args = parser.parse_args()
    path = args.video

    errors: list[str] = []
    if not path.is_file():
        print(f"QA FAIL: file missing: {path}")
        return 2
    size = path.stat().st_size
    if size < MIN_BYTES:
        errors.append(f"file too small: {size} bytes (<{MIN_BYTES})")

    ffprobe = shutil.which("ffprobe")
    ffmpeg = shutil.which("ffmpeg")
    if not ffprobe or not ffmpeg:
        print("QA FAIL: ffmpeg and ffprobe must be installed")
        return 2

    probe = run([
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate:format=duration",
        "-of", "json", str(path),
    ])
    if probe.returncode:
        errors.append("ffprobe could not read the MP4")
        metadata = {}
    else:
        try:
            metadata = json.loads(probe.stdout.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            metadata = {}
            errors.append("ffprobe returned invalid metadata")

    streams = metadata.get("streams") or []
    fmt = metadata.get("format") or {}
    if not streams:
        errors.append("no video stream")
        width = height = 0
        fps = 0.0
    else:
        stream = streams[0]
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
        rate = str(stream.get("avg_frame_rate") or "0/1")
        try:
            n, d = rate.split("/", 1)
            fps = float(n) / max(float(d), 1.0)
        except (ValueError, ZeroDivisionError):
            fps = 0.0

    try:
        duration = float(fmt.get("duration") or 0.0)
    except (ValueError, TypeError):
        duration = 0.0

    if duration < args.min_seconds:
        errors.append(f"duration too short: {duration:.2f}s (<{args.min_seconds:.2f}s)")
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        errors.append(f"resolution too small: {width}x{height} (need at least {MIN_WIDTH}x{MIN_HEIGHT})")
    if fps < 10:
        errors.append(f"frame rate too low or unknown: {fps:.2f} fps")

    # Sample one grayscale frame per second and measure real pixel change.
    motion = 0.0
    frame_count = 0
    sample = run([
        ffmpeg, "-v", "error", "-i", str(path), "-vf",
        f"fps=1,scale={FRAME_SIDE}:{FRAME_SIDE}:force_original_aspect_ratio=decrease,pad={FRAME_SIDE}:{FRAME_SIDE}:(ow-iw)/2:(oh-ih)/2,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
    ])
    frame_bytes = FRAME_SIDE * FRAME_SIDE
    if sample.returncode:
        errors.append("ffmpeg could not decode video frames")
    else:
        raw = sample.stdout
        frames = [raw[i:i + frame_bytes] for i in range(0, len(raw) - frame_bytes + 1, frame_bytes)]
        frame_count = len(frames)
        if frame_count < 2:
            errors.append("not enough decodable frames to assess motion")
        else:
            deltas = []
            for previous, current in zip(frames, frames[1:]):
                deltas.append(sum(abs(a - b) for a, b in zip(previous, current)) / frame_bytes)
            motion = sum(deltas) / len(deltas)
            if motion < MIN_MEAN_FRAME_DELTA:
                errors.append(f"near-static output: mean frame delta {motion:.3f} (<{MIN_MEAN_FRAME_DELTA})")

    report = {
        "ok": not errors,
        "file": str(path),
        "bytes": size,
        "duration_seconds": round(duration, 3),
        "resolution": f"{width}x{height}",
        "fps": round(fps, 3),
        "sampled_frames": frame_count,
        "mean_frame_delta": round(motion, 3),
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
