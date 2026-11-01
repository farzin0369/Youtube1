#!/usr/bin/env python3
"""Generate scene-locked Persian narration: each spoken line matches its visible scene."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str], timeout: int = 240) -> None:
    subprocess.run(command, check=True, timeout=timeout)


def probe_duration(path: Path) -> float:
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True
    ).strip()
    return float(raw)


def atempo_chain(speed: float) -> str:
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


def stamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--voice", default="fa-IR-FaridNeural")
    parser.add_argument("--rate", default="+10%")
    args = parser.parse_args()

    video = Path(args.video)
    brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
    scenes = brief.get("scenes") or []
    if len(scenes) != 4:
        raise SystemExit("BAMO audio gate: exactly four authored scenes are required")
    lines = [str(scene.get("text", "")).strip() for scene in scenes]
    if not all(lines):
        raise SystemExit("BAMO audio gate: every scene needs visible text")
    expected = " ".join(lines)
    actual = " ".join(str(brief.get("narration", "")).split())
    if actual != expected:
        raise SystemExit("BAMO sync gate: narration must exactly equal the ordered scene texts")

    video_duration = probe_duration(video)
    durations = [float(scene["duration"]) for scene in scenes]
    if abs(sum(durations) - video_duration) > 0.75:
        raise SystemExit(
            f"BAMO sync gate: scene duration total {sum(durations):.2f}s "
            f"does not match rendered video {video_duration:.2f}s"
        )

    edge_cli = Path(sys.executable).with_name("edge-tts")
    subtitles = video.with_name("BAMO-fa.vtt")
    voice = video.with_name("BAMO-voiceover.mp3")
    output = video.with_name("BAMO-HyperFrames-final.mp4")
    cues = ["WEBVTT", ""]
    offset = 0.0
    segment_wavs: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="bamo-scene-tts-") as tmp:
        tmpdir = Path(tmp)
        for index, (line, target) in enumerate(zip(lines, durations), start=1):
            raw_mp3 = tmpdir / f"scene-{index}.mp3"
            wav = tmpdir / f"scene-{index}.wav"
            run([
                str(edge_cli), "--voice", args.voice, f"--rate={args.rate}",
                "--text", line, "--write-media", str(raw_mp3)
            ])
            spoken = probe_duration(raw_mp3)
            speed = max(1.0, spoken / max(target - 0.08, 0.1))
            audio_filter = atempo_chain(speed) if speed > 1.001 else "anull"
            run([
                "ffmpeg", "-y", "-i", str(raw_mp3), "-af",
                f"{audio_filter},apad,atrim=duration={target:.3f}",
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(wav)
            ])
            segment_wavs.append(wav)
            cues.extend([
                str(index),
                f"{stamp(offset)} --> {stamp(offset + target)}",
                line,
                ""
            ])
            offset += target

        concat_file = tmpdir / "concat.txt"
        concat_file.write_text(
            "".join(f"file '{p.as_posix()}'\n" for p in segment_wavs),
            encoding="utf-8"
        )
        combined_wav = tmpdir / "combined.wav"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
             str(concat_file), "-c:a", "pcm_s16le", str(combined_wav)])
        run(["ffmpeg", "-y", "-i", str(combined_wav), "-codec:a", "libmp3lame",
             "-b:a", "160k", str(voice)])

    subtitles.write_text("\n".join(cues), encoding="utf-8")
    run([
        "ffmpeg", "-y", "-i", str(video), "-i", str(voice),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "160k", "-t", f"{video_duration:.3f}",
        "-movflags", "+faststart", str(output)
    ], timeout=180)
    output.replace(video)

    manifest_path = video.with_name("manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "audio_track": True,
        "voiceover": args.voice,
        "voiceover_rate": args.rate,
        "audio_alignment": "one TTS segment per scene; exact scene text; scene-locked VTT",
        "subtitles_file": subtitles.name,
        "youtube_upload": "not_performed"
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    if probe_duration(video) < video_duration - 0.1:
        raise SystemExit("BAMO audio gate: final video duration unexpectedly shortened")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
