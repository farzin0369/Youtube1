#!/usr/bin/env python3
"""Spiritual cartoon story short — free CPU path.

Style: soft children's-book / alpine-storybook illustration
  (warm, simple characters, mountains, golden light — NOT photoreal).

Pipeline:
  fixed story beats → cartoon still per beat → Edge-TTS narrator
  → Ken Burns → large Vazirmatn captions → vertical MP4

Inspired by open story pipelines (Story-Flicks pattern) but zero paid API:
  Pollinations images + edge-tts + ffmpeg only.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ── First story: spiritual, simple, Quranic-adjacent closeness theme ───────
STORY_TITLE = "پسر کوهستان"

# Each beat = one spoken line + one cartoon frame (synced)
BEATS = [
    {
        "line": "تو یه دهکده‌ی کوهستانی، پسری زندگی می‌کرد که فکر می‌کرد خدا خیلی دور است.",
        "prompt": (
            "children storybook cartoon illustration vertical, young boy standing alone on green alpine mountain "
            "meadow, simple cute character design soft colors, distant snow peaks, slightly sad curious expression, "
            "warm daylight, clean flat shading, no text no watermark"
        ),
    },
    {
        "line": "هر شب به آسمون پر ستاره نگاه می‌کرد و می‌گفت: کاش می‌تونستم بهش برسم.",
        "prompt": (
            "children storybook cartoon illustration vertical, same young boy lying on grass looking up at "
            "huge starry night sky over mountains, soft blue and gold palette, wonder on his face, "
            "simple cute character, clean flat shading, no text no watermark"
        ),
    },
    {
        "line": "یه روز طوفان اومد و بره‌ی کوچیکی از گله گم شد.",
        "prompt": (
            "children storybook cartoon illustration vertical, stormy alpine hills, small lost lamb in wind, "
            "dark clouds and rain, emotional but soft not scary, simple cartoon animals, "
            "clean flat shading, no text no watermark"
        ),
    },
    {
        "line": "پسر بدون اینکه کسی ببینه، رفت دنبال بره؛ خیس و سرد، اما نترسید.",
        "prompt": (
            "children storybook cartoon illustration vertical, young boy walking through rain on mountain path "
            "searching, determined kind face, wet hair simple cartoon style, soft dramatic lighting, "
            "clean flat shading, no text no watermark"
        ),
    },
    {
        "line": "پشت یه سنگ، بره رو پیدا کرد و بغلش کرد.",
        "prompt": (
            "children storybook cartoon illustration vertical, young boy kneeling hugging small lamb behind a rock, "
            "relief and warmth, soft golden light breaking through clouds, cute simple characters, "
            "clean flat shading, no text no watermark"
        ),
    },
    {
        "line": "همون لحظه فهمید: خدا دور نبود؛ تو همون کارِ مهربونش کنارش بود.",
        "prompt": (
            "children storybook cartoon illustration vertical, boy and lamb under soft rainbow light on mountain, "
            "peaceful hopeful mood, warm gold and soft green, simple cute storybook style, "
            "clean flat shading, no text no watermark"
        ),
    },
    {
        "line": "گاهی نزدیک‌ترین راه به آسمان، یه قدم مهربونی روی زمینه.",
        "prompt": (
            "children storybook cartoon illustration vertical, wide peaceful alpine village sunset, boy walking home "
            "with lamb, warm orange sky, hopeful ending frame, simple cute style, "
            "clean flat shading, no text no watermark"
        ),
    },
]

STYLE_SUFFIX = (
    ", consistent character design across scenes, children's picture book aesthetic, "
    "soft rounded shapes, gentle colors, alpine heidi-like countryside mood, not photorealistic, not 3d render"
)

VOICE = "fa-IR-FaridNeural"
ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "assets" / "fonts"


def run(cmd: list[str], timeout: int = 180) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-1400:])


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


def ensure_vazirmatn() -> Path:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    bold = FONTS_DIR / "Vazirmatn-Bold.ttf"
    if bold.is_file() and bold.stat().st_size > 50_000:
        return bold
    urls = [
        "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/ttf/Vazirmatn-Bold.ttf",
        "https://github.com/rastikerdar/vazirmatn/raw/v33.003/fonts/ttf/Vazirmatn-Bold.ttf",
    ]
    for url in urls:
        try:
            print("[font] Vazirmatn…", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, bold.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if bold.stat().st_size > 50_000:
                return bold
        except Exception as e:
            print(f"[font] {type(e).__name__}", flush=True)
            bold.unlink(missing_ok=True)
    raise RuntimeError("Vazirmatn download failed")


async def tts(text: str, out: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate="-10%", pitch="-2Hz").save(str(out))


def fetch_image(prompt: str, dest: Path) -> bool:
    full = prompt + STYLE_SUFFIX
    q = urllib.parse.quote(full)
    url = f"https://image.pollinations.ai/prompt/{q}?width=768&height=1344&nologo=true"
    for attempt in range(3):
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
    frames = max(24, int(duration * 24))
    z = "min(1.12,1+0.00025*on)" if seed % 2 == 0 else "if(eq(on,1),1.1,max(1.0,1.1-0.00025*on))"
    vf = (
        f"scale=840:1493:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24,"
        f"eq=contrast=1.06:saturation=1.15"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-t", f"{duration:.3f}",
        "-vf", "".join(vf),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        str(out),
    ], timeout=120)


def write_ass(path: Path, lines: list[str], duration: float) -> None:
    def ts(t: float) -> str:
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    n = max(len(lines), 1)
    header = """[Script Info]
