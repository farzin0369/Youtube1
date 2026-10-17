#!/usr/bin/env python3
"""Download an authorized source and create a vertical 9:16 clip with FFmpeg."""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="URL for a video you own or are authorized to reuse")
    parser.add_argument("--start", type=float, default=0, help="Clip start time in seconds")
    parser.add_argument("--duration", type=float, default=30, help="Clip duration (1–90 seconds)")
    parser.add_argument("--output", default="ssemble-open-clip.mp4")
    args = parser.parse_args()
    if not args.url.startswith(("https://", "http://")):
        parser.error("--url must be an http(s) URL")
    if args.start < 0:
        parser.error("--start must be >= 0")
    if not 1 <= args.duration <= 90:
        parser.error("--duration must be between 1 and 90 seconds")
    for executable in ("ffmpeg", "yt-dlp"):
        if shutil.which(executable) is None:
            print(f"ERROR: required executable not found: {executable}", file=sys.stderr)
            return 2
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ssemble-open-") as tmp:
        source = Path(tmp) / "source.%(ext)s"
        run([
            "yt-dlp", "--no-playlist", "--max-filesize", "800M",
            "-f", "bv*[height<=1080]+ba/b[height<=1080]/b",
            "--merge-output-format", "mp4", "-o", str(source), args.url,
        ])
        candidates = [p for p in Path(tmp).glob("source.*") if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
        if not candidates:
            print("ERROR: yt-dlp did not produce a supported video file.", file=sys.stderr)
            return 3
        downloaded = max(candidates, key=lambda p: p.stat().st_size)
        vf = (
            "split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=20:10[blur];"
            "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fit];"
            "[blur][fit]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p"
        )
        run([
            "ffmpeg", "-hide_banner", "-y", "-ss", str(args.start),
            "-i", str(downloaded), "-t", str(args.duration), "-vf", vf,
            "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            str(output),
        ])
    print(f"SUCCESS: {output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
