#!/usr/bin/env python3
"""Hybrid story short:
  - Nature lines → Mixkit living video (real motion)
  - Character action lines → AI 2D with STRICT subject lock
  - TTS: light diacritics only (heavy diacritics can break Farid)
  - Audio always muxed + loudnorm
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

def mk(vid: int) -> str:
    return f"https://assets.mixkit.co/videos/{vid}/{vid}-720.mp4"

# mode: mixkit | ai
# line: spoken + caption (light diacritics — only where needed)
BEATS = [
    {
        "line": "تو کوهستان، پسری فکر می‌کرد خدا خیلی دور است.",
        "mode": "ai",
        "prompt": (
            "2D children's book illustration, ONE young Persian boy age 10 short brown hair "
            "standing alone in alpine village foreground looking into distance, wooden houses, "
            "green mountains, soft daylight, flat colors clean outlines vertical 9:16, "
            "NO second person, NO text, NOT photo, NOT 3D"
        ),
        "mixkit": [mk(43764), mk(4064)],
    },
    {
        "line": "هر شب به آسمان پر ستاره نگاه می‌کرد.",
        "mode": "ai",
        "prompt": (
            "2D children's book, SAME boy lying on grass looking UP at huge starry night sky, "
            "face tilted to stars, wonder expression, mountain silhouette, vertical 9:16, "
            "NO second person, NO text, NOT photo"
        ),
        "mixkit": [mk(1610), mk(4333)],
    },
    {
        "line": "می‌گفت کاش می‌تونستم به خدا برسم.",
        "mode": "mixkit",
        "prompt": "starry night sky",  # unused if mixkit ok
        "mixkit": [mk(1609), mk(1610)],
    },
    {
        "line": "یه روز طوفان اومد و یه بره از گله گم شد.",
        "mode": "mixkit",
        "prompt": "lost lamb",
        "mixkit": [mk(42200), mk(42199), mk(4257)],
    },
    {
        "line": "پسر رفت زیر باران دنبال بره.",
        "mode": "ai",
        "prompt": (
            "2D children's book, SAME young boy walking alone mid-stride on wet mountain path "
            "in rain, determined face, wet hair, searching, vertical 9:16, "
            "NO second person, NO hugging, NO text, NOT photo"
        ),
        "mixkit": [mk(17409), mk(17408)],
    },
    {
        "line": "بره را پیدا کرد و محکم بغلش کرد.",
        "mode": "ai",
        "prompt": (
            "2D children's book CRITICAL: young boy kneeling hugging a small white LAMB sheep, "
            "lamb wool clearly visible in his arms, warm relief on boy face, golden light, "
            "vertical 9:16. FORBIDDEN: hugging another child, two boys, human baby, no lamb"
        ),
        "mixkit": [mk(42198), mk(4258)],
    },
    {
        "line": "اون لحظه فهمید خدا در مهربانی کنار اوست.",
        "mode": "mixkit",
        "prompt": "sunlight meadow",
        "mixkit": [mk(4344), mk(43763)],
    },
    {
        "line": "نزدیک‌ترین راه به آسمان، یک قدم مهربانی است.",
        "mode": "mixkit",
        "prompt": "sunset path",
        "mixkit": [mk(43766), mk(4345), mk(4065)],
    },
]

VOICE = "fa-IR-FaridNeural"
ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "assets" / "fonts"
MIN_IMG = 40_000


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


async def tts_line(text: str, out: Path) -> None:
    import edge_tts
    # Clear Persian, moderate pace, strong volume
    await edge_tts.Communicate(
        text, VOICE, rate="-15%", pitch="-2Hz", volume="+50%"
    ).save(str(out))


def loudnorm(src: Path, dst: Path) -> None:
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-af", "loudnorm=I=-12:TP=-1.0:LRA=8,highpass=f=80,lowpass=f=12000",
        "-ar", "48000", "-ac", "1", str(dst),
    ], timeout=60)


def download_mixkit(urls: list[str], dest: Path) -> bool:
    if dest.is_file() and dest.stat().st_size > 200_000:
        return True
    for url in urls:
        try:
            print(f"[mixkit] {url}", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if dest.stat().st_size > 200_000:
                return True
        except Exception as e:
            print(f"[mixkit] {type(e).__name__}", flush=True)
            dest.unlink(missing_ok=True)
    return False


def living_clip(src: Path, duration: float, out: Path) -> None:
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
        "-t", f"{duration:.3f}",
        "-vf",
        "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
        "eq=contrast=1.05:saturation=1.1",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
        str(out),
    ], timeout=120)


def fetch_ai_image(prompt: str, dest: Path, seed: int) -> bool:
    q = urllib.parse.quote(prompt)
    for attempt in range(5):
        s = 6000 + seed * 31 + attempt * 13
        url = (
            f"https://image.pollinations.ai/prompt/{q}"
            f"?width=768&height=1344&nologo=true&seed={s}&model=flux"
        )
        try:
            print(f"[ai] scene {seed+1} try {attempt+1}", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=100) as resp, dest.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if dest.stat().st_size >= MIN_IMG:
                return True
        except Exception as e:
            print(f"[ai] {type(e).__name__}", flush=True)
            time.sleep(12 + attempt * 6)
        dest.unlink(missing_ok=True)
        time.sleep(3)
    return False


def ken_burns(image: Path, duration: float, out: Path, seed: int) -> None:
    frames = max(40, int(duration * 24))
    z = "min(1.18,1+0.00035*on)" if seed % 2 == 0 else "if(eq(on,1),1.16,max(1.0,1.16-0.00035*on))"
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-t", f"{duration:.3f}",
        "-vf",
        f"scale=960:1700:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
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
        text = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        a, b = start + 0.05, max(start + 0.5, end - 0.05)
        events.append(f"Dialogue: 0,{ts(a)},{ts(b)},Body,,0,0,0,,{{\fad(70,70)}}{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/story_cartoon")
    out.mkdir(parents=True, exist_ok=True)
    clips = out / "clips"
    clips.mkdir(exist_ok=True)
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
        asyncio.run(tts_line(beat["line"], raw))
        loudnorm(raw, ap)
        # verify audio not empty
        if ap.stat().st_size < 2000:
            raise RuntimeError(f"TTS empty for line {i}")
        line_audios.append(ap)
        print(f"[tts] {i+1} ok {ap.stat().st_size}b: {beat['line']}", flush=True)

    segs: list[Path] = []
    caption_segments: list[tuple[float, float, str]] = []
    t_cursor = 0.0

    for i, (beat, ap) in enumerate(zip(BEATS, line_audios)):
        dur = max(1.6, media_duration(ap))
        vis_dur = dur + 0.3
        video_only = out / f"seg_{i:02d}_v.mp4"

        if beat["mode"] == "mixkit":
            raw = clips / f"mix_{i:02d}.mp4"
            if not download_mixkit(beat["mixkit"], raw):
                # fallback AI
                img = imgs / f"scene_{i:02d}.jpg"
                fetch_ai_image(beat.get("prompt", "nature landscape"), img, i)
                ken_burns(img, vis_dur, video_only, i)
            else:
                living_clip(raw, vis_dur, video_only)
                print(f"[scene {i+1}] Mixkit living", flush=True)
        else:
            img = imgs / f"scene_{i:02d}.jpg"
            ok = fetch_ai_image(beat["prompt"], img, i)
            if not ok:
                # last resort mixkit
                raw = clips / f"mix_{i:02d}.mp4"
                if download_mixkit(beat["mixkit"], raw):
                    living_clip(raw, vis_dur, video_only)
                else:
                    raise RuntimeError(f"No visual for scene {i+1}")
            else:
                ken_burns(img, vis_dur, video_only, i)
                print(f"[scene {i+1}] AI character", flush=True)
            time.sleep(6)

        padded = audio_dir / f"line_{i:02d}_pad.mp3"
        run([
            "ffmpeg", "-y", "-i", str(ap),
            "-af", "apad=pad_dur=0.3", "-t", f"{vis_dur:.3f}", str(padded),
        ])

        # FORCE audio map — never silent video
        seg = out / f"seg_{i:02d}.mp4"
        run([
            "ffmpeg", "-y",
            "-i", str(video_only),
            "-i", str(padded),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(seg),
        ])
        # verify segment has audio
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(seg)],
            capture_output=True, text=True,
        )
        if "audio" not in (r.stdout or ""):
            raise RuntimeError(f"Segment {i} missing audio stream")

        segs.append(seg)
        caption_segments.append((t_cursor, t_cursor + vis_dur, beat["line"]))
        t_cursor += vis_dur

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
        "-c:a", "copy",
        "-movflags", "+faststart", str(final),
    ])

    # final audio check
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(final)],
        capture_output=True, text=True,
    )
    print(f"[SUCCESS] {final} bytes={final.stat().st_size} audio={r.stdout.strip()} ~{media_duration(final):.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
