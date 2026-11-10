"""Render BAMO's 2026-11-10 Persian science short about xylem water transport."""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from app.html_motion_renderer import render_html_project

OUT = Path("artifacts/bamo-science-short-20261110.mp4")
SRT = OUT.with_suffix(".srt")
QA = OUT.with_name("bamo-science-short-20261110-qa.json")
REVIEW = OUT.with_name("bamo-science-short-20261110-review.jpg")
VOICE = "fa-IR-FaridNeural"
FPS = 24
WIDTH = 1080
HEIGHT = 1920
TOPIC = "درختان چطور آب را تا نوک شاخه‌ها می‌کشند؟"
SOURCES = [
    "https://organismalbio.biosci.gatech.edu/nutrition-transport-and-homeostasis/plant-transport-processes-i/",
    "https://bio.libretexts.org/Bookshelves/Introductory_and_General_Biology/General_Biology_2e_%28OpenStax%29/06%3A_Unit_VI-_Plant_Structure_and_Function/6.01%3A_Plant_Form_and_Physiology/6.1.06%3A_Transport_of_Water_and_Solutes_in_Plants",
    "https://open.lib.umn.edu/horticulture/chapter/11-1-plants-and-water/",
]

SCENES = [
    {
        "text": "درختان بلند، آب را چطور تا برگ‌ها بالا می‌برند؟",
        "narration": "درختان بلند، آب را چطور تا برگ‌ها بالا می‌برند؟",
        "visual_prompt": "نمای کامل یک درخت سه‌بعدی؛ دوربین از ریشه‌ها به سوی تاج و برگ‌ها بالا می‌رود",
        "motif": "plant",
        "palette": {"bg": "#06131b", "primary": "#50dfbd", "secondary": "#9bc9ef", "accent": "#f3d58a"},
    },
    {
        "text": "آب از ریشه وارد آوندهای چوبی، زایلم، می‌شود.",
        "narration": "آب از ریشه وارد آوندهای چوبی، زایلم، می‌شود.",
        "visual_prompt": "نمای ماکرو سه‌بعدی ریشه و تارهای کشنده در خاک؛ قطره‌های آب به سمت ریشه حرکت می‌کنند",
        "motif": "root",
        "palette": {"bg": "#11140f", "primary": "#6ed8b2", "secondary": "#c5a77c", "accent": "#a6e8ff"},
    },
    {
        "text": "پیوندهای هیدروژنی، مولکول‌های آب را کنار هم نگه می‌دارند.",
        "narration": "پیوندهای هیدروژنی، مولکول‌های آب را کنار هم نگه می‌دارند.",
        "visual_prompt": "برش مقطعی سه‌بعدی از لوله زایلم؛ ستون پیوسته آب و قطره‌های آبی در حال صعود",
        "motif": "xylem",
        "palette": {"bg": "#071725", "primary": "#55d9ff", "secondary": "#6ba6e8", "accent": "#e5f8ff"},
    },
    {
        "text": "در برگ، آب تبخیر و از روزنه‌ها خارج می‌شود.",
        "narration": "در برگ، آب تبخیر و از روزنه‌ها خارج می‌شود.",
        "visual_prompt": "نمای میکروسکوپی سه‌بعدی روزنه برگ با دو سلول نگهبان و بخار آب در حال خروج",
        "motif": "stomata",
        "palette": {"bg": "#101b16", "primary": "#82e0ad", "secondary": "#b8e5d0", "accent": "#b8dfff"},
    },
    {
        "text": "تبخیر، در زایلم کشش ایجاد می‌کند و آب را بالا می‌کشد.",
        "narration": "تبخیر، در زایلم کشش ایجاد می‌کند و آب را بالا می‌کشد.",
        "visual_prompt": "نمای نزدیک لوله زایلم با ستون آب پیوسته؛ ذرات آب رو به بالا حرکت می‌کنند",
        "motif": "xylem",
        "palette": {"bg": "#07131f", "primary": "#41c9ee", "secondary": "#83b8e8", "accent": "#f2d78d"},
    },
    {
        "text": "این سازوکار، کشش–همبستگی است؛ ریشه پمپ اصلی نیست.",
        "narration": "این سازوکار، کشش–همبستگی است؛ ریشه پمپ اصلی نیست.",
        "visual_prompt": "عقب‌نشینی سینمایی دوربین از ریشه تا تاج درخت و نمایش مسیر پیوسته آب تا برگ‌ها",
        "motif": "plant",
        "palette": {"bg": "#06131b", "primary": "#70e2bf", "secondary": "#9dcdf1", "accent": "#f4d68b"},
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
    match = re.search(r"Duration:\\s*(\\d+):(\\d+):(\\d+(?:\\.\\d+)?)", output)
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
    duration_match = re.search(r"Duration:\\s*(\\d+):(\\d+):(\\d+(?:\\.\\d+)?)", output)
    dimensions = re.search(r"\\b(\\d{2,5})x(\\d{2,5})\\b", video_line)
    fps_match = re.search(r"([0-9]+(?:\\.[0-9]+)?)\\s+fps\\b", video_line)
    sample_match = re.search(r"([0-9]+)\\s+Hz\\b", audio_line)
    if not video_line or not audio_line or not duration_match or not dimensions or not fps_match or not sample_match:
        raise RuntimeError(f"FFmpeg could not inspect final MP4 streams: {output[-1800:]}")
    hours, minutes, seconds = duration_match.groups()
    channel_count = 1 if re.search(r"\\bmono\\b", audio_line) else (2 if re.search(r"\\bstereo\\b", audio_line) else 0)
    return {
        "duration": int(hours) * 3600 + int(minutes) * 60 + float(seconds),
        "width": int(dimensions.group(1)),
        "height": int(dimensions.group(2)),
        "fps": float(fps_match.group(1)),
        "video_codec": re.search(r"Video:\\s*([a-zA-Z0-9_]+)", video_line).group(1),
        "audio_codec": re.search(r"Audio:\\s*([a-zA-Z0-9_]+)", audio_line).group(1),
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
        talk = edge_tts.Communicate(scene["narration"], VOICE, rate="+8%", volume="+0%")
        await talk.save(str(path))
        if not path.is_file() or path.stat().st_size < 1000:
            raise RuntimeError(f"Persian TTS did not create scene {index}")
        paths.append(path)
    return paths


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bamo-xylem-water-") as tmp:
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
    video_duration = probe_duration(silent)
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
        "date": "2026-11-10",
        "engine": "BAMO HTML/WebGL ray-marched 3D plant vascular scenes",
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
        "visual_scene_motifs": ["plant", "root", "xylem", "stomata", "xylem", "plant"],
        "visual_design": "dedicated 3D plant silhouette with roots and leaves, cutaway xylem vessel with upward water particles, stomata with escaping vapour, and root hairs; orbiting perspective camera",
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
