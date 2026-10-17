#!/usr/bin/env python3
"""High-retention spiritual 2D story short (CPU).

Quality bar for watchability:
  - Short spoken lines (easy to pronounce, easy to follow)
  - Per-line TTS with slower rate + audio loudnorm
  - Unique image locked to the action of THAT line
  - Camera always moves
  - Soft crossfade between scenes
  - Large Vazirmatn captions timed to the same line
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

# Short lines = clearer speech + tighter image match
BEATS = [
    {
        "line": "تو کوهستان، پسری فکر می‌کرد خدا خیلی دور است.",
        "prompt": (
            "2D children's storybook, MUST SHOW one young boy standing alone in alpine village foreground, "
            "wooden houses behind him, green mountains, he looks far away thoughtful, soft warm daylight, "
            "flat 2D colors clean outlines vertical"
        ),
    },
    {
        "line": "هر شب به آسمان پر ستاره نگاه می‌کرد.",
        "prompt": (
            "2D children's storybook, MUST SHOW young boy lying on grass looking UP at huge starry sky, "
            "face tilted to stars, mountain silhouette night, wonder expression, flat 2D vertical"
        ),
    },
    {
        "line": "می‌گفت کاش می‌تونستم به خدا برسم.",
        "prompt": (
            "2D children's storybook, MUST SHOW close-up boy face looking at stars with longing hope, "
            "starry night bokeh soft light on face, flat 2D vertical"
        ),
    },
    {
        "line": "یه روز طوفان اومد و یه بره از گله گم شد.",
        "prompt": (
            "2D children's storybook, MUST SHOW small lost white lamb alone near rocks in soft rain storm, "
            "sheep flock far away, windy pasture not scary, flat 2D vertical"
        ),
    },
    {
        "line": "پسر رفت زیر باران دنبال بره.",
        "prompt": (
            "2D children's storybook, MUST SHOW same boy walking mid-stride on wet mountain path in rain, "
            "searching determined kind face wet hair, flat 2D vertical"
        ),
    },
    {
        "line": "بره رو پیدا کرد و محکم بغلش کرد.",
        "prompt": (
            "2D children's storybook, MUST SHOW boy kneeling hugging small white lamb behind a rock, "
            "relief warm golden light through clouds, flat 2D vertical"
        ),
    },
    {
        "line": "اون لحظه فهمید خدا تو مهربونی کنارشه.",
        "prompt": (
            "2D children's storybook, MUST SHOW boy and lamb together under soft rainbow light on green slope, "
            "peaceful hopeful mood warm gold green, flat 2D vertical"
        ),
    },
    {
        "line": "نزدیک‌ترین راه به آسمان، یه قدم مهربونیه.",
        "prompt": (
            "2D children's storybook, MUST SHOW boy walking home with lamb toward alpine village at warm sunset, "
            "orange pink sky hopeful path, flat 2D vertical"
        ),
    },
]

STYLE_LOCK = (
    ". Same boy every scene: short brown hair, simple earth-tone tunic, about 10 years old. "
    "Pure 2D storybook illustration, soft rounded shapes, gentle alpine colors like classic children's book. "
    "NOT photorealistic, NOT 3D, NOT dark, no text, no watermark"
)

VOICE = "fa-IR-FaridNeural"
ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "assets" / "fonts"
MIN_IMG_BYTES = 35_000
CROSSFADE = 0.35  # seconds soft cut between scenes


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


def normalize_persian(text: str) -> str:
    """Light TTS-friendly normalization."""
    text = text.replace("می‌", "می ").replace("ها", "ها")
    # keep meaning; spacing helps some neural voices
    return " ".join(text.split())


async def tts_line(text: str, out: Path) -> None:
    import edge_tts
    spoken = normalize_persian(text)
    # slower + slightly lower = clearer, less robotic rush
    await edge_tts.Communicate(
        spoken, VOICE, rate="-18%", pitch="-4Hz", volume="+20%"
    ).save(str(out))


def loudnorm_audio(src: Path, dst: Path) -> None:
    """Broadcast-ish loudness so phone speakers are clear."""
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,highpass=f=80,lowpass=f=12000",
        "-ar", "48000", "-ac", "1", str(dst),
    ], timeout=60)


def fetch_image(prompt: str, dest: Path, seed: int) -> bool:
    full = prompt + STYLE_LOCK
    q = urllib.parse.quote(full)
    for attempt in range(6):
        seed_try = 3100 + seed * 23 + attempt * 7
        url = (
            f"https://image.pollinations.ai/prompt/{q}"
            f"?width=864&height=1536&nologo=true&seed={seed_try}&model=flux"
        )
        try:
            print(f"[img] scene {seed + 1} try {attempt + 1}", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=100) as resp, dest.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if dest.stat().st_size >= MIN_IMG_BYTES:
                print(f"[img] ok {dest.stat().st_size} bytes", flush=True)
                return True
            print("[img] reject tiny", flush=True)
        except Exception as e:
            print(f"[img] {type(e).__name__}", flush=True)
            time.sleep(16 + attempt * 8)
        dest.unlink(missing_ok=True)
        time.sleep(5)
    return False


def camera_move(image: Path, duration: float, out: Path, seed: int) -> None:
    frames = max(36, int(duration * 24))
    motions = [
        "min(1.15,1+0.00028*on)",
        "if(eq(on,1),1.13,max(1.0,1.13-0.00028*on))",
        "min(1.11,1+0.00018*on)",
        "if(eq(on,1),1.11,max(1.0,1.11-0.00018*on))",
    ]
    z = motions[seed % len(motions)]
    y = (
        "ih/2-(ih/zoom/2)+0.06*sin(on/40)*ih"
        if seed % 2 == 0
        else "ih/2-(ih/zoom/2)-0.05*sin(on/36)*ih"
    )
    vf = (
        f"scale=960:1700:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='{y}':d={frames}:s=720x1280:fps=24,"
        f"eq=contrast=1.06:saturation=1.14:brightness=0.015"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-t", f"{duration:.3f}",
        "-vf", "".join(vf),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
        str(out),
    ], timeout=120)


def write_ass(path: Path, segments: list[tuple[float, float, str]]) -> None:
    def ts(t: float) -> str:
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    # Larger, high-contrast captions for mobile
    header = """[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Body,Vazirmatn,56,&H00FFFFFF,&H000000FF,&H00000000,&HCC000000,0,0,0,0,100,100,0,0,1,6,3,2,22,22,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start, end, line in segments:
        text = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        events.append(
            f"Dialogue: 0,{ts(start)},{ts(end)},Body,,0,0,0,,{{\fad(90,80)}}{text}"
        )
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def concat_with_xfade(segs: list[Path], out: Path) -> None:
    """Soft crossfade so cuts feel less harsh."""
    if len(segs) == 1:
        run(["ffmpeg", "-y", "-i", str(segs[0]), "-c", "copy", str(out)])
        return
    # Build xfade chain
    durs = [media_duration(s) for s in segs]
    args: list[str] = ["ffmpeg", "-y"]
    for s in segs:
        args += ["-i", str(s)]
    n = len(segs)
    # video xfade + acrossfade for audio
    vfilters = []
    afilters = []
    # progressive labels
    offset = 0.0
    for i in range(n - 1):
        offset += durs[i] - CROSSFADE
        if i == 0:
            vfilters.append(
                f"[0:v][1:v]xfade=transition=fade:duration={CROSSFADE}:offset={offset:.3f}[v1]"
            )
            afilters.append(
                f"[0:a][1:a]acrossfade=d={CROSSFADE}[a1]"
            )
        else:
            vfilters.append(
                f"[v{i}][{i+1}:v]xfade=transition=fade:duration={CROSSFADE}:offset={offset:.3f}[v{i+1}]"
            )
            afilters.append(
                f"[a{i}][{i+1}:a]acrossfade=d={CROSSFADE}[a{i+1}]"
            )
    last = n - 1
    fc = ";".join(vfilters + afilters)
    args += [
        "-filter_complex", fc,
        "-map", f"[v{last}]", "-map", f"[a{last}]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(out),
    ]
    try:
        run(args, timeout=240)
    except Exception as e:
        print(f"[warn] xfade failed ({e}); plain concat", flush=True)
        clist = out.parent / "concat_plain.txt"
        clist.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
        run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(clist),
            "-c:v", "libx264", "-preset", "fast", "-crf", "14",
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", str(out),
        ])


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/story_cartoon")
    out.mkdir(parents=True, exist_ok=True)
    imgs = out / "images"
    imgs.mkdir(exist_ok=True)
    audio_dir = out / "audio_lines"
    audio_dir.mkdir(exist_ok=True)

    force = "--force-images" in sys.argv
    font_file = ensure_vazirmatn()
    fonts_dir = font_file.parent.resolve()

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])

    line_audios: list[Path] = []
    for i, beat in enumerate(BEATS):
        raw = audio_dir / f"line_{i:02d}_raw.mp3"
        ap = audio_dir / f"line_{i:02d}.mp3"
        if not ap.is_file() or ap.stat().st_size < 1000:
            asyncio.run(tts_line(beat["line"], raw))
            loudnorm_audio(raw, ap)
        line_audios.append(ap)
        print(f"[tts] {i + 1}: {beat['line']}", flush=True)

    segs: list[Path] = []
    caption_segments: list[tuple[float, float, str]] = []
    t_cursor = 0.0

    for i, (beat, ap) in enumerate(zip(BEATS, line_audios)):
        dur = max(1.4, media_duration(ap))
        # tiny breath after each line so image can land
        vis_dur = dur + 0.25
        img = imgs / f"scene_{i:02d}.jpg"

        need = force or (not img.is_file()) or img.stat().st_size < MIN_IMG_BYTES
        if need:
            ok = fetch_image(beat["prompt"], img, seed=i)
            if not ok:
                print(f"[warn] scene {i + 1} image failed", flush=True)
                colors = ["87CEEB", "1e3a5f", "4a5568", "3d5a6c", "c4a574", "5a8a9a", "6bb3c0", "e8a87c"]
                run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"color=c=0x{colors[i % len(colors)]}:s=720x1280:d=1",
                    "-frames:v", "1", str(img),
                ])
            time.sleep(9)

        video_only = out / f"seg_{i:02d}_v.mp4"
        camera_move(img, vis_dur, video_only, seed=i)

        # pad audio with short silence at end for breathing room
        padded = audio_dir / f"line_{i:02d}_pad.mp3"
        run([
            "ffmpeg", "-y", "-i", str(ap),
            "-af", f"apad=pad_dur=0.25", "-t", f"{vis_dur:.3f}",
            str(padded),
        ])

        seg = out / f"seg_{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-i", str(video_only), "-i", str(padded),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(seg),
        ])
        segs.append(seg)
        caption_segments.append((t_cursor, t_cursor + vis_dur, beat["line"]))
        t_cursor += vis_dur
        print(f"[ok] scene {i + 1}/{len(BEATS)} ({vis_dur:.1f}s)", flush=True)

    assembled = out / "assembled.mp4"
    concat_with_xfade(segs, assembled)

    # Recompute caption times roughly on final duration if xfade shortened
    final_dur = media_duration(assembled)
    if final_dur > 1 and abs(final_dur - t_cursor) > 1.0:
        scale = final_dur / t_cursor
        caption_segments = [
            (a * scale, b * scale, line) for a, b, line in caption_segments
        ]

    ass = out / "captions.ass"
    write_ass(ass, caption_segments)

    final = out / "final_story.mp4"
    vf = f"ass={ass.resolve().as_posix()}:fontsdir={fonts_dir.as_posix()}"
    run([
        "ffmpeg", "-y", "-i", str(assembled),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "13", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(final),
    ])
    print(f"[SUCCESS] {final} bytes={final.stat().st_size} ~{media_duration(final):.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
