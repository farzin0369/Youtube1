"""Render BAMO's 2026-11-08 Persian science short: wave interference."""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from app.html_motion_renderer import render_html_project

OUT = Path("artifacts/bamo-science-short-20261108.mp4")
SRT = OUT.with_suffix(".srt")
QA = OUT.with_name("bamo-science-short-20261108-qa.json")
REVIEW = OUT.with_name("bamo-science-short-20261108-review.jpg")
VOICE = "fa-IR-FaridNeural"
FPS = 24
WIDTH = 1080
HEIGHT = 1920
TOPIC = "چرا دو موج گاهی همدیگر را تقویت یا خنثی می‌کنند؟"
SOURCES = [
    "https://openstax.org/books/physics/pages/13-3-wave-interaction-superposition-and-interference",
    "https://www.acs.psu.edu/drussell/Demos/superposition/superposition.html",
]

SCENES = [
    {
        "text": "دو موج می‌توانند همدیگر را تقویت کنند… یا تضعیف!",
        "narration": "دو موج می‌توانند همدیگر را تقویت کنند… یا تضعیف!",
        "visual_prompt": "دو منبع همدوس در میدان موجی سه‌بعدی؛ نمای باز و نزدیک‌شدن دوربین",
        "motif": "interference",
        "phase": 0.0,
        "phase_sweep": 0.5,
        "palette": {"bg": "#030817", "primary": "#22d3ee", "secondary": "#818cf8", "accent": "#f0abfc"},
    },
    {
        "text": "وقتی قله‌ها هم‌زمان برسند، دامنهٔ برآیند بزرگ‌تر می‌شود.",
        "narration": "وقتی قله‌ها هم‌زمان برسند، دامنهٔ برآیند بزرگ‌تر می‌شود.",
        "visual_prompt": "تداخل سازنده دو موج هم‌فاز؛ برآمدگی‌های موج برجسته و روشن",
        "motif": "interference",
        "phase": 0.0,
        "phase_sweep": 0.0,
        "palette": {"bg": "#03151a", "primary": "#2dd4bf", "secondary": "#4ade80", "accent": "#facc15"},
    },
    {
        "text": "اگر قلهٔ یکی به درهٔ دیگری برسد، موج‌های هم‌اندازه خنثی می‌شوند.",
        "narration": "اگر قلهٔ یکی به درهٔ دیگری برسد، موج‌های هم‌اندازه خنثی می‌شوند.",
        "visual_prompt": "تداخل ویرانگر با اختلاف فاز ۱۸۰ درجه؛ خطوط گره و سطح کم‌دامنه",
        "motif": "interference",
        "phase": 3.14159265,
        "phase_sweep": 0.0,
        "palette": {"bg": "#10071d", "primary": "#c084fc", "secondary": "#f472b6", "accent": "#22d3ee"},
    },
    {
        "text": "این تفاوت به اختلاف فاز بستگی دارد؛ نیم‌دوره یعنی ۱۸۰ درجه.",
        "narration": "این تفاوت به اختلاف فاز بستگی دارد؛ نیم‌دوره یعنی ۱۸۰ درجه.",
        "visual_prompt": "تداخل با اختلاف فاز میانی؛ ترکیب نواحی تقویت و تضعیف",
        "motif": "interference",
        "phase": 1.57079633,
        "phase_sweep": 0.0,
        "palette": {"bg": "#18080b", "primary": "#fb7185", "secondary": "#f97316", "accent": "#fef08a"},
    },
    {
        "text": "انرژی نابود نمی‌شود؛ الگوی شدت در فضا بازتوزیع می‌شود.",
        "narration": "انرژی نابود نمی‌شود؛ الگوی شدت در فضا بازتوزیع می‌شود.",
        "visual_prompt": "نمای کلی میدان دو منبع با نوارهای روشن و تاریک و تغییر تدریجی فاز",
        "motif": "interference",
        "phase": 0.0,
        "phase_sweep": 6.2831853,
        "palette": {"bg": "#061020", "primary": "#38bdf8", "secondary": "#a78bfa", "accent": "#fbbf24"},
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
        talk = edge_tts.Communicate(
            scene["narration"], VOICE, rate="+2%", volume="+0%"
        )
        await talk.save(str(path))
        if not path.is_file() or path.stat().st_size < 1000:
            raise RuntimeError(f"Persian TTS did not create scene {index}")
        paths.append(path)
    return paths


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bamo-wave-interference-") as tmp:
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
        filters.append(
            "".join(labels) + f"concat=n={len(voices)}:v=0:a=1[aout]"
        )
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
    if len(re.findall(r"(?m)^\\d+$", subtitle_text)) != len(SCENES):
        raise RuntimeError("Subtitle cue count does not match scene count")
    if any(scene["text"] not in subtitle_text for scene in SCENES):
        raise RuntimeError("Subtitle text does not match narration text")
    if not REVIEW.is_file() or REVIEW.stat().st_size < 10000:
        raise RuntimeError("Visual review contact sheet was not created")

    report = {
        "topic": TOPIC,
        "date": "2026-11-08",
        "engine": "BAMO HTML/WebGL ray-marched two-source interference surface",
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
        "visual_design": "160x160 animated WebGL mesh, two coherent sources, phase-controlled interference, moving perspective camera",
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
