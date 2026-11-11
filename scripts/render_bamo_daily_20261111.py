"""Render BAMO's 2026-11-11 Persian science short about auroras and Earth's magnetosphere."""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from app.html_motion_renderer import render_html_project

# Use the runner's FFmpeg binary for metadata checks; do not assume ffprobe is installed.
# The workflow installs FFmpeg/ffprobe from Ubuntu packages before this script runs.

OUT = Path("artifacts/bamo-science-short-20261111.mp4")
SRT = OUT.with_suffix(".srt")
QA = OUT.with_name("bamo-science-short-20261111-qa.json")
REVIEW = OUT.with_name("bamo-science-short-20261111-review.jpg")
VOICE = "fa-IR-DilaraNeural"
FPS = 24
WIDTH = 1080
HEIGHT = 1920
TOPIC = "شفق قطبی چگونه از برخورد باد خورشیدی و جو زمین پدید می‌آید؟"
SOURCES = [
    "https://science.nasa.gov/sun/auroras/",
    "https://prod-01-asg-www-swpc.woc.noaa.gov/content/aurora-tutorial",
    "https://www.csa-asc.gc.ca/eng/astronomy/northern-lights/what-are-northern-lights.asp",
]

SCENES = [
    {
        "text": "شفق قطبی، نورِ برخورد ذرات خورشیدی با گازهای جو زمین است.",
        "narration": "شفق قطبی، نورِ برخورد ذرات خورشیدی با گازهای جو زمین است.",
        "visual_prompt": "نمای مداری سه‌بعدی از زمین با پرده‌های نورانی قطبی و دوربین در حال گردش",
        "motif": "aurora",
        "phase": 0.0,
        "phase_sweep": 0.35,
        "palette": {"bg": "#020712", "primary": "#55f7c8", "secondary": "#8b5cf6", "accent": "#7dd3fc"},
    },
    {
        "text": "باد خورشیدی ذرات باردار می‌آورد؛ میدان مغناطیسی زمین بیشترشان را منحرف می‌کند.",
        "narration": "باد خورشیدی ذرات باردار می‌آورد؛ میدان مغناطیسی زمین بیشترشان را منحرف می‌کند.",
        "visual_prompt": "جریان ذرات خورشیدی در سه‌بعد از کنار زمین می‌گذرد و با خطوط میدان مغناطیسی منحرف می‌شود",
        "motif": "aurora",
        "phase": 0.9,
        "phase_sweep": 0.45,
        "palette": {"bg": "#060b19", "primary": "#7dd3fc", "secondary": "#60a5fa", "accent": "#facc15"},
    },
    {
        "text": "بخشی از ذرات در امتداد خطوط میدان، به نواحی قطبی می‌رسند.",
        "narration": "بخشی از ذرات در امتداد خطوط میدان، به نواحی قطبی می‌رسند.",
        "visual_prompt": "خطوط میدان مغناطیسی سه‌بعدی به شکل قوس‌های دو قطبی، ذرات در امتداد آن‌ها به قطب‌ها هدایت می‌شوند",
        "motif": "aurora",
        "phase": 1.8,
        "phase_sweep": 0.55,
        "palette": {"bg": "#020a18", "primary": "#38bdf8", "secondary": "#a78bfa", "accent": "#67e8f9"},
    },
    {
        "text": "برخورد با اکسیژن و نیتروژن، اتم‌ها را برانگیخته می‌کند؛ سپس نور آزاد می‌شود.",
        "narration": "برخورد با اکسیژن و نیتروژن، اتم‌ها را برانگیخته می‌کند؛ سپس نور آزاد می‌شود.",
        "visual_prompt": "نمای نزدیک سه‌بعدی از پرده‌های شفق در بالای جو، ذرات پرانرژی و موج‌های نورانی",
        "motif": "aurora",
        "phase": 2.7,
        "phase_sweep": 0.65,
        "palette": {"bg": "#07111c", "primary": "#34d399", "secondary": "#f472b6", "accent": "#fef08a"},
    },
    {
        "text": "اکسیژن سبز یا قرمز می‌تابد؛ نیتروژن آبی یا بنفش، در ارتفاع‌های متفاوت.",
        "narration": "اکسیژن سبز یا قرمز می‌تابد؛ نیتروژن آبی یا بنفش، در ارتفاع‌های متفاوت.",
        "visual_prompt": "نمای دوربین مداری از زمین و پرده‌های سبز، قرمز و آبی شفق در لایه‌های مختلف جو",
        "motif": "aurora",
        "phase": 3.6,
        "phase_sweep": 0.8,
        "palette": {"bg": "#030712", "primary": "#22d3ee", "secondary": "#a78bfa", "accent": "#f0abfc"},
    },
]


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {' '.join(cmd[:4])}\n{result.stderr[-2500:]}")
    return result.stdout.strip()


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-t", "0.01", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    output = result.stderr + result.stdout
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
    if not match:
        raise RuntimeError(f"FFmpeg could not read media duration for {path}: {output[-1200:]}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def probe_media_info(path: Path) -> dict[str, object]:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-map", "0:v:0", "-frames:v", "1", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    output = result.stderr + result.stdout
    video_line = next((line for line in output.splitlines() if "Video:" in line), "")
    audio_line = next((line for line in output.splitlines() if "Audio:" in line), "")
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
    dimensions = re.search(r"\b(\d{2,5})x(\d{2,5})\b", video_line)
    fps_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s+fps\b", video_line)
    sample_match = re.search(r"([0-9]+)\s+Hz\b", audio_line)
    if not video_line or not audio_line or not duration_match or not dimensions or not fps_match or not sample_match:
        raise RuntimeError(f"FFmpeg could not inspect final MP4 streams: {output[-1800:]}")
    hours, minutes, seconds = duration_match.groups()
    channel_count = 1 if re.search(r"\bmono\b", audio_line) else (2 if re.search(r"\bstereo\b", audio_line) else 0)
    return {
        "duration": int(hours) * 3600 + int(minutes) * 60 + float(seconds),
        "width": int(dimensions.group(1)),
        "height": int(dimensions.group(2)),
        "fps": float(fps_match.group(1)),
        "video_codec": re.search(r"Video:\s*([a-zA-Z0-9_]+)", video_line).group(1),
        "audio_codec": re.search(r"Audio:\s*([a-zA-Z0-9_]+)", audio_line).group(1),
        "audio_sample_rate": int(sample_match.group(1)),
        "audio_channels": channel_count,
    }


def srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


async def make_voice_files(root: Path) -> list[Path]:
    paths = []
    for index, scene in enumerate(SCENES, start=1):
        path = root / f"scene-{index:02d}.mp3"
        talk = edge_tts.Communicate(scene["narration"], VOICE, rate="+7%", volume="+0%")
        await talk.save(str(path))
        if not path.is_file() or path.stat().st_size < 1000:
            raise RuntimeError(f"Persian TTS did not create scene {index}")
        paths.append(path)
    return paths


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bamo-aurora-magnetosphere-") as tmp:
        root = Path(tmp)
        voices = asyncio.run(make_voice_files(root))
        voice_lengths = [probe_duration(p) for p in voices]
        print("VOICE_CLIP_SECONDS=" + json.dumps([round(value, 3) for value in voice_lengths]))
        scene_durations = [max(3.0, d + 0.18) for d in voice_lengths]

        project = {
            "format": "short",
            "fps": FPS,
            "title": TOPIC,
            "scenes": [
                {**scene, "duration": duration}
                for scene, duration in zip(SCENES, scene_durations)
            ],
        }
        total_duration = sum(scene_durations)
        if not 15 <= total_duration <= 30:
            raise RuntimeError(f"Unexpected short duration: {total_duration:.2f}s")

        silent = root / "visual-only.mp4"
        render_html_project(project, silent, fps=FPS, width=WIDTH, height=HEIGHT)

        cmd = ["ffmpeg", "-y"]
        for voice in voices:
            cmd += ["-i", str(voice)]
        cmd += ["-i", str(silent)]
        filters = []
        labels = []
        for i, duration in enumerate(scene_durations):
            filters.append(
                f"[{i}:a]apad=pad_dur=0.5,atrim=duration={duration:.3f},"
                f"asetpts=PTS-STARTPTS[a{i}]"
            )
            labels.append(f"[a{i}]")
        filters.append("".join(labels) + f"concat=n={len(voices)}:v=0:a=1[aout]")
        cmd += [
            "-filter_complex", ";".join(filters),
            "-map", f"{len(voices)}:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", "-t", f"{total_duration:.3f}", str(OUT),
        ]
        run(cmd)
        # Probe the silent render before TemporaryDirectory removes it.
        video_duration = probe_duration(silent)

        cursor = 0.0
        srt_blocks = []
        for i, (scene, duration) in enumerate(zip(SCENES, scene_durations), start=1):
            srt_blocks.append(
                f"{i}\n{srt_time(cursor)} --> {srt_time(cursor + duration)}\n{scene['text']}\n"
            )
            cursor += duration
        SRT.write_text("\n".join(srt_blocks), encoding="utf-8")

    run([
        "ffmpeg", "-y", "-i", str(OUT), "-vf",
        "fps=1/3,scale=360:-1,tile=3x3", "-frames:v", "1", str(REVIEW)
    ])

    media = probe_media_info(OUT)
    if (media["width"], media["height"]) != (WIDTH, HEIGHT):
        raise RuntimeError("Final MP4 has unexpected dimensions")
    if abs(float(media["fps"]) - FPS) > 0.01:
        raise RuntimeError("Final MP4 has unexpected frame rate")
    actual_duration = float(media["duration"])
    audio_duration = total_duration
    if not 15 <= actual_duration <= 30:
        raise RuntimeError("Final MP4 duration is outside Shorts target")
    if abs(video_duration - audio_duration) > 0.10 or abs(actual_duration - total_duration) > 0.10:
        raise RuntimeError(f"Audio/video duration mismatch: audio={audio_duration:.3f}s video={video_duration:.3f}s container={actual_duration:.3f}s")
    if any(scene["text"] != scene["narration"] for scene in SCENES):
        raise RuntimeError("On-screen text does not exactly match the narrated scene text")
    subtitle_text = SRT.read_text(encoding="utf-8")
    if len(re.findall(r"(?m)^\d+$", subtitle_text)) != len(SCENES):
        raise RuntimeError("Subtitle cue count does not match scene count")
    if any(scene["text"] not in subtitle_text for scene in SCENES):
        raise RuntimeError("Subtitle text does not match narration text")
    if not REVIEW.is_file() or REVIEW.stat().st_size < 10000:
        raise RuntimeError("Visual review contact sheet was not created")

    report = {
        "topic": TOPIC,
        "date": "2026-11-11",
        "engine": "BAMO HTML/WebGL ray-marched 3D Earth magnetosphere, solar-wind particles and auroral curtains",
        "voice": VOICE,
        "duration_seconds": round(actual_duration, 3),
        "video_duration_seconds": round(video_duration, 3),
        "audio_duration_seconds": round(audio_duration, 3),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "audio_sample_rate": media["audio_sample_rate"],
        "audio_channels": media["audio_channels"],
        "video_codec": media["video_codec"],
        "audio_codec": media["audio_codec"],
        "caption_count": len(SCENES),
        "voice_clip_durations_seconds": [round(value, 3) for value in voice_lengths],
        "caption_alignment": "each on-screen caption exactly matches its separate Persian narration clip; cue timing follows that clip",
        "visual_scene_motifs": ["aurora", "aurora_solar_wind", "aurora_magnetosphere", "aurora_atmosphere", "aurora_photons", "aurora_colors"],
        "visual_design": "Ray-marched 3D Earth sphere, four dipole-like magnetic loops, five moving auroral curtains, solar-wind particle stream and orbiting perspective camera; six distinct palettes and phase offsets",
        "visual_review_status": "pending manual frame inspection",
        "quality_gate": "TECHNICAL_PASS_PENDING_MANUAL_VISUAL_REVIEW",
        "sources": SOURCES,
        "youtube_published": False,
    }
    QA.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    print(f"MP4={OUT.resolve()}")
    print(f"SRT={SRT.resolve()}")
    print(f"QA={QA.resolve()}")
    print(f"REVIEW={REVIEW.resolve()}")


if __name__ == "__main__":
    main()
