"""Render BAMO's 2026-11-08 Persian science short: wave interference."""
from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from app.html_motion_renderer import render_html_project

OUT = Path("artifacts/bamo-science-short-20261108.mp4")
SRT = OUT.with_suffix(".srt")
QA = OUT.with_name("bamo-science-short-20261108-qa.json")
VOICE = "fa-IR-FaridNeural"
FPS = 24
WIDTH = 720
HEIGHT = 1280
TOPIC = "چرا دو موج گاهی همدیگر را تقویت و گاهی خنثی می‌کنند؟"

SCENES = [
    {
        "text": "دو موج همیشه قوی‌تر نمی‌شوند!",
        "narration": "دو موج همیشه قوی‌تر نمی‌شوند!",
        "visual_prompt": "دو منبع موج همدوس و حلقه‌های تداخل سه‌بعدی",
        "motif": "interference",
        "phase": 0.0,
        "phase_sweep": 0.0,
        "palette": {"bg": "#030817", "primary": "#22d3ee", "secondary": "#818cf8", "accent": "#f0abfc"},
    },
    {
        "text": "قله با قله؛ دامنهٔ موجِ حاصل بزرگ‌تر می‌شود.",
        "narration": "قله با قله؛ دامنهٔ موجِ حاصل بزرگ‌تر می‌شود.",
        "visual_prompt": "تداخل سازنده دو موج هم‌فاز از دو منبع نقطه‌ای",
        "motif": "interference",
        "phase": 0.0,
        "phase_sweep": 0.0,
        "palette": {"bg": "#03151a", "primary": "#2dd4bf", "secondary": "#4ade80", "accent": "#facc15"},
    },
    {
        "text": "قله با دره؛ دامنهٔ موجِ حاصل کاهش می‌یابد.",
        "narration": "قله با دره؛ دامنهٔ موجِ حاصل کاهش می‌یابد.",
        "visual_prompt": "تداخل دو موج با اختلاف فاز و نواحی کاهش دامنه",
        "motif": "interference",
        "phase": 3.14159265,
        "phase_sweep": 0.0,
        "palette": {"bg": "#10071d", "primary": "#c084fc", "secondary": "#f472b6", "accent": "#22d3ee"},
    },
    {
        "text": "نیم‌دوره اختلاف فاز؛ برآیندِ دو موجِ هم‌اندازه صفر می‌شود.",
        "narration": "نیم‌دوره اختلاف فاز؛ برآیندِ دو موجِ هم‌اندازه صفر می‌شود.",
        "visual_prompt": "سطح تداخل ویرانگر با گره‌های کم‌دامنه در میدان سه‌بعدی",
        "motif": "interference",
        "phase": 3.14159265,
        "phase_sweep": 0.0,
        "palette": {"bg": "#18080b", "primary": "#fb7185", "secondary": "#f97316", "accent": "#fef08a"},
    },
    {
        "text": "انرژی از بین نمی‌رود؛ در الگوی کلی بازتوزیع می‌شود.",
        "narration": "انرژی از بین نمی‌رود؛ در الگوی کلی بازتوزیع می‌شود.",
        "visual_prompt": "الگوی کامل تداخل موجی و نواحی تقویت و تضعیف",
        "motif": "interference",
        "phase": 1.57079633,
        "phase_sweep": 0.0,
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
    if not 15 <= actual_duration <= 30:
        raise RuntimeError("Final MP4 duration is outside Shorts target")

    report = {
        "topic": TOPIC,
        "date": "2026-11-08",
        "engine": "BAMO HTML/WebGL ray-marched two-source interference surface",
        "voice": VOICE,
        "duration_seconds": round(actual_duration, 3),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "caption_count": len(SCENES),
        "caption_alignment": "one caption per narration segment; scene durations derived from each TTS clip",
        "quality_gate": "PASS",
        "youtube_published": False,
    }
    QA.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    print(f"MP4={OUT.resolve()}")
    print(f"SRT={SRT.resolve()}")
    print(f"QA={QA.resolve()}")


if __name__ == "__main__":
    main()
