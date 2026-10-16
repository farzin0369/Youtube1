#!/usr/bin/env python3
"""Persian narration + readable captions. Refuse if video fails QA."""
from __future__ import annotations

import asyncio
import re
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    "وقتی همه درها بسته به نظر می‌رسند، "
    "یک نور هنوز راه را نشان می‌دهد. "
    "از نو شروع کن. "
    "تو قوی‌تری از چیزی که فکر می‌کنی."
)
# Male Persian — slower, calmer delivery
VOICE = "fa-IR-FaridNeural"
MIN_VIDEO_BYTES = 200_000


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


def write_ass(path: Path, lines: list[tuple[float, float, str]], w=720, h=1280) -> None:
    def ts(t: float) -> str:
        hh = int(t // 3600)
        mm = int((t % 3600) // 60)
        ss = t % 60
        return f"{hh:d}:{mm:02d}:{ss:05.2f}"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,5,2,2,36,36,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start, end, text in lines:
        t = text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        events.append(f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{t}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


async def synth(text: str, out: Path) -> None:
    import edge_tts
    # Slower rate + soft pitch for less robotic feel
    communicate = edge_tts.Communicate(text, VOICE, rate="-12%", pitch="-2Hz")
    await communicate.save(str(out))


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "output/colab_cli")
    video_in = root / "video_raw.mp4"
    if not video_in.is_file():
        print("missing video_raw")
        return 1
    if video_in.stat().st_size < MIN_VIDEO_BYTES:
        print(f"QA FAIL: video too small ({video_in.stat().st_size}) — will not publish trash")
        return 2

    audio = root / "narration.mp3"
    ass = root / "captions.ass"
    final = root / "final_short.mp4"

    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])
    asyncio.run(synth(SCRIPT, audio))
    adur = media_duration(audio)
    vdur = media_duration(video_in)
    print(f"audio={adur:.2f}s video={vdur:.2f}s bytes={video_in.stat().st_size}")

    sentences = [s.strip() for s in re.split(r"[\.؟!]+", SCRIPT) if s.strip()]
    n = max(len(sentences), 1)
    lines = [(adur * i / n, adur * (i + 1) / n, s) for i, s in enumerate(sentences)]
    write_ass(ass, lines)

    # Match video length to narration; keep motion (don't overstretch >2x)
    stretch = min(max(adur / max(vdur, 0.1), 0.85), 2.0)
    vf = (
        f"setpts={stretch}*PTS,"
        "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
        f"ass={ass.as_posix()}"
    )
    vf = "".join(vf)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_in), "-i", str(audio),
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(final),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1200:])
        return 1
    print("OK", final, final.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
