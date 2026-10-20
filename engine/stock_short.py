#!/usr/bin/env python3
"""Stock-footage YouTube Shorts engine (MoneyPrinter-style, no AI faces).

Pipeline: Persian script → Edge-TTS → Pexels clips → FFmpeg 9:16 + captions
No GPU. Looks like real faceless YouTube content.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any
from urllib.parse import quote

DEFAULT_STORY = {
    "id": "sapling_stock",
    "voice": "fa-IR-FaridNeural",
    "rate": "-8%",
    "beats": [
        {
            "line": "روزی مردی به کودکی گفت: این نهال کی سایه می‌ده؟",
            "query": "seedling plant soil hands watering garden sunrise",
        },
        {
            "line": "کودک به نهال نگاه کرد و چیزی نگفت.",
            "query": "child looking at small plant outdoor nature",
        },
        {
            "line": "پیرمرد خم شد و با مهربانی پرسید.",
            "query": "elderly man garden teaching child outdoor",
        },
        {
            "line": "کودک گفت: من هم زیر سایه‌ی درختی نشستم که کسی پیش از من کاشته بود.",
            "query": "large oak tree shade sunlight peaceful park",
        },
        {
            "line": "خوبی کن؛ شاید روزی سایه‌اش به غریبه‌ای برسد.",
            "query": "people planting tree community hope golden hour",
        },
    ],
}


def run(cmd: list[str], timeout: int = 300) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-2000:])


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


def ensure_deps() -> None:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q", "--upgrade",
        "edge-tts", "requests", "nest_asyncio",
    ])


def run_async(coro):
    import nest_asyncio
    nest_asyncio.apply()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def tts(text: str, out: Path, voice: str, rate: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate, volume="+25%").save(str(out))


def pexels_video(query: str, out: Path, api_key: str) -> bool:
    import requests

    headers = {"Authorization": api_key}
    url = f"https://api.pexels.com/videos/search?query={quote(query)}&per_page=15&orientation=portrait"
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            # fallback landscape
            url = f"https://api.pexels.com/videos/search?query={quote(query)}&per_page=15"
            r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        videos = r.json().get("videos") or []
        if not videos:
            return False
        random.shuffle(videos)
        for v in videos:
            files = sorted(
                v.get("video_files") or [],
                key=lambda f: (f.get("height") or 0),
                reverse=True,
            )
            for f in files:
                link = f.get("link")
                h = f.get("height") or 0
                if not link or h < 480:
                    continue
                vr = requests.get(link, timeout=120, stream=True)
                if vr.status_code != 200:
                    continue
                with open(out, "wb") as fh:
                    for chunk in vr.iter_content(256_000):
                        fh.write(chunk)
                if out.stat().st_size > 80_000:
                    print(f"[pexels] {query[:40]} → {out.name} ({out.stat().st_size//1024}KB)", flush=True)
                    return True
                out.unlink(missing_ok=True)
        return False
    except Exception as e:
        print(f"[pexels] fail {query}: {e}", flush=True)
        return False


def solid_fallback(out: Path, seconds: float = 4.0) -> None:
    """Last-resort solid color clip if Pexels fails."""
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x1a1a2e:s=1080x1920:d={seconds:.2f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
    ], timeout=60)


def make_vertical_clip(src: Path, dst: Path, duration: float) -> None:
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
        "-t", f"{duration:.3f}",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "eq=contrast=1.05:saturation=1.08",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(dst),
    ], timeout=180)


def render(story: dict[str, Any], out_path: Path, work: Path, pexels_key: str) -> dict[str, Any]:
    ensure_deps()
    work.mkdir(parents=True, exist_ok=True)
    audio_dir = work / "audio"
    clip_dir = work / "clips"
    audio_dir.mkdir(exist_ok=True)
    clip_dir.mkdir(exist_ok=True)

    beats = story["beats"]
    voice = story.get("voice", "fa-IR-FaridNeural")
    rate = story.get("rate", "-8%")

    segs: list[Path] = []
    captions: list[tuple[float, float, str]] = []
    t0 = 0.0

    for i, beat in enumerate(beats):
        print(f"[beat] {i+1}/{len(beats)}", flush=True)
        # TTS
        raw = audio_dir / f"a{i:02d}_raw.mp3"
        ap = audio_dir / f"a{i:02d}.mp3"
        run_async(tts(beat["line"], raw, voice, rate))
        run([
            "ffmpeg", "-y", "-i", str(raw),
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "1", str(ap),
        ], timeout=60)
        dur = max(2.5, media_duration(ap))
        vis = dur + 0.25

        # Stock video
        stock = clip_dir / f"stock_{i:02d}.mp4"
        ok = False
        if pexels_key:
            ok = pexels_video(beat.get("query", "nature tree"), stock, pexels_key)
        if not ok:
            print(f"[stock] fallback solid scene {i+1}", flush=True)
            solid_fallback(stock, vis)

        vclip = clip_dir / f"v{i:02d}.mp4"
        make_vertical_clip(stock, vclip, vis)

        # mux
        padded = audio_dir / f"a{i:02d}_pad.mp3"
        run(["ffmpeg", "-y", "-i", str(ap), "-af", f"apad=pad_dur=0.25", "-t", f"{vis:.3f}", str(padded)])
        seg = clip_dir / f"s{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-i", str(vclip), "-i", str(padded),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-pix_fmt", "yuv420p", str(seg),
        ])
        segs.append(seg)
        captions.append((t0, t0 + vis, beat["line"]))
        t0 += vis

    clist = work / "concat.txt"
    clist.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    assembled = work / "assembled.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(clist),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", str(assembled),
    ])

    def ts(t: float) -> str:
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    ass = work / "captions.ass"
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Body,Arial,64,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,1,0,0,0,100,100,0,0,3,4,0,2,48,48,220,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for a, b, line in captions:
        t = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        ev.append(f"Dialogue: 0,{ts(a+0.05)},{ts(max(a+0.5,b-0.05))},Body,,0,0,0,,{t}")
    ass.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-i", str(assembled),
        "-vf", f"ass={ass.as_posix()}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart", str(out_path),
    ])

    meta = {
        "ok": True,
        "bytes": out_path.stat().st_size,
        "sec": media_duration(out_path),
        "beats": len(beats),
        "engine": "stock_short_v1",
    }
    # aliases for old workflows
    for name in ("final_story.mp4", "video_raw.mp4"):
        alt = out_path.parent / name
        if alt.resolve() != out_path.resolve():
            subprocess.check_call(["cp", str(out_path), str(alt)])
    print(json.dumps(meta), flush=True)
    return meta


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--story", default=None)
    p.add_argument("--out", default="/content/final_story.mp4")
    p.add_argument("--work", default="/content/stock_work")
    args, _ = p.parse_known_args(argv)

    story = DEFAULT_STORY
    if args.story and Path(args.story).is_file():
        story = json.loads(Path(args.story).read_text(encoding="utf-8"))

    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        print("[warn] PEXELS_API_KEY missing — solid-color fallback", flush=True)

    render(story, Path(args.out), Path(args.work), key)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
