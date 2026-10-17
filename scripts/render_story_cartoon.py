#!/usr/bin/env python3
"""Spiritual cartoon story — each narrator line = unique matching scene + camera move.

Critical UX rules:
  - Scene MUST change with spoken content (look at sky → sky-looking frame)
  - Camera always moves (Ken Burns zoom/pan), never a frozen still
  - Per-line TTS so visual duration matches that line
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

# Unique visual per line — prompts are literal matches to the spoken action
BEATS = [
    {
        "line": "تو یه دهکده‌ی کوهستانی، پسری زندگی می‌کرد که فکر می‌کرد خدا خیلی دور است.",
        "prompt": (
            "children storybook cartoon, wide establishing shot of small alpine village in green mountains, "
            "tiny wooden houses, one small boy standing alone in foreground looking distant, "
            "soft daylight, cute simple character design, warm colors, flat shading, vertical 9:16, no text"
        ),
    },
    {
        "line": "هر شب به آسمون پر ستاره نگاه می‌کرد و می‌گفت: کاش می‌تونستم بهش برسم.",
        "prompt": (
            "children storybook cartoon, CLOSE-UP of young boy lying on grass LOOKING UP at huge starry night sky, "
            "his face tilted upward toward stars, mountains silhouette, soft blue and gold, wonder expression, "
            "camera angle from slightly below looking at boy and sky together, vertical 9:16, no text"
        ),
    },
    {
        "line": "یه روز طوفان اومد و بره‌ی کوچیکی از گله گم شد.",
        "prompt": (
            "children storybook cartoon, stormy mountain pasture, wind and rain, flock of sheep, "
            "ONE small lamb separated and lost alone near rocks, dramatic soft clouds, not scary for kids, "
            "vertical 9:16, no text"
        ),
    },
    {
        "line": "پسر بدون اینکه کسی ببینه، رفت دنبال بره؛ خیس و سرد، اما نترسید.",
        "prompt": (
            "children storybook cartoon, boy WALKING through rain on mountain dirt path, searching, "
            "wet hair, determined kind face, side view mid-stride, rainy atmosphere, soft drama, "
            "vertical 9:16, no text"
        ),
    },
    {
        "line": "پشت یه سنگ، بره رو پیدا کرد و بغلش کرد.",
        "prompt": (
            "children storybook cartoon, boy KNEELING behind a large rock HUGGING a small lamb tightly, "
            "relief and warmth on his face, golden light breaking through clouds onto them, "
            "intimate medium shot, vertical 9:16, no text"
        ),
    },
    {
        "line": "همون لحظه فهمید: خدا دور نبود؛ تو همون کارِ مهربونش کنارش بود.",
        "prompt": (
            "children storybook cartoon, boy and lamb sitting together under soft rainbow light on mountain slope, "
            "peaceful hopeful faces looking forward, warm gold and soft green, spiritual calm mood, "
            "vertical 9:16, no text"
        ),
    },
    {
        "line": "گاهی نزدیک‌ترین راه به آسمان، یه قدم مهربونی روی زمینه.",
        "prompt": (
            "children storybook cartoon, wide ending shot boy walking home toward alpine village at warm sunset, "
            "lamb beside him, orange pink sky, hopeful path leading to houses, soft storybook ending frame, "
            "vertical 9:16, no text"
        ),
    },
]

STYLE = (
    ", consistent same boy character in every scene, children's picture book, soft rounded shapes, "
    "gentle colors, alpine countryside, NOT photorealistic, NOT 3d, no watermark"
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


def fetch_unique_image(prompt: str, dest: Path, seed: int) -> bool:
    full = f"{prompt}{STYLE} seed:{seed}"
    q = urllib.parse.quote(full)
    # seed in query helps diversity when API supports it
    url = f"https://image.pollinations.ai/prompt/{q}?width=768&height=1344&nologo=true&seed={1000 + seed}"
    for attempt in range(4):
        try:
            print(f"[img] scene {seed + 1} try {attempt + 1}", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as resp, dest.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if dest.stat().st_size > 25_000:
                return True
        except Exception as e:
            print(f"[img] {type(e).__name__}", flush=True)
            time.sleep(15 + attempt * 12)
        dest.unlink(missing_ok=True)
    return False


def camera_move(image: Path, duration: float, out: Path, seed: int) -> None:
    """Always-moving camera: zoom + slight pan (never static)."""
    frames = max(30, int(duration * 24))
    # Vary motion direction per scene so cuts feel different
    motions = [
        # zoom in center
        "min(1.18,1+0.00035*on)",
        # zoom out
        "if(eq(on,1),1.16,max(1.0,1.16-0.00035*on))",
        # zoom in slower
        "min(1.14,1+0.00022*on)",
        # zoom out slower
        "if(eq(on,1),1.12,max(1.0,1.12-0.00022*on))",
    ]
    z = motions[seed % len(motions)]
    # slight vertical drift for "camera" feel
    y_expr = "ih/2-(ih/zoom/2)+0.08*sin(on/40)*ih" if seed % 2 == 0 else "ih/2-(ih/zoom/2)-0.06*sin(on/35)*ih"
    vf = (
        f"scale=900:1600:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='{y_expr}':d={frames}:s=720x1280:fps=24,"
        f"eq=contrast=1.06:saturation=1.14"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-t", f"{duration:.3f}",
        "-vf", "".join(vf),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
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

    font_file = ensure_vazirmatn()
    fonts_dir = font_file.parent.resolve()

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])

    # Per-line TTS → accurate scene durations
    line_audios: list[Path] = []
    for i, beat in enumerate(BEATS):
        ap = audio_dir / f"line_{i:02d}.mp3"
        if not ap.is_file() or ap.stat().st_size < 1000:
            asyncio.run(tts_line(beat["line"], ap))
        line_audios.append(ap)
        print(f"[tts] {i + 1}: {beat['line'][:36]}…", flush=True)

    segs: list[Path] = []
    caption_segments: list[tuple[float, float, str]] = []
    t_cursor = 0.0

    for i, (beat, ap) in enumerate(zip(BEATS, line_audios)):
        dur = max(1.2, media_duration(ap))
        img = imgs / f"scene_{i:02d}.jpg"

        # Force unique image per beat — never reuse another scene's file
        if not img.is_file() or img.stat().st_size < 25_000:
            ok = fetch_unique_image(beat["prompt"], img, seed=i)
            if not ok:
                print(f"[warn] scene {i + 1} image failed — solid placeholder", flush=True)
                run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"color=c=0x{['87CEEB','1a2744','4a5568','5b7c99','c4a574','7ec8e3','e8a87c'][i]}:s=720x1280:d=1",
                    "-frames:v", "1", str(img),
                ])
            time.sleep(8)  # free API pacing so next scene is different

        seg = out / f"seg_{i:02d}.mp4"
        # video with camera motion
        video_only = out / f"seg_{i:02d}_v.mp4"
        camera_move(img, dur, video_only, seed=i)
        # mux this line's audio onto this segment
        run([
            "ffmpeg", "-y", "-i", str(video_only), "-i", str(ap),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(seg),
        ])
        segs.append(seg)
        caption_segments.append((t_cursor, t_cursor + dur, beat["line"]))
        t_cursor += dur
        print(f"[ok] scene {i + 1}/{len(BEATS)} ({dur:.1f}s) UNIQUE + camera", flush=True)

    concat = out / "concat.txt"
    concat.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    assembled = out / "assembled.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", str(assembled),
    ])

    ass = out / "captions.ass"
    write_ass(ass, caption_segments)

    final = out / "final_story.mp4"
    vf = f"ass={ass.resolve().as_posix()}:fontsdir={fonts_dir.as_posix()}"
    run([
        "ffmpeg", "-y", "-i", str(assembled),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart",
        str(final),
    ])
    print(f"[SUCCESS] {final} bytes={final.stat().st_size} duration≈{t_cursor:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
