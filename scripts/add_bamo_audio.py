#!/usr/bin/env python3
"""Add Persian Edge-TTS narration and timed VTT subtitles to a rendered BAMO MP4."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def probe_duration(path: Path) -> float:
    raw = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        text=True,
    ).strip()
    return float(raw)


def atempo_chain(speed: float) -> str:
    """Return legal chained atempo filters for any positive speed."""
    if speed <= 0:
        raise ValueError("speed must be positive")
    filters: list[str] = []
    while speed > 2.0:
        filters.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        filters.append("atempo=0.5")
        speed /= 0.5
    filters.append(f"atempo={speed:.5f}")
    return ",".join(filters)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--voice", default="fa-IR-FaridNeural")
    parser.add_argument("--rate", default="+10%")
    args = parser.parse_args()

    video = Path(args.video)
    brief_path = Path(args.brief)
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    narration = str(brief.get("narration", "")).strip()
    if not narration:
        raise SystemExit("BAMO audio gate: narration is required")

    duration = probe_duration(video)
    voice = video.with_name("BAMO-voiceover.mp3")
    subtitles = video.with_name("BAMO-fa.vtt")
    output = video.with_name("BAMO-HyperFrames-final.mp4")

    subprocess.run(
        [
            "edge-tts", "--voice", args.voice, f"--rate={args.rate}",
            "--text", narration, "--write-media", str(voice),
            "--write-subtitles", str(subtitles),
        ],
        check=True,
        timeout=240,
    )

    voice_duration = probe_duration(voice)
    speed = max(1.0, voice_duration / max(duration - 0.15, 0.1))
    audio_filter = atempo_chain(speed) if speed > 1.03 else "anull"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video), "-i", str(voice),
            "-filter_complex",
            f"[1:a]{audio_filter},apad=pad_dur={duration:.3f},atrim=duration={duration:.3f},"
            f"afade=t=out:st={max(0.0, duration - 0.35):.3f}:d=0.35[a]",
            "-map", "0:v:0", "-map", "[a]", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{duration:.3f}",
            "-movflags", "+faststart", str(output),
        ],
        check=True,
        timeout=180,
    )
    output.replace(video)

    manifest_path = video.with_name("manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "audio_track": True,
            "voiceover": args.voice,
            "voiceover_rate": args.rate,
            "voiceover_speed_factor": round(speed, 3),
            "subtitles_file": subtitles.name,
            "youtube_upload": "not_performed",
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not subtitles.is_file() or subtitles.stat().st_size < 20:
        raise SystemExit("BAMO audio gate: timed Persian subtitles were not created")
    if probe_duration(video) < duration - 0.1:
        raise SystemExit("BAMO audio gate: final video duration unexpectedly shortened")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
