"""Render BAMO's 2026-11-09 Persian science short about Saturn's rings."""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from app.html_motion_renderer import render_html_project

OUT = Path("artifacts/bamo-science-short-20261109.mp4")
SRT = OUT.with_suffix(".srt")
QA = OUT.with_name("bamo-science-short-20261109-qa.json")
REVIEW = OUT.with_name("bamo-science-short-20261109-review.jpg")
VOICE = "fa-IR-DilaraNeural"
FPS = 24
WIDTH = 1080
HEIGHT = 1920
TOPIC = "حلقه‌های زحل از چه ساخته شده‌اند و چرا یکپارچه نیستند؟"
SOURCES = [
    "https://science.nasa.gov/mission/cassini/science/rings/",
    "https://science.nasa.gov/mission/cassini/faq/",
    "https://www.jpl.nasa.gov/images/pia18295-translucent-rings/",
]

SCENES = [
    {
        "text": "حلقه‌های زحل جامد نیستند؛ میلیاردها تکه یخ‌اند که دور سیاره می‌چرخند.",
        "narration": "حلقه‌های زحل جامد نیستند؛ میلیاردها تکه یخ‌اند که دور سیاره می‌چرخند.",
        "visual_prompt": "نمای سینمایی سه‌بعدی از زحل با حلقه‌های یخی و حرکت آرام دوربین",
        "motif": "cosmic",
        "palette": {"bg": "#030817", "primary": "#e6c58c", "secondary": "#8bd3e6", "accent": "#f8e7bd"},
    },
    {
        "text": "بیشترشان یخ آب‌اند؛ از غبار ریز تا تکه‌هایی به بزرگی کوه.",
        "narration": "بیشترشان یخ آب‌اند؛ از غبار ریز تا تکه‌هایی به بزرگی کوه.",
        "visual_prompt": "نمای نزدیک ذرات یخی حلقه و مدارهای مستقل پیرامون سیاره",
        "motif": "ellipse",
        "palette": {"bg": "#07121c", "primary": "#a5e6f2", "secondary": "#d7c6a3", "accent": "#ffffff"},
    },
    {
        "text": "با پهنای عظیم، ضخامت حلقه‌های اصلی فقط حدود ده متر است.",
        "narration": "با پهنای عظیم، ضخامت حلقه‌های اصلی فقط حدود ده متر است.",
        "visual_prompt": "نمای لبه‌ای حلقه‌های بسیار نازک در کنار کره عظیم زحل",
        "motif": "cosmic",
        "palette": {"bg": "#100c19", "primary": "#f5c77e", "secondary": "#c4a7e7", "accent": "#f7e6c5"},
    },
    {
        "text": "هر ذره مدار خودش را دارد؛ نزدیک‌ترها سریع‌تر از دورترها می‌چرخند.",
        "narration": "هر ذره مدار خودش را دارد؛ نزدیک‌ترها سریع‌تر از دورترها می‌چرخند.",
        "visual_prompt": "نمای مداری از ذرات نزدیک و دور با سرعت‌های مداری متفاوت",
        "motif": "ellipse",
        "palette": {"bg": "#06151b", "primary": "#69d7d0", "secondary": "#e8c58e", "accent": "#b7f0ff"},
    },
    {
        "text": "پس حلقه‌ها نوار یکپارچه نیستند؛ ازدحامی از ذرات مستقل‌اند.",
        "narration": "پس حلقه‌ها نوار یکپارچه نیستند؛ ازدحامی از ذرات مستقل‌اند.",
        "visual_prompt": "عقب‌نشینی دوربین و آشکارشدن ساختار حلقه‌ای زحل در فضا",
        "motif": "cosmic",
        "palette": {"bg": "#030a18", "primary": "#e9d2a1", "secondary": "#83c8de", "accent": "#f6e6c6"},
    },
]


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {' '.join(cmd[:4])}\n{result.stderr[-2500:]}")
    return result.stdout.strip()


def probe_duration(path: Path) -> float:
    return float(run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ]))


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
        talk = edge_tts.Communicate(scene["narration"], VOICE, rate="+1%", volume="+0%")
        await talk.save(str(path))
        if not path.is_file() or path.stat().st_size < 1000:
            raise RuntimeError(f"Persian TTS did not create scene {index}")
        paths.append(path)
    return paths


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bamo-saturn-rings-") as tmp:
        root = Path(tmp)
        voices = asyncio.run(make_voice_files(root))
        voice_lengths = [probe_duration(p) for p in voices]
        scene_durations = [max(3.4, d + 0.45) for d in voice_lengths]

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
                f"[{i}:a]apad=pad_dur=0.6,atrim=duration={duration:.3f},"
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

    run(["ffmpeg", "-y", "-i", str(OUT), "-vf", "fps=1/4,scale=360:-1,tile=3x2", "-frames:v", "1", str(REVIEW)])

    metadata = json.loads(run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(OUT)
    ]))
    video = next((x for x in metadata["streams"] if x.get("codec_type") == "video"), None)
    audio = next((x for x in metadata["streams"] if x.get("codec_type") == "audio"), None)
    if not video or not audio:
        raise RuntimeError("Final MP4 is missing its video or narration stream")
    if (video.get("width"), video.get("height")) != (WIDTH, HEIGHT):
        raise RuntimeError("Final MP4 has unexpected dimensions")
    if video.get("r_frame_rate") != f"{FPS}/1":
        raise RuntimeError("Final MP4 has unexpected frame rate")
    actual_duration = float(metadata["format"]["duration"])
    video_duration = float(video.get("duration") or actual_duration)
    audio_duration = float(audio.get("duration") or actual_duration)
    if not 15 <= actual_duration <= 30:
        raise RuntimeError("Final MP4 duration is outside Shorts target")
    if abs(video_duration - audio_duration) > 0.10:
        raise RuntimeError(f"Audio/video duration mismatch: {audio_duration:.3f}s vs {video_duration:.3f}s")
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
        "date": "2026-11-09",
        "engine": "BAMO HTML/WebGL ray-marched ringed-planet 3D engine",
        "voice": VOICE,
        "duration_seconds": round(actual_duration, 3),
        "video_duration_seconds": round(video_duration, 3),
        "audio_duration_seconds": round(audio_duration, 3),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "audio_sample_rate": audio.get("sample_rate"),
        "audio_channels": audio.get("channels"),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "caption_count": len(SCENES),
        "caption_alignment": "each caption exactly matches its narration segment; SRT timing derives from the corresponding TTS clip",
        "visual_design": "ringed-planet SDF geometry with independently orbiting satellite motif and moving perspective camera",
        "visual_review_status": "pending manual frame inspection",
        "quality_gate": "TECHNICAL_PASS_PENDING_VISUAL_REVIEW",
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
