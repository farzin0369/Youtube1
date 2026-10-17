#!/usr/bin/env python3
"""Free cinematic short — zero GPU, zero paid API, zero fragile CDN.

Visuals: procedural cinematic scenes via FFmpeg (light rays, particles, gradients).
Audio: Edge-TTS Persian male.
Captions: ASS burned-in.
Runs on GitHub Actions CPU every day.
"""
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
VOICE = "fa-IR-FaridNeural"


def run(cmd: list[str], timeout: int = 180) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(r.stderr[-1200:])
        raise RuntimeError(cmd[0])


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


async def tts(text: str, out: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate="-10%", pitch="-2Hz").save(str(out))


def write_ass(path: Path, sentences: list[str], duration: float) -> None:
    def ts(t: float) -> str:
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    n = max(len(sentences), 1)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,5,2,2,40,40,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for i, sent in enumerate(sentences):
        start, end = duration * i / n, duration * (i + 1) / n
        t = sent.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{t}")
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def make_scene(path: Path, duration: float, kind: int) -> None:
    """Procedural vertical cinematic scene (spiritual atmosphere)."""
    # Dark base + golden light motion — different motion per scene
    if kind == 0:
        # rising golden particles / light dust
        fc = (
            f"color=c=0x0a0e1a:s=720x1280:d={duration:.3f}:r=24,"
            f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)',"
            f"noise=alls=12:allf=t,"
            f"hue=s=0.3,"
            f"geq="
            f"r='min(255,r(X,Y)+40*exp(-((X-360)*(X-360)+(Y-mod(T*40,1400))*(Y-mod(T*40,1400)))/80000))':"
            f"g='min(255,g(X,Y)+28*exp(-((X-360)*(X-360)+(Y-mod(T*40,1400))*(Y-mod(T*40,1400)))/80000))':"
            f"b='min(255,b(X,Y)+8*exp(-((X-360)*(X-360)+(Y-mod(T*40,1400))*(Y-mod(T*40,1400)))/80000))',"
            f"eq=contrast=1.15:brightness=-0.05:saturation=1.1"
        )
    elif kind == 1:
        # soft radial glow pulse center
        fc = (
            f"color=c=0x0c1220:s=720x1280:d={duration:.3f}:r=24,"
            f"geq="
            f"r='min(255,12+55*exp(-((X-360)^2+(Y-640)^2)/(180000+40000*sin(T*1.2))))':"
            f"g='min(255,10+40*exp(-((X-360)^2+(Y-640)^2)/(180000+40000*sin(T*1.2))))':"
            f"b='min(255,18+25*exp(-((X-360)^2+(Y-640)^2)/(220000+30000*sin(T*0.8))))',"
            f"eq=contrast=1.1:saturation=1.05"
        )
    elif kind == 2:
        # vertical light beam
        fc = (
            f"color=c=0x080c18:s=720x1280:d={duration:.3f}:r=24,"
            f"geq="
            f"r='min(255,8+70*exp(-((X-360-40*sin(T*0.7))^2)/12000)*exp(-((Y-640)^2)/900000))':"
            f"g='min(255,6+50*exp(-((X-360-40*sin(T*0.7))^2)/12000)*exp(-((Y-640)^2)/900000))':"
            f"b='min(255,10+20*exp(-((X-360-40*sin(T*0.7))^2)/15000)*exp(-((Y-640)^2)/900000))',"
            f"eq=contrast=1.12:brightness=-0.02"
        )
    else:
        # warm horizon glow rising
        fc = (
            f"color=c=0x0a0a14:s=720x1280:d={duration:.3f}:r=24,"
            f"geq="
            f"r='min(255,8+90*exp(-((Y-(1000-T*25))^2)/70000))':"
            f"g='min(255,6+45*exp(-((Y-(1000-T*25))^2)/80000))':"
            f"b='min(255,12+20*exp(-((Y-(1000-T*25))^2)/100000))',"
            f"eq=contrast=1.08:saturation=1.15"
        )
    vf = "".join(fc)
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", vf,
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(path),
    ])


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/free_cinematic")
    out.mkdir(parents=True, exist_ok=True)

    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])
    audio = out / "narration.mp3"
    asyncio.run(tts(SCRIPT, audio))
    adur = media_duration(audio)
    print(f"[ok] audio {adur:.2f}s", flush=True)

    n = 4
    seg_dur = adur / n
    segs = []
    for i in range(n):
        seg = out / f"seg_{i:02d}.mp4"
        print(f"[scene] {i+1}/{n}", flush=True)
        make_scene(seg, seg_dur, i)
        segs.append(seg)

    concat_list = out / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    raw = out / "video_raw.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "copy", "-an", str(raw),
    ])

    sentences = [s.strip() for s in re.split(r"[\.؟!]+", SCRIPT) if s.strip()]
    ass = out / "captions.ass"
    write_ass(ass, sentences, adur)

    final = out / "final_short.mp4"
    run([
        "ffmpeg", "-y", "-i", str(raw), "-i", str(audio),
        "-vf", f"ass={ass.as_posix()}",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(final),
    ])
    print(f"[SUCCESS] {final} bytes={final.stat().st_size} ~{adur:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
