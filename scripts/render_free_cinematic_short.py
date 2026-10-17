#!/usr/bin/env python3
"""Free cinematic short engine — no GPU, no paid API.

Stack (100% free):
  - Mixkit free stock (CDN, no key)
  - Edge-TTS Persian male
  - FFmpeg 9:16 + ASS captions + color grade

When Colab GPU is available, LTX path remains optional upgrade.
"""
from __future__ import annotations

import asyncio
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

# Curated Mixkit free cinematic clips (spiritual / light / cathedral / nature)
# Official Mixkit free license — commercial OK, no attribution required.
MIXKIT_CLIPS = [
    "https://assets.mixkit.co/videos/preview/mixkit-rays-of-light-through-trees-in-the-forest-4518-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-white-sand-beach-and-palm-trees-1564-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-stars-in-space-background-1610-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-fire-sparks-from-a-campfire-at-night-39764-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-waves-coming-to-the-beach-5016-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-clouds-and-blue-sky-2408-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-sunset-over-the-sea-1621-large.mp4",
    "https://assets.mixkit.co/videos/preview/mixkit-young-woman-looking-at-the-sky-42950-large.mp4",
]

SCRIPT = (
    "وقتی همه درها بسته به نظر می‌رسند، "
    "یک نور هنوز راه را نشان می‌دهد. "
    "از نو شروع کن. "
    "تو قوی‌تری از چیزی که فکر می‌کنی."
)
VOICE = "fa-IR-FaridNeural"


def run(cmd: list[str], timeout: int = 300) -> None:
    print("[cmd]", " ".join(cmd[:8]), "...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise RuntimeError(f"command failed: {cmd[0]}")


def download(url: str, dest: Path) -> bool:
    try:
        print("[dl]", url.split("/")[-1], flush=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, dest.open("wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        return dest.stat().st_size > 30_000
    except Exception as e:
        print("[dl fail]", e, flush=True)
        dest.unlink(missing_ok=True)
        return False


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


async def tts(text: str, out: Path) -> None:
    import edge_tts
    c = edge_tts.Communicate(text, VOICE, rate="-10%", pitch="-2Hz")
    await c.save(str(out))


def write_ass(path: Path, sentences: list[str], duration: float) -> None:
    def ts(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h:d}:{m:02d}:{s:05.2f}"

    n = max(len(sentences), 1)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,5,2,2,40,40,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for i, sent in enumerate(sentences):
        start = duration * i / n
        end = duration * (i + 1) / n
        t = sent.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{t}")
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/free_cinematic")
    out.mkdir(parents=True, exist_ok=True)
    clips_dir = out / "clips"
    clips_dir.mkdir(exist_ok=True)

    # 1) Download free Mixkit clips
    local_clips: list[Path] = []
    for i, url in enumerate(MIXKIT_CLIPS):
        dest = clips_dir / f"mix_{i:02d}.mp4"
        if dest.is_file() and dest.stat().st_size > 30_000:
            local_clips.append(dest)
            continue
        if download(url, dest):
            local_clips.append(dest)
    if len(local_clips) < 2:
        print("ERROR: not enough free clips downloaded")
        return 1
    print(f"[ok] {len(local_clips)} clips", flush=True)

    # 2) TTS
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])
    audio = out / "narration.mp3"
    asyncio.run(tts(SCRIPT, audio))
    adur = media_duration(audio)
    print(f"[ok] audio {adur:.2f}s", flush=True)

    # 3) Build vertical segments timed to audio (equal share)
    n = min(4, len(local_clips))
    seg_dur = adur / n
    segs: list[Path] = []
    for i in range(n):
        src = local_clips[i % len(local_clips)]
        seg = out / f"seg_{i:02d}.mp4"
        # Cinematic grade + vertical crop + slight zoom feel via scale
        vf = (
            f"scale=720:1280:force_original_aspect_ratio=increase,"
            f"crop=720:1280,"
            f"eq=brightness=-0.03:contrast=1.08:saturation=1.05,"
            f"fps=24"
        )
        run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
            "-t", f"{seg_dur:.3f}",
            "-vf", vf,
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            str(seg),
        ])
        segs.append(seg)

    # 4) Concat
    concat_list = out / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    raw = out / "video_raw.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-an",
        str(raw),
    ])

    # 5) Captions
    sentences = [s.strip() for s in re.split(r"[\.؟!]+", SCRIPT) if s.strip()]
    ass = out / "captions.ass"
    write_ass(ass, sentences, adur)

    # 6) Mux audio + burn ASS
    final = out / "final_short.mp4"
    vf = f"ass={ass.as_posix()}"
    run([
        "ffmpeg", "-y", "-i", str(raw), "-i", str(audio),
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(final),
    ])

    size = final.stat().st_size
    print(f"[SUCCESS] {final} bytes={size} duration≈{adur:.1f}s", flush=True)
    if size < 200_000:
        print("WARNING: file small — check quality")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
