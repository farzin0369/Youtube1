#!/usr/bin/env python3
"""Add Persian male TTS + readable ASS captions onto video_raw.mp4 → final short."""
from __future__ import annotations

import asyncio
import re
import subprocess
import sys
from pathlib import Path

# Hooky spiritual Persian narration (ImamAli110 style)
SCRIPT = (
    "وقتی همه درها بسته به نظر می‌رسند، "
    "یک نور هنوز راه را نشان می‌دهد. "
    "از نو شروع کن. "
    "تو قوی‌تری از چیزی که فکر می‌کنی."
)

VOICE = "fa-IR-FaridNeural"  # male Persian Edge TTS


def ass_escape(s: str) -> str:
    return s.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def write_ass(path: Path, lines: list[tuple[float, float, str]], w: int = 720, h: int = 1280) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,54,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,4,1,2,40,40,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def ts(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h:d}:{m:02d}:{s:05.2f}"

    events = []
    for start, end, text in lines:
        # short lines for readability
        chunk = ass_escape(text.strip())
        events.append(f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{chunk}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


async def synth_edge(text: str, out: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, VOICE, rate="-8%")
    await communicate.save(str(out))


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "output/colab_cli")
    video_in = root / "video_raw.mp4"
    if not video_in.is_file():
        print("missing", video_in)
        return 1

    audio = root / "narration.mp3"
    ass = root / "captions.ass"
    final = root / "final_short.mp4"

    print("[finish] TTS", VOICE, flush=True)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])
    asyncio.run(synth_edge(SCRIPT, audio))
    adur = media_duration(audio)
    vdur = media_duration(video_in)
    print(f"[finish] audio={adur:.2f}s video={vdur:.2f}s", flush=True)

    # Split script into caption chunks by sentence
    parts = [p.strip() for p in re.split(r"([.!?؟]+)\s*", SCRIPT) if p and p.strip()]
    # recombine punctuation
    sentences: list[str] = []
    i = 0
    while i < len(parts):
        if i + 1 < len(parts) and parts[i + 1] in ".!?؟":
            sentences.append(parts[i] + parts[i + 1])
            i += 2
        else:
            sentences.append(parts[i])
            i += 1
    # simpler split on Persian / period-like
    sentences = [s.strip() for s in re.split(r"[\.؟!]+", SCRIPT) if s.strip()]
    if not sentences:
        sentences = [SCRIPT]

    # equal time slices over audio
    n = len(sentences)
    lines = []
    for idx, sent in enumerate(sentences):
        start = adur * idx / n
        end = adur * (idx + 1) / n
        lines.append((start, end, sent))
    write_ass(ass, lines)

    # Stretch video to audio length if needed, burn ASS, mux audio
    # Use setpts to match duration
    if vdur < 0.1:
        print("bad video duration")
        return 1
    speed = vdur / max(adur, 0.1)
    # If video shorter, slow it; if longer, speed up slightly
    vf = (
        f"setpts={adur/vdur}*PTS,"
        "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
        f"ass={ass.as_posix()}"
    )
    vf = "".join(vf)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_in),
        "-i", str(audio),
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(final),
    ]
    print("[finish] ffmpeg", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        return 1
    print("[finish] OK", final, final.stat().st_size, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
