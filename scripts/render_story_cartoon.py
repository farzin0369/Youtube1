#!/usr/bin/env python3
"""Pure AI spiritual story — natural-paced Persian TTS + high-quality scene images.

Audio: Edge-TTS Farid with natural pauses, moderate rate, loudnorm (no robotic rush).
Visual: Pollinations flux, strict per-line prompts, living Ken Burns, big captions.
No Mixkit.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Spoken text: short clauses + commas so Farid breathes naturally
BEATS = [
    {
        "line": "تو کوهستان، پسری فکر می‌کرد خدا خیلی دور است.",
        "prompt": (
            "award winning 2D children's storybook illustration, ONE young Persian boy age 10, "
            "short brown hair, simple earth-tone tunic, standing alone in alpine village, "
            "looking into distance with thoughtful eyes, wooden houses, lush green mountains, "
            "soft golden daylight, rich colors, clean outlines, vertical 9:16 composition, "
            "NO second person, NO text, NO watermark, NOT photo, NOT 3D render"
        ),
    },
    {
        "line": "هر شب، به آسمان پر ستاره نگاه می‌کرد.",
        "prompt": (
            "award winning 2D children's storybook, SAME boy lying on soft grass looking UP, "
            "huge starry night sky full of bright stars, wonder on his face, mountain silhouette, "
            "deep blue and gold night palette, vertical 9:16, NO second person, NO text, NOT photo"
        ),
    },
    {
        "line": "می‌گفت: کاش می‌تونستم به خدا برسم.",
        "prompt": (
            "award winning 2D children's storybook close-up, SAME boy's hopeful face lit by starlight, "
            "eyes looking upward with longing, soft emotional lighting, vertical 9:16, "
            "NO second person, NO text, NOT photo"
        ),
    },
    {
        "line": "یه روز طوفان اومد، و یه بره از گله گم شد.",
        "prompt": (
            "award winning 2D children's storybook, ONE small fluffy white lamb alone near wet rocks, "
            "soft rain and wind, flock far in background, not scary, cool blue-gray tones, "
            "vertical 9:16, NO boy in frame, NO hugging, NO text, NOT photo"
        ),
    },
    {
        "line": "پسر رفت زیر باران، دنبال بره.",
        "prompt": (
            "award winning 2D children's storybook, SAME boy walking alone mid-stride on wet mountain path, "
            "rain falling, determined kind face, wet hair, searching pose, vertical 9:16, "
            "NO second person, NO hugging, NO text, NOT photo"
        ),
    },
    {
        "line": "بره را پیدا کرد، و محکم بغلش کرد.",
        "prompt": (
            "award winning 2D children's storybook CRITICAL: young boy kneeling, arms around a small white LAMB, "
            "lamb wool clearly visible, warm relief on boy's face, golden soft light, emotional moment, "
            "vertical 9:16. FORBIDDEN: hugging another child, two boys, human baby, missing lamb"
        ),
    },
    {
        "line": "اون لحظه فهمید، خدا در مهربانی کنار اوست.",
        "prompt": (
            "award winning 2D children's storybook, SAME boy sitting with white lamb under soft rainbow light, "
            "green mountain slope, peaceful hopeful mood, warm colors, vertical 9:16, NO text, NOT photo"
        ),
    },
    {
        "line": "نزدیک‌ترین راه به آسمان، یک قدم مهربانی است.",
        "prompt": (
            "award winning 2D children's storybook, SAME boy walking home carrying the lamb toward alpine village, "
            "warm sunset orange and pink sky, hopeful ending, vertical 9:16, NO text, NOT photo"
        ),
    },
]

STYLE = (
    " Consistent character: same 10-year-old boy, short brown hair, earth-tone tunic, every scene. "
    "Pure 2D storybook, soft rounded shapes, premium children's book quality, high detail."
)

VOICE = "fa-IR-FaridNeural"
ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "assets" / "fonts"
MIN_IMG = 45_000


def run(cmd: list[str], timeout: int = 200) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-1600:])


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


async def tts_natural(text: str, out: Path) -> None:
    """Natural pacing: slower rate, slight lower pitch, not rushed."""
    import edge_tts
    # -12% rate + soft pitch = less robotic than extreme settings
    await edge_tts.Communicate(
        text,
        VOICE,
        rate="-12%",
        pitch="-2Hz",
        volume="+40%",
    ).save(str(out))


def process_audio(src: Path, dst: Path) -> None:
    """Human-like loudness + light warmth (highpass/lowpass), no harshness."""
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-af",
        "highpass=f=70,lowpass=f=10500,"
        "acompressor=threshold=-18dB:ratio=2.5:attack=20:release=200,"
        "loudnorm=I=-14:TP=-1.5:LRA=9",
        "-ar", "48000", "-ac", "1", str(dst),
    ], timeout=60)


def fetch_image(prompt: str, dest: Path, seed: int) -> bool:
    full = prompt + STYLE
    q = urllib.parse.quote(full)
    for attempt in range(7):
        s = 9000 + seed * 43 + attempt * 23
        url = (
            f"https://image.pollinations.ai/prompt/{q}"
            f"?width=768&height=1344&nologo=true&seed={s}&model=flux&enhance=true"
        )
        try:
            print(f"[ai] scene {seed+1} try {attempt+1}", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if dest.stat().st_size >= MIN_IMG:
                print(f"[ai] ok {dest.stat().st_size}", flush=True)
                return True
            print("[ai] reject tiny", flush=True)
        except Exception as e:
            print(f"[ai] {type(e).__name__}", flush=True)
            time.sleep(16 + attempt * 8)
        dest.unlink(missing_ok=True)
        time.sleep(5)
    return False


def ken_burns(image: Path, duration: float, out: Path, seed: int) -> None:
    frames = max(48, int(duration * 24))
    patterns = [
        "min(1.22,1+0.00042*on)",
        "if(eq(on,1),1.2,max(1.0,1.2-0.00042*on))",
        "min(1.16,1+0.00032*on)",
        "if(eq(on,1),1.15,max(1.0,1.15-0.00032*on))",
    ]
    z = patterns[seed % len(patterns)]
    y = (
        "ih/2-(ih/zoom/2)+0.07*sin(on/40)*ih"
        if seed % 2 == 0
        else "ih/2-(ih/zoom/2)-0.06*sin(on/34)*ih"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-t", f"{duration:.3f}",
        "-vf",
        f"scale=1000:1780:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='{y}':d={frames}:s=720x1280:fps=24,"
        f"eq=contrast=1.07:saturation=1.14:brightness=0.01",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "12", "-pix_fmt", "yuv420p",
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
Style: Body,Vazirmatn,56,&H00FFFFFF,&H000000FF,&H00000000,&HCC000000,0,0,0,0,100,100,0,0,1,6,3,2,24,24,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start, end, line in segments:
        text = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        a, b = start + 0.06, max(start + 0.55, end - 0.06)
        events.append(f"Dialogue: 0,{ts(a)},{ts(b)},Body,,0,0,0,,{{\fad(80,80)}}{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/story_cartoon")
    out.mkdir(parents=True, exist_ok=True)
    imgs = out / "images"
    imgs.mkdir(exist_ok=True)
    audio_dir = out / "audio_lines"
    audio_dir.mkdir(exist_ok=True)
    fonts_dir = ensure_vazirmatn().parent.resolve()

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])

    line_audios: list[Path] = []
    for i, beat in enumerate(BEATS):
        raw = audio_dir / f"line_{i:02d}_raw.mp3"
        ap = audio_dir / f"line_{i:02d}.mp3"
        asyncio.run(tts_natural(beat["line"], raw))
        process_audio(raw, ap)
        if ap.stat().st_size < 2000:
            raise RuntimeError(f"TTS empty line {i}")
        line_audios.append(ap)
        print(f"[tts-natural] {i+1}: {beat['line']}", flush=True)

    segs: list[Path] = []
    caption_segments: list[tuple[float, float, str]] = []
    t_cursor = 0.0

    for i, (beat, ap) in enumerate(zip(BEATS, line_audios)):
        dur = max(1.8, media_duration(ap))
        # short breath gap after each line
        vis_dur = dur + 0.35
        img = imgs / f"scene_{i:02d}.jpg"
        video_only = out / f"seg_{i:02d}_v.mp4"

        if not fetch_image(beat["prompt"], img, seed=i):
            raise RuntimeError(f"Image failed scene {i+1}")
        ken_burns(img, vis_dur, video_only, seed=i)
        time.sleep(8)

        padded = audio_dir / f"line_{i:02d}_pad.mp3"
        run([
            "ffmpeg", "-y", "-i", str(ap),
            "-af", "apad=pad_dur=0.35", "-t", f"{vis_dur:.3f}", str(padded),
        ])

        seg = out / f"seg_{i:02d}.mp4"
        run([
            "ffmpeg", "-y",
            "-i", str(video_only), "-i", str(padded),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", str(seg),
        ])
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(seg)],
            capture_output=True, text=True,
        )
        if "audio" not in (r.stdout or ""):
            raise RuntimeError(f"No audio on segment {i}")

        segs.append(seg)
        caption_segments.append((t_cursor, t_cursor + vis_dur, beat["line"]))
        t_cursor += vis_dur
        print(f"[ok] scene {i+1}/{len(BEATS)} ({vis_dur:.1f}s)", flush=True)

    clist = out / "concat.txt"
    clist.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    assembled = out / "assembled.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(clist),
        "-c:v", "libx264", "-preset", "fast", "-crf", "13",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", str(assembled),
    ])

    ass = out / "captions.ass"
    write_ass(ass, caption_segments)
    final = out / "final_story.mp4"
    vf = f"ass={ass.resolve().as_posix()}:fontsdir={fonts_dir.as_posix()}"
    run([
        "ffmpeg", "-y", "-i", str(assembled),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "12", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart", str(final),
    ])
    print(
        f"[SUCCESS] pure-AI natural-TTS {final} "
        f"bytes={final.stat().st_size} ~{media_duration(final):.1f}s",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
