#!/usr/bin/env python3
"""Spiritual short — working Mixkit living video + diacritic TTS + scene lock.

Mixkit CDN pattern (verified 2026):
  https://assets.mixkit.co/videos/{id}/{id}-720.mp4
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import urllib.request
from pathlib import Path

def mk(vid: int) -> str:
    return f"https://assets.mixkit.co/videos/{vid}/{vid}-720.mp4"

BEATS = [
    {
        "line": "تو کُوهِستان، پِسَری فِکر می‌کَرد خُدا خِیلی دور اَست.",
        "mixkit": [mk(43764), mk(4064), mk(43763)],  # mountains / landscape
    },
    {
        "line": "هَر شَب بِه آسِمانِ پُر سِتاره نِگاه می‌کَرد.",
        "mixkit": [mk(1610), mk(4333), mk(1609)],  # stars / night sky
    },
    {
        "line": "می‌گُفت: کاش می‌تَوانِستَم بِه خُدا بِرَسَم.",
        "mixkit": [mk(1609), mk(1610)],
    },
    {
        "line": "یِه روز طوفان آمَد و یِه بَرِّه اَز گَلِّه گُم شُد.",
        "mixkit": [mk(42200), mk(42199), mk(4257)],  # sheep flock
    },
    {
        "line": "پِسَر رَفت زیرِ باران دُنبالِ بَرِّه.",
        "mixkit": [mk(17409), mk(17408), mk(43767)],  # rain / wet path
    },
    {
        "line": "بَرِّه را پِیدا کَرد و مَحکَم بَغَلَش کَرد.",
        # ONLY sheep/lamb — never AI "two boys hugging"
        "mixkit": [mk(42198), mk(42200), mk(4258)],
    },
    {
        "line": "آن لَحظِه فَهمید خُدا دَر مِهرَبانی کِنارِ اوست.",
        "mixkit": [mk(4344), mk(43763)],  # sunlight meadow
    },
    {
        "line": "نَزدیک‌تَرین راه بِه آسِمان، یِک قَدَمِ مِهرَبانی‌ست.",
        "mixkit": [mk(43766), mk(4345), mk(4065)],  # sunset mountains / path
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


async def tts_line(text: str, out: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(
        text, VOICE, rate="-22%", pitch="-3Hz", volume="+30%"
    ).save(str(out))


def loudnorm(src: Path, dst: Path) -> None:
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=9,highpass=f=90,lowpass=f=11000",
        "-ar", "48000", "-ac", "1", str(dst),
    ], timeout=60)


def download_mixkit(urls: list[str], dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
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
                print(f"[mixkit] ok {dest.stat().st_size}", flush=True)
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
        "eq=contrast=1.05:saturation=1.12",
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
        text = " ".join(line.split()).replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
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
        print(f"[tts] {i + 1}: {beat['line']}", flush=True)

    segs: list[Path] = []
    caption_segments: list[tuple[float, float, str]] = []
    t_cursor = 0.0

    for i, (beat, ap) in enumerate(zip(BEATS, line_audios)):
        dur = max(1.6, media_duration(ap))
        vis_dur = dur + 0.25
        raw_clip = clips / f"raw_{i:02d}.mp4"
        video_only = out / f"seg_{i:02d}_v.mp4"

        ok = download_mixkit(beat["mixkit"], raw_clip)
        if not ok:
            raise RuntimeError(f"All Mixkit URLs failed for scene {i + 1}")
        living_clip(raw_clip, vis_dur, video_only)
        print(f"[scene] {i + 1}: Mixkit living OK", flush=True)

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
