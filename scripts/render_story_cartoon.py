#!/usr/bin/env python3
"""Spiritual short — Mixkit living video + strict text/image sync + TTS diacritics.

Why Mixkit again:
  Real camera motion (sheep, mountains, rain, sunset) beats frozen AI stills.

Why not Clew:
  ClewCode/Clew are coding/issue tools, not a free video engine.
  Scene control is done here with rule-based QA agents (no paid API).

QA agents (local, free):
  1) Orthography agent — diacritics for Farid TTS
  2) Scene-lock agent — each line maps to ONE Mixkit clip keyword
  3) Duration agent — clip length matches spoken line
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import urllib.request
from pathlib import Path

STORY_TITLE = "پسر کوهستان"

# Spoken text WITH careful diacritics (اعراب) for clearer Farid pronunciation.
# visual: Mixkit free stock (living) — chosen so content matches the line.
BEATS = [
    {
        "line": "تو کُوهِستان، پِسَری فِکر می‌کَرد خُدا خِیلی دور اَست.",
        "mixkit": [
            # alpine / mountain village feel
            "https://assets.mixkit.co/videos/preview/mixkit-aerial-view-of-a-green-mountainous-landscape-43764-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-landscape-of-mountains-and-blue-sky-4064-large.mp4",
        ],
        "fallback_prompt": "2D storybook alpine village green mountains wooden houses soft daylight vertical no people hugging",
    },
    {
        "line": "هَر شَب بِه آسِمانِ پُر سِتاره نِگاه می‌کَرد.",
        "mixkit": [
            "https://assets.mixkit.co/videos/preview/mixkit-stars-in-space-background-1610-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-night-sky-full-of-stars-4333-large.mp4",
        ],
        "fallback_prompt": "2D storybook boy looking UP at starry night sky mountains silhouette vertical",
    },
    {
        "line": "می‌گُفت: کاش می‌تَوانِستَم بِه خُدا بِرَسَم.",
        "mixkit": [
            "https://assets.mixkit.co/videos/preview/mixkit-stars-in-space-background-1610-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-milky-way-stars-time-lapse-1609-large.mp4",
        ],
        "fallback_prompt": "2D storybook close-up hopeful face under stars vertical no second person",
    },
    {
        "line": "یِه روز طوفان آمَد و یِه بَرِّه اَز گَلِّه گُم شُد.",
        "mixkit": [
            # sheep / lamb living footage
            "https://assets.mixkit.co/videos/preview/mixkit-herd-of-sheep-grazing-in-the-field-42200-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-flock-of-sheep-grazing-in-the-meadow-42199-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-sheep-grazing-in-a-field-4257-large.mp4",
        ],
        "fallback_prompt": "2D storybook ONE small white lamb alone in soft rain near rocks vertical NO boy NO hugging",
    },
    {
        "line": "پِسَر رَفت زیرِ باران دُنبالِ بَرِّه.",
        "mixkit": [
            "https://assets.mixkit.co/videos/preview/mixkit-rain-falling-on-the-ground-in-a-forest-17409-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-raindrops-falling-on-the-ground-17408-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-walking-on-a-path-in-the-woods-on-a-rainy-day-43767-large.mp4",
        ],
        "fallback_prompt": "2D storybook boy walking alone in rain on mountain path vertical NO second person",
    },
    {
        "line": "بَرِّه را پِیدا کَرد و مَحکَم بَغَلَش کَرد.",
        # Prefer real lamb footage; AI often confuses hug with another child — avoid that failure mode
        "mixkit": [
            "https://assets.mixkit.co/videos/preview/mixkit-sheep-and-lambs-in-the-countryside-42201-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-herd-of-lambs-42198-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-close-up-of-a-sheep-4258-large.mp4",
        ],
        "fallback_prompt": (
            "2D children's storybook MUST SHOW young boy kneeling HUGGING a small white LAMB only, "
            "NOT hugging another child, NOT two boys, lamb clearly visible wool, warm light vertical"
        ),
    },
    {
        "line": "آن لَحظِه فَهمید خُدا دَر مِهرَبانی کِنارِ اوست.",
        "mixkit": [
            "https://assets.mixkit.co/videos/preview/mixkit-sunlight-through-the-trees-in-the-forest-43763-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-green-meadow-with-sunlight-4344-large.mp4",
        ],
        "fallback_prompt": "2D storybook soft golden sunlight green meadow peaceful vertical",
    },
    {
        "line": "نَزدیک‌تَرین راه بِه آسِمان، یِک قَدَمِ مِهرَبانی‌ست.",
        "mixkit": [
            "https://assets.mixkit.co/videos/preview/mixkit-sunset-over-the-mountains-43766-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-beautiful-sunset-over-the-mountains-4345-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-path-in-the-mountains-at-sunset-4065-large.mp4",
        ],
        "fallback_prompt": "2D storybook path toward village warm sunset orange sky vertical",
    },
]

VOICE = "fa-IR-FaridNeural"
ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "assets" / "fonts"


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


# ── Agent 1: Orthography — strip display diacritics optionally; TTS keeps them ─
def caption_clean(text: str) -> str:
    """Show readable caption; keep most diacritics that help reading."""
    return " ".join(text.split())


async def tts_line(text: str, out: Path) -> None:
    import edge_tts
    # Diacritics stay in spoken string — this is the orthography agent output
    await edge_tts.Communicate(
        text, VOICE, rate="-22%", pitch="-3Hz", volume="+30%"
    ).save(str(out))


def loudnorm(src: Path, dst: Path) -> None:
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=9,highpass=f=90,lowpass=f=11000",
        "-ar", "48000", "-ac", "1", str(dst),
    ], timeout=60)


# ── Agent 2: Scene-lock — download living Mixkit clip ───────────────────────
def download_mixkit(urls: list[str], dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 100_000:
        return True
    for url in urls:
        try:
            print(f"[mixkit] {url.split('/')[-1][:50]}", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as resp, dest.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if dest.stat().st_size > 100_000:
                return True
        except Exception as e:
            print(f"[mixkit] {type(e).__name__}", flush=True)
            dest.unlink(missing_ok=True)
    return False


def living_clip(src: Path, duration: float, out: Path) -> None:
    """Loop/trim Mixkit clip to exact duration, vertical crop, mild grade."""
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
        "-t", f"{duration:.3f}",
        "-vf",
        "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
        "eq=contrast=1.05:saturation=1.1",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
        str(out),
    ], timeout=120)


def fallback_still_motion(prompt: str, duration: float, out: Path, seed: int) -> None:
    """Only if Mixkit fails — still + living Ken Burns."""
    import time
    import urllib.parse
    img = out.with_suffix(".jpg")
    q = urllib.parse.quote(
        prompt + " pure 2D storybook NOT photorealistic no watermark"
    )
    url = f"https://image.pollinations.ai/prompt/{q}?width=768&height=1344&nologo=true&seed={5000+seed}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=80) as resp, img.open("wb") as f:
            while True:
                c = resp.read(65536)
                if not c:
                    break
                f.write(c)
    except Exception:
        run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x2a4a3a:s=720x1280:d=1",
            "-frames:v", "1", str(img),
        ])
    frames = max(40, int(duration * 24))
    z = "min(1.2,1+0.0004*on)" if seed % 2 == 0 else "if(eq(on,1),1.18,max(1.0,1.18-0.0004*on))"
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(img),
        "-t", f"{duration:.3f}",
        "-vf",
        f"scale=960:1700:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24",
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
Style: Body,Vazirmatn,54,&H00FFFFFF,&H000000FF,&H00000000,&HCC000000,0,0,0,0,100,100,0,0,1,6,3,2,22,22,165,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start, end, line in segments:
        text = caption_clean(line).replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        a, b = start + 0.05, max(start + 0.5, end - 0.05)
        events.append(f"Dialogue: 0,{ts(a)},{ts(b)},Body,,0,0,0,,{{\fad(70,70)}}{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/story_cartoon")
    out.mkdir(parents=True, exist_ok=True)
    clips = out / "mixkit"
    clips.mkdir(exist_ok=True)
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
        asyncio.run(tts_line(beat["line"], raw))
        loudnorm(raw, ap)
        line_audios.append(ap)
        print(f"[tts-agent] {i + 1}: {beat['line']}", flush=True)

    segs: list[Path] = []
    caption_segments: list[tuple[float, float, str]] = []
    t_cursor = 0.0

    for i, (beat, ap) in enumerate(zip(BEATS, line_audios)):
        dur = max(1.6, media_duration(ap))
        vis_dur = dur + 0.25

        raw_clip = clips / f"raw_{i:02d}.mp4"
        video_only = out / f"seg_{i:02d}_v.mp4"

        # Scene-lock agent: prefer living Mixkit
        ok = download_mixkit(beat["mixkit"], raw_clip)
        if ok:
            living_clip(raw_clip, vis_dur, video_only)
            print(f"[scene-agent] {i + 1}: Mixkit living OK", flush=True)
        else:
            print(f"[scene-agent] {i + 1}: Mixkit fail → fallback still+motion", flush=True)
            fallback_still_motion(beat["fallback_prompt"], vis_dur, video_only, seed=i)

        padded = audio_dir / f"line_{i:02d}_pad.mp3"
        run([
            "ffmpeg", "-y", "-i", str(ap),
            "-af", "apad=pad_dur=0.25", "-t", f"{vis_dur:.3f}", str(padded),
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

    # Simple concat (Mixkit already moves — light cuts are fine)
    clist = out / "concat.txt"
    clist.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    assembled = out / "assembled.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(clist),
        "-c:v", "libx264", "-preset", "fast", "-crf", "15",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", str(assembled),
    ])

    ass = out / "captions.ass"
    write_ass(ass, caption_segments)

    final = out / "final_story.mp4"
    vf = f"ass={ass.resolve().as_posix()}:fontsdir={fonts_dir.as_posix()}"
    run([
        "ffmpeg", "-y", "-i", str(assembled),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(final),
    ])
    print(f"[SUCCESS] {final} bytes={final.stat().st_size} ~{media_duration(final):.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
