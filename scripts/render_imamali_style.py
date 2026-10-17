#!/usr/bin/env python3
"""ImamAli channel style short — free CPU path.

Style match (like user's published shorts):
  - One cinematic AI still per spoken phrase (Pollinations free)
  - Ken Burns slow zoom/pan
  - Warm spiritual color grade (gold / amber / deep blue)
  - Persian male TTS + large readable captions synced to audio

No Colab GPU required.
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

SCRIPT = (
    "وقتی نگرانی مالی قلبت را می‌فشارد، "
    "نفس عمیق بکش. "
    "آنچه در کنترل توست را انجام بده. "
    "بقیه را به خدا بسپار. "
    "تو تنها نیستی."
)

# Visual direction per phrase (English prompts for image model)
VISUALS = [
    "cinematic vertical portrait, person sitting alone at night by a small window, warm golden candle light, deep blue shadows, emotional peaceful mood, photorealistic, film grain, no text no watermark",
    "cinematic vertical close-up, soft golden light rays through darkness, dust particles floating, calm spiritual atmosphere, photorealistic, shallow depth of field, no text",
    "cinematic vertical shot, open hands receiving warm light from above in a dark room, hopeful mood, golden amber color grade, photorealistic, no text no watermark",
    "cinematic vertical wide shot, silhouette under a vast starry night sky, single beam of golden light, peaceful surrender, filmic color, no text",
    "cinematic vertical shot, two figures walking on a path toward warm sunrise light, hope and companionship, golden hour, photorealistic spiritual mood, no text",
]

VOICE = "fa-IR-FaridNeural"


def run(cmd: list[str], timeout: int = 180) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-1200:])


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


async def tts(text: str, out: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate="-8%", pitch="-2Hz").save(str(out))


def fetch_image(prompt: str, dest: Path, width: int = 720, height: int = 1280) -> bool:
    """Pollinations free image endpoint (may watermark on free tier)."""
    q = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{q}?width={width}&height={height}&nologo=true&model=flux"
    for attempt in range(4):
        try:
            print(f"[img] attempt {attempt+1} {dest.name}", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as resp, dest.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if dest.stat().st_size > 15_000:
                return True
        except Exception as e:
            print(f"[img] fail: {e}", flush=True)
            time.sleep(8 * (attempt + 1))
        dest.unlink(missing_ok=True)
    return False


def ken_burns(image: Path, duration: float, out: Path, seed: int) -> None:
    """Slow zoom on still → vertical cinematic motion."""
    frames = max(24, int(duration * 24))
    # Alternate zoom in / zoom out
    if seed % 2 == 0:
        z = "min(1.15,1+0.00035*on)"
    else:
        z = "if(eq(on,1),1.12,max(1.0,1.12-0.00035*on))"
    vf = (
        f"scale=800:1422:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24,"
        # Warm spiritual grade
        f"eq=contrast=1.08:brightness=-0.02:saturation=1.12,"
        f"colorbalance=rs=0.06:gs=0.02:bs=-0.04:rm=0.04:bm=-0.03,"
        f"vignette=PI/5"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-t", f"{duration:.3f}",
        "-vf", "".join(vf),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(out),
    ], timeout=120)


def write_ass(path: Path, phrases: list[str], duration: float) -> None:
    def ts(t: float) -> str:
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    n = max(len(phrases), 1)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,54,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,5,2,2,36,36,160,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for i, p in enumerate(phrases):
        start, end = duration * i / n, duration * (i + 1) / n
        t = p.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{t}")
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

    phrases = [s.strip() for s in re.split(r"[\.؟!]+", SCRIPT) if s.strip()]
    if not phrases:
        phrases = [SCRIPT]

    # Pad / trim visuals to phrase count
    visuals = (VISUALS * ((len(phrases) // len(VISUALS)) + 1))[: len(phrases)]

    audio = out / "narration.mp3"
    asyncio.run(tts(SCRIPT, audio))
    adur = media_duration(audio)
    print(f"[ok] audio {adur:.2f}s phrases={len(phrases)}", flush=True)

    seg_dur = adur / len(phrases)
    segs: list[Path] = []
    for i, (phrase, prompt) in enumerate(zip(phrases, visuals)):
        img = imgs / f"p_{i:02d}.jpg"
        if not img.is_file() or img.stat().st_size < 15_000:
            ok = fetch_image(prompt, img)
            if not ok:
                # solid warm fallback
                run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"color=c=0x1a1428:s=720x1280:d=1",
                    "-frames:v", "1", str(img),
                ])
            time.sleep(2)  # be kind to free API

        seg = out / f"seg_{i:02d}.mp4"
        ken_burns(img, seg_dur, seg, seed=i)
        segs.append(seg)
        print(f"[ok] scene {i+1}/{len(phrases)}: {phrase[:40]}", flush=True)

    concat = out / "concat.txt"
    concat.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    raw = out / "video_raw.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:v", "copy", "-an", str(raw)])

    ass = out / "captions.ass"
    write_ass(ass, phrases, adur)

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
