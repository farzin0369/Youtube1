"""Render BAMO's 2026-11-12 Persian science short about gecko dry adhesion."""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from app.html_motion_renderer import render_html_project

OUT = Path("artifacts/bamo-science-short-20261112.mp4")
SRT = OUT.with_suffix(".srt")
QA = OUT.with_name("bamo-science-short-20261112-qa.json")
REVIEW = OUT.with_name("bamo-science-short-20261112-review.jpg")
VOICE = "fa-IR-FaridNeural"
FPS = 24
WIDTH = 1080
HEIGHT = 1920
TOPIC = "گِکو چگونه بدون چسب به شیشه می‌چسبد؟"
SOURCES = [
    "https://www.nature.com/articles/35015073",
    "https://doi.org/10.1073/pnas.192252799",
    "https://newsarchive.berkeley.edu/news/media/releases/2000/06/07_gecko.html",
]

SCENES = [
    {
        "text": "گِکو از شیشه بالا می‌رود؛ بدون چسب و بدون مکش!",
        "narration": "گِکو از شیشه بالا می‌رود؛ بدون چسب و بدون مکش!",
        "visual_prompt": "مارمولک گکو روی دیواره شیشه‌ای، نمای سه‌بعدی کامل با حرکت دوربین مداری",
        "motif": "gecko",
        "phase": 0.0,
        "phase_sweep": 0.65,
        "palette": {"bg": "#06101b", "primary": "#6bd6a8", "secondary": "#b8c98b", "accent": "#f2d38a"},
    },
    {
        "text": "زیر انگشتانش، رشته‌های کراتینیِ ریزی به نام «ستا» قرار دارند.",
        "narration": "زیر انگشتانش، رشته‌های کراتینیِ ریزی به نام «ستا» قرار دارند.",
        "visual_prompt": "نمای ماکرو از کف انگشت گکو و پنج انگشت پهن‌شونده روی سطح شیشه",
        "motif": "gecko_toe",
        "phase": 0.7,
        "phase_sweep": 0.45,
        "palette": {"bg": "#07131d", "primary": "#65d8c0", "secondary": "#9ec6a6", "accent": "#f6d98e"},
    },
    {
        "text": "هر ستا به صدها نوکِ پهن و میکروسکوپی تقسیم می‌شود.",
        "narration": "هر ستا به صدها نوکِ پهن و میکروسکوپی تقسیم می‌شود.",
        "visual_prompt": "بزرگ‌نمایی سه‌بعدی رشته‌های ستا که در انتها به شاخه‌های پهن و تخت می‌رسند",
        "motif": "gecko_setae",
        "phase": 1.4,
        "phase_sweep": 0.6,
        "palette": {"bg": "#0a0b1b", "primary": "#67d8e8", "secondary": "#9b8ee8", "accent": "#f4c879"},
    },
    {
        "text": "نوک‌ها به سطح نزدیک می‌شوند؛ نیروهای واندروالس آن‌ها را نگه می‌دارند.",
        "narration": "نوک‌ها به سطح نزدیک می‌شوند؛ نیروهای واندروالس آن‌ها را نگه می‌دارند.",
        "visual_prompt": "تماس نزدیک نوک‌های میکروسکوپی با سطح شیشه و نمایش فاصله بسیار کم مولکولی",
        "motif": "gecko_contact",
        "phase": 2.2,
        "phase_sweep": 0.5,
        "palette": {"bg": "#0b101a", "primary": "#62d9d0", "secondary": "#8db7e8", "accent": "#f8d27c"},
    },
    {
        "text": "گِکو با تغییر زاویهٔ انگشت جدا می‌شود؛ این ساختار الهام‌بخش چسب خشک است.",
        "narration": "گِکو با تغییر زاویهٔ انگشت جدا می‌شود؛ این ساختار الهام‌بخش چسب خشک است.",
        "visual_prompt": "انگشت گکو با حرکت چرخشی از سطح شیشه جدا می‌شود و دوربین به نمای کامل مارمولک عقب می‌رود",
        "motif": "gecko_toe",
        "phase": 3.1,
        "phase_sweep": 1.0,
        "palette": {"bg": "#07121a", "primary": "#7bdfb4", "secondary": "#a4c8db", "accent": "#f4d28b"},
    },
]


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {' '.join(cmd[:4])}\n{result.stderr[-2500:]}")
    return result.stdout.strip()


def probe_duration(path: Path) -> float:
    value = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ])
    return float(value)


