#!/usr/bin/env python3
"""ImamAli viral short — beautiful large captions, hook-first, free CPU.

Retention-first structure:
  HOOK (0–3s) → pain → steps → soft CTA
Visual:
  per-phrase AI still + Ken Burns + warm grade
Captions:
  large, high-contrast, readable Persian — never tiny
"""
from __future__ import annotations

import asyncio
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Hook first — stop the scroll. Then value. Then soft close.
PHRASES = [
    "اگه شب‌ها به‌خاطر پول نمی‌خوابی…",
    "این سه قدم برای توست.",
    "اول: فقط امروز را ببین، نه کل ماه.",
    "دوم: یک کار کوچکِ قابل‌کنترل انجام بده.",
    "سوم: بقیه را با آرامش بسپار.",
    "تو قوی‌تری از این نگرانی.",
]

VISUALS = [
    "cinematic vertical close-up worried person at night beside window warm single lamp deep blue shadows emotional photorealistic film grain no text",
    "cinematic vertical golden light breaking through dark clouds hope atmosphere photorealistic vertical 9:16 no text",
    "cinematic vertical calendar page and morning coffee soft sunlight calm planning mood photorealistic no text",
    "cinematic vertical hands writing one small task in notebook warm desk lamp focused calm photorealistic no text",
    "cinematic vertical open palms under soft golden beam in dark room peaceful surrender photorealistic no text",
    "cinematic vertical silhouette walking toward warm sunrise on open path hopeful spiritual photorealistic no text",
]

VOICE = "fa-IR-FaridNeural"


def run(cmd: list[str], timeout: int = 180) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-1400:])


def media_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


async def tts(text: str, out: Path) -> None:
    import edge_tts
    # Slightly slower + lower pitch = calmer, more natural motivational tone
    await edge_tts.Communicate(text, VOICE, rate="-12%", pitch="-3Hz").save(str(out))


def fetch_image(prompt: str, dest: Path, width: int = 768, height: int = 1344) -> bool:
    q = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{q}?width={width}&height={height}&nologo=true&model=flux"
    for attempt in range(4):
        try:
            print(f"[img] {dest.name} try {attempt + 1}", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as resp, dest.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if dest.stat().st_size > 20_000:
                return True
        except Exception as e:
            print(f"[img] {type(e).__name__}", flush=True)
            time.sleep(12 + attempt * 10)
        dest.unlink(missing_ok=True)
    return False


def ken_burns(image: Path, duration: float, out: Path, seed: int) -> None:
    frames = max(30, int(duration * 30))
    if seed % 2 == 0:
        z = "min(1.18,1+0.00028*on)"
    else:
        z = "if(eq(on,1),1.14,max(1.0,1.14-0.00028*on))"
    vf = (
        f"scale=900:1600:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30,"
        f"eq=contrast=1.1:brightness=-0.015:saturation=1.15,"
        f"colorbalance=rs=0.08:gs=0.03:bs=-0.05:rm=0.05:bm=-0.04,"
        f"vignette=PI/6,"
        f"unsharp=5:5:0.6:5:5:0.0"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-t", f"{duration:.3f}",
        "-vf", "".join(vf),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
        str(out),
    ], timeout=150)


def write_beautiful_ass(path: Path, phrases: list[str], duration: float) -> None:
    """Large, high-contrast Persian captions — readable on mobile."""

    def ts(t: float) -> str:
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    n = max(len(phrases), 1)
    # PlayRes 1080x1920 — font 72–78 reads large on phone
    # Alignment 2 = bottom-center; big margin so text sits in lower third
    # Primary white, thick black outline, soft shadow — never tiny grey text
    header = """[Script Info]
Title: ImamAli beautiful captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Arial,82,&H00FFFFFF,&H000000FF,&H00000000,&HCC000000,-1,0,0,0,100,100,0,0,1,7,3,2,50,50,280,1
Style: Body,Arial,74,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,6,3,2,50,50,260,1
Style: Soft,Arial,70,&H00E8F0FF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,5,2,2,50,50,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines: list[str] = []
    for i, phrase in enumerate(phrases):
        start = duration * i / n
        end = duration * (i + 1) / n
        # tiny pad so cuts feel clean
        start = max(0.0, start)
        end = min(duration, end)
        text = phrase.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        # Fade in/out + slight scale pop on whole phrase (not per letter)
        if i == 0:
            style = "Hook"
            anim = r"{\fad(120,100)\t(0,180,\fscx108\fscy108)\t(180,320,\fscx100\fscy100)}"
        elif i == n - 1:
            style = "Soft"
            anim = r"{\fad(100,150)}"
        else:
            style = "Body"
            anim = r"{\fad(90,80)\t(0,140,\fscx104\fscy104)\t(140,260,\fscx100\fscy100)}"
        lines.append(
            f"Dialogue: 0,{ts(start)},{ts(end)},{style},,0,0,0,,{anim}{text}"
        )
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/imamali_style")
    out.mkdir(parents=True, exist_ok=True)
    imgs = out / "images"
    imgs.mkdir(exist_ok=True)

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])

    phrases = list(PHRASES)
    visuals = (VISUALS * ((len(phrases) // len(VISUALS)) + 1))[: len(phrases)]

    spoken = " ".join(phrases)
    audio = out / "narration.mp3"
    asyncio.run(tts(spoken, audio))
    adur = media_duration(audio)
    print(f"[ok] audio {adur:.2f}s | phrases={len(phrases)}", flush=True)

    # Weight hook a bit longer for retention
    weights = [1.35] + [1.0] * (len(phrases) - 2) + [1.1]
    total_w = sum(weights)
    durations = [adur * (w / total_w) for w in weights]

    segs: list[Path] = []
    for i, (phrase, prompt, seg_dur) in enumerate(zip(phrases, visuals, durations)):
        img = imgs / f"p_{i:02d}.jpg"
        if not img.is_file() or img.stat().st_size < 20_000:
            if not fetch_image(prompt, img):
                # warm dark fallback so pipeline never dies
                run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", "color=c=0x14101f:s=1080x1920:d=1",
                    "-frames:v", "1", str(img.with_suffix(".png")),
                ])
                img = img.with_suffix(".png")
            time.sleep(3)

        seg = out / f"seg_{i:02d}.mp4"
        ken_burns(img, seg_dur, seg, seed=i)
        segs.append(seg)
        print(f"[ok] {i + 1}/{len(phrases)}: {phrase[:48]}", flush=True)

    concat = out / "concat.txt"
    concat.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    raw = out / "video_raw.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:v", "copy", "-an", str(raw)])

    ass = out / "captions.ass"
    write_beautiful_ass(ass, phrases, adur)

    final = out / "final_short.mp4"
    # Slight overall polish
    vf = f"ass={ass.as_posix()},eq=contrast=1.03:saturation=1.05"
    run([
        "ffmpeg", "-y", "-i", str(raw), "-i", str(audio),
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(final),
    ])
    print(f"[SUCCESS] {final} bytes={final.stat().st_size} ~{adur:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