Title: story cartoon captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Vazirmatn,58,&H00FFFFFF,&H000000FF,&H00000000,&HCC000000,0,0,0,0,100,100,0,0,1,5,3,2,26,26,200,1
Style: Body,Vazirmatn,52,&H00FFFFFF,&H000000FF,&H00000000,&HBB000000,0,0,0,0,100,100,0,0,1,5,2,2,26,26,190,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for i, line in enumerate(lines):
        start, end = duration * i / n, duration * (i + 1) / n
        text = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        style = "Hook" if i == 0 else "Body"
        anim = r"{\fad(100,80)}"
        events.append(f"Dialogue: 0,{ts(start)},{ts(end)},{style},,0,0,0,,{anim}{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/story_cartoon")
    out.mkdir(parents=True, exist_ok=True)
    imgs = out / "images"
    imgs.mkdir(exist_ok=True)

    font_file = ensure_vazirmatn()
    fonts_dir = font_file.parent.resolve()

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])

    lines = [b["line"] for b in BEATS]
    spoken = " ".join(lines)
    audio = out / "narration.mp3"
    asyncio.run(tts(spoken, audio))
    adur = media_duration(audio)
    print(f"[ok] {STORY_TITLE} | audio {adur:.2f}s | scenes={len(BEATS)}", flush=True)

    seg_dur = adur / len(BEATS)
    segs: list[Path] = []
    for i, beat in enumerate(BEATS):
        img = imgs / f"scene_{i:02d}.jpg"
        if not img.is_file() or img.stat().st_size < 20_000:
            if not fetch_image(beat["prompt"], img):
                run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"color=c=0x87CEEB:s=720x1280:d=1",
                    "-frames:v", "1", str(img),
                ])
            time.sleep(3)
        seg = out / f"seg_{i:02d}.mp4"
        ken_burns(img, seg_dur, seg, seed=i)
        segs.append(seg)
        print(f"[ok] scene {i + 1}: {beat['line'][:40]}…", flush=True)

    concat = out / "concat.txt"
    concat.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    raw = out / "video_raw.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:v", "copy", "-an", str(raw)])

    ass = out / "captions.ass"
    write_ass(ass, lines, adur)

    final = out / "final_story.mp4"
    vf = f"ass={ass.resolve().as_posix()}:fontsdir={fonts_dir.as_posix()}"
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