def probe_media(path: Path) -> dict[str, object]:
    data = json.loads(run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ]))
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    audio = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    if not video or not audio:
        raise RuntimeError("Final MP4 is missing a video or audio stream")
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
    numerator, denominator = rate.split("/", 1)
    fps = float(numerator) / max(1.0, float(denominator))
    return {
        "duration": float(data["format"]["duration"]),
        "video_duration": float(video.get("duration") or data["format"]["duration"]),
        "audio_duration": float(audio.get("duration") or data["format"]["duration"]),
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": fps,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "audio_sample_rate": int(audio.get("sample_rate") or 0),
        "audio_channels": int(audio.get("channels") or 0),
        "size_bytes": int(data["format"].get("size") or 0),
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
        talk = edge_tts.Communicate(
            scene["narration"], VOICE, rate="+5%", volume="+0%", pitch="+0Hz"
        )
        await talk.save(str(path))
        if not path.is_file() or path.stat().st_size < 1000:
            raise RuntimeError(f"Persian TTS did not create scene {index}")
        paths.append(path)
    return paths


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bamo-gecko-dry-adhesion-") as tmp:
        root = Path(tmp)
        voices = asyncio.run(make_voice_files(root))
        voice_lengths = [probe_duration(p) for p in voices]
        print("VOICE_CLIP_SECONDS=" + json.dumps([round(v, 3) for v in voice_lengths]))
        scene_durations = [max(3.25, duration + 0.22) for duration in voice_lengths]

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
                f"[{i}:a]apad=pad_dur=0.35,atrim=duration={duration:.3f},"
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
        video_duration = probe_duration(silent)

        cursor = 0.0
        blocks = []
        for i, (scene, duration) in enumerate(zip(SCENES, scene_durations), start=1):
            blocks.append(
                f"{i}\n{srt_time(cursor)} --> {srt_time(cursor + duration)}\n{scene['text']}\n"
            )
            cursor += duration
        SRT.write_text("\n".join(blocks), encoding="utf-8")

    run([
        "ffmpeg", "-y", "-i", str(OUT), "-vf",
        "fps=1/3,scale=360:-1,tile=3x2", "-frames:v", "1", str(REVIEW)
    ])

    media = probe_media(OUT)
    if (media["width"], media["height"]) != (WIDTH, HEIGHT):
        raise RuntimeError("Final MP4 has unexpected dimensions")
    if abs(float(media["fps"]) - FPS) > 0.01:
        raise RuntimeError("Final MP4 has unexpected frame rate")
    if media["video_codec"] != "h264" or media["audio_codec"] != "aac":
        raise RuntimeError("Unexpected final MP4 codecs")
    if not 15 <= float(media["duration"]) <= 30:
        raise RuntimeError("Final MP4 duration is outside Shorts target")
    if abs(float(media["video_duration"]) - float(media["audio_duration"])) > 0.12:
        raise RuntimeError(
            "Audio/video stream duration mismatch: "
            f"{media['audio_duration']:.3f}s vs {media['video_duration']:.3f}s"
        )
    if abs(float(media["video_duration"]) - video_duration) > 0.12:
        raise RuntimeError("Final video duration differs from the HTML/WebGL render")
    if int(media["size_bytes"]) < 100_000:
        raise RuntimeError("Final MP4 is unexpectedly small")
    if any(scene["text"] != scene["narration"] for scene in SCENES):
        raise RuntimeError("On-screen text does not exactly match narration")
    subtitle_text = SRT.read_text(encoding="utf-8")
    if len(re.findall(r"(?m)^\d+$", subtitle_text)) != len(SCENES):
        raise RuntimeError("Subtitle cue count does not match scene count")
    if any(scene["text"] not in subtitle_text for scene in SCENES):
        raise RuntimeError("Subtitle text does not match narration")
    if not REVIEW.is_file() or REVIEW.stat().st_size < 10_000:
        raise RuntimeError("Visual review contact sheet was not created")

    report = {
        "topic": TOPIC,
        "date": "2026-11-12",
        "engine": "BAMO HTML/WebGL ray-marched 3D gecko, toe-pad, branched setae and molecular-contact scenes",
        "voice": VOICE,
        "voice_clip_durations_seconds": [round(v, 3) for v in voice_lengths],
        "duration_seconds": round(float(media["duration"]), 3),
        "video_duration_seconds": round(float(media["video_duration"]), 3),
        "audio_duration_seconds": round(float(media["audio_duration"]), 3),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "audio_sample_rate": media["audio_sample_rate"],
        "audio_channels": media["audio_channels"],
        "video_codec": media["video_codec"],
        "audio_codec": media["audio_codec"],
        "file_size_bytes": media["size_bytes"],
        "caption_count": len(SCENES),
        "caption_alignment": "each RTL on-screen caption equals its separately generated Persian narration clip; SRT cue duration follows that clip with a short reading tail",
        "visual_scene_motifs": [s["motif"] for s in SCENES],
        "visual_design": "ray-marched 3D gecko on glass; close-up toe pad and digits; branched keratin setae with flattened spatula tips; near-contact surface geometry; peeling/release shot with perspective camera motion",
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
