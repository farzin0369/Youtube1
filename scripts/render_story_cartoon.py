#!/usr/bin/env python3
"""Spiritual 2D cartoon story — high relevance + camera motion (CPU).

Improvements:
  - Strict scene-action prompts (what is ON SCREEN must match the line)
  - Same-boy character lock across scenes
  - Reject tiny / solid / failed images and retry
  - Stronger 2D storybook look (not photo, not 3d)
  - Per-line TTS + always-moving camera
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

STORY_TITLE = "پسر کوهستان"

# Each prompt starts with the EXACT visual action so the model cannot drift
BEATS = [
    {
        "line": "تو یه دهکده‌ی کوهستانی، پسری زندگی می‌کرد که فکر می‌کرد خدا خیلی دور است.",
        "prompt": (
            "2D children's storybook illustration, MUST SHOW: small alpine village with wooden houses "
            "and ONE young boy standing alone in the foreground looking into the distance, "
            "green mountain meadows, soft warm daylight, simple cute character design, "
            "flat 2D coloring, clean outlines, vertical composition"
        ),
        "must": "village boy standing",
    },
    {
        "line": "هر شب به آسمون پر ستاره نگاه می‌کرد و می‌گفت: کاش می‌تونستم بهش برسم.",
        "prompt": (
            "2D children's storybook illustration, MUST SHOW: young boy lying on grass looking UP "
            "at a huge starry night sky, face tilted toward stars, mountain silhouette, "
            "night blue and soft gold stars, wonder expression, flat 2D coloring, vertical"
        ),
        "must": "boy looking up stars",
    },
    {
        "line": "یه روز طوفان اومد و بره‌ی کوچیکی از گله گم شد.",
        "prompt": (
            "2D children's storybook illustration, MUST SHOW: rainy stormy pasture, flock of sheep, "
            "ONE small lost lamb alone near rocks, wind and soft rain, not scary, "
            "flat 2D coloring, vertical"
        ),
        "must": "lost lamb storm",
    },
    {
        "line": "پسر بدون اینکه کسی ببینه، رفت دنبال بره؛ خیس و سرد، اما نترسید.",
        "prompt": (
            "2D children's storybook illustration, MUST SHOW: same young boy WALKING on a wet mountain "
            "path in the rain, mid-stride, searching, wet hair, determined kind face, "
            "rain drops, flat 2D coloring, vertical"
        ),
        "must": "boy walking rain",
    },
    {
        "line": "پشت یه سنگ، بره رو پیدا کرد و بغلش کرد.",
        "prompt": (
            "2D children's storybook illustration, MUST SHOW: boy kneeling behind a large rock "
            "HUGGING a small white lamb, warm relief on face, golden light through clouds, "
            "flat 2D coloring, vertical"
        ),
        "must": "boy hugging lamb",
    },
    {
        "line": "همون لحظه فهمید: خدا دور نبود؛ تو همون کارِ مهربونش کنارش بود.",
        "prompt": (
            "2D children's storybook illustration, MUST SHOW: boy and lamb sitting together under soft "
            "rainbow light on a green mountain slope, peaceful hopeful mood, warm gold green palette, "
            "flat 2D coloring, vertical"
        ),
        "must": "boy lamb rainbow light",
    },
    {
        "line": "گاهی نزدیک‌ترین راه به آسمان، یه قدم مهربونی روی زمینه.",
        "prompt": (
            "2D children's storybook illustration, MUST SHOW: wide ending shot of boy walking home "
            "toward alpine village at warm sunset with lamb beside him, orange pink sky, "
            "hopeful path, flat 2D coloring, vertical"
        ),
        "must": "sunset village walk",
    },
]

STYLE_LOCK = (
    ". Same boy character every scene: short brown hair, simple tunic, age about 10. "
    "Pure 2D storybook, soft rounded shapes, gentle colors, alpine Heidi countryside mood. "
    "NOT photorealistic, NOT 3D render, NOT anime, NOT dark horror, no text, no watermark, no logo"
)

VOICE = "fa-IR-FaridNeural"
ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "assets" / "fonts"
MIN_IMG_BYTES = 30_000  # reject solid placeholders


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
    for url in [
        "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/ttf/Vazirmatn-Bold.ttf",
        "https://github.com/rastikerdar/vazirmatn/raw/v33.003/fonts/ttf/Vazirmatn-Bold.ttf",
    ]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, bold.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if bold.stat().st_size > 50_000:
                return bold
        except Exception:
            bold.unlink(missing_ok=True)
    raise RuntimeError("Vazirmatn download failed")


async def tts_line(text: str, out: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate="-10%", pitch="-2Hz").save(str(out))


def fetch_image(prompt: str, dest: Path, seed: int) -> bool:
    """Fetch 2D storybook frame; reject tiny/irrelevant solids."""
    full = prompt + STYLE_LOCK
    q = urllib.parse.quote(full)
    # Higher quality request: larger size, fixed seed per scene for retry consistency
    for attempt in range(5):
        seed_try = 2000 + seed * 17 + attempt * 3
        url = (
            f"https://image.pollinations.ai/prompt/{q}"
            f"?width=864&height=1536&nologo=true&seed={seed_try}&model=flux"
        )
        try:
            print(f"[img] scene {seed + 1} try {attempt + 1} seed={seed_try}", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=100) as resp, dest.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            size = dest.stat().st_size
            if size >= MIN_IMG_BYTES:
                print(f"[img] ok scene {seed + 1} bytes={size}", flush=True)
                return True
            print(f"[img] reject tiny {size} bytes", flush=True)
        except Exception as e:
            print(f"[img] {type(e).__name__}", flush=True)
            time.sleep(18 + attempt * 10)
        dest.unlink(missing_ok=True)
        time.sleep(6)
    return False


def camera_move(image: Path, duration: float, out: Path, seed: int) -> None:
    frames = max(30, int(duration * 24))
    motions = [
        "min(1.16,1+0.00032*on)",
        "if(eq(on,1),1.14,max(1.0,1.14-0.00032*on))",
        "min(1.12,1+0.0002*on)",
        "if(eq(on,1),1.12,max(1.0,1.12-0.0002*on))",
    ]
    z = motions[seed % len(motions)]
    y_expr = (
        "ih/2-(ih/zoom/2)+0.07*sin(on/38)*ih"
        if seed % 2 == 0
        else "ih/2-(ih/zoom/2)-0.05*sin(on/32)*ih"
    )
    vf = (
        f"scale=960:1700:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='{y_expr}':d={frames}:s=720x1280:fps=24,"
        f"eq=contrast=1.05:saturation=1.12:brightness=0.01"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-t", f"{duration:.3f}",
        "-vf", "".join(vf),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p",
        str(out),
    ], timeout=120)


def write_ass(path: Path, segments: list[tuple[float, float, str]]) -> None:
    def ts(t: float) -> str:
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    header = """[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Body,Vazirmatn,50,&H00FFFFFF,&H000000FF,&H00000000,&HBB000000,0,0,0,0,100,100,0,0,1,5,2,2,24,24,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start, end, line in segments:
        text = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        events.append(
            f"Dialogue: 0,{ts(start)},{ts(end)},Body,,0,0,0,,{{\fad(80,70)}}{text}"
        )
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/story_cartoon")
    out.mkdir(parents=True, exist_ok=True)
    imgs = out / "images"
    imgs.mkdir(exist_ok=True)
    audio_dir = out / "audio_lines"
    audio_dir.mkdir(exist_ok=True)

    # optional: force re-download weak images
    force = "--force-images" in sys.argv

    font_file = ensure_vazirmatn()
    fonts_dir = font_file.parent.resolve()

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])

    line_audios: list[Path] = []
    for i, beat in enumerate(BEATS):
        ap = audio_dir / f"line_{i:02d}.mp3"
        if not ap.is_file() or ap.stat().st_size < 1000:
            asyncio.run(tts_line(beat["line"], ap))
        line_audios.append(ap)
        print(f"[tts] {i + 1}: {beat['line'][:40]}…", flush=True)

    segs: list[Path] = []
    caption_segments: list[tuple[float, float, str]] = []
    t_cursor = 0.0

    for i, (beat, ap) in enumerate(zip(BEATS, line_audios)):
        dur = max(1.2, media_duration(ap))
        img = imgs / f"scene_{i:02d}.jpg"

        need = force or (not img.is_file()) or img.stat().st_size < MIN_IMG_BYTES
        if need:
            ok = fetch_image(beat["prompt"], img, seed=i)
            if not ok:
                print(f"[warn] scene {i + 1} still missing — soft color fallback", flush=True)
                # soft gradient-like solid (better than pure black)
                colors = ["87CEEB", "2c3e6b", "5a6a7a", "4a708b", "c4a574", "6bb3c0", "e8a87c"]
                run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"color=c=0x{colors[i]}:s=720x1280:d=1",
                    "-frames:v", "1", str(img),
                ])
            time.sleep(10)

        video_only = out / f"seg_{i:02d}_v.mp4"
        camera_move(img, dur, video_only, seed=i)
        seg = out / f"seg_{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-i", str(video_only), "-i", str(ap),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(seg),
        ])
        segs.append(seg)
        caption_segments.append((t_cursor, t_cursor + dur, beat["line"]))
        t_cursor += dur
        print(f"[ok] scene {i + 1}/{len(BEATS)} ({dur:.1f}s) 2D+camera", flush=True)

    concat = out / "concat.txt"
    concat.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    assembled = out / "assembled.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", str(assembled),
    ])

    ass = out / "captions.ass"
    write_ass(ass, caption_segments)

    final = out / "final_story.mp4"
    vf = f"ass={ass.resolve().as_posix()}:fontsdir={fonts_dir.as_posix()}"
    run([
        "ffmpeg", "-y", "-i", str(assembled),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart",
        str(final),
    ])
    print(f"[SUCCESS] {final} bytes={final.stat().st_size} duration≈{t_cursor:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
