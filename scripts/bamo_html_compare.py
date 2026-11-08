#!/usr/bin/env python3
"""HTML/HyperFrames compare — Persian aurora with carefully written TTS text."""
from __future__ import annotations

import asyncio
import html as html_lib
import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "daily"

TITLE = "شَفَقِ قُطبی چیست؟"

# نگارش دقیق + اعراب برای تلفظ درست Edge-TTS
# برند به صورت قابل‌تلفظ فارسی نوشته شده (نه at twelve bamo)
SENTENCES = [
    "شَفَقِ قُطبی چیست؟",
    "خورشید پلاسما را به بیرون می‌فِرِستَد.",
    "میدانِ مَغناطیسیِ زمین، ذرّات را به سَمتِ قُطب‌ها هِدایَت می‌کُنَد.",
    "گازهایِ جَو بَرانگیخته می‌شَوَند و آسمان روشن می‌شَوَد.",
    "رَنگ به اِرتِفاع و شیمی بَستگی دارد.",
    "بامو. دُنبال کُنید: آتِ دَوازده بامو.",
]

MIXKIT_IDS = [34788, 14185, 31559]
UA = "Mozilla/5.0 (compatible; BAMOShorts/1.0)"


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 900) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True, timeout=timeout)


def _probe(path: Path) -> float:
    try:
        return float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    str(path),
                ],
                text=True,
            ).strip()
        )
    except Exception:
        return 2.0


def _download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp, dest.open("wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        ok = dest.exists() and dest.stat().st_size > 100_000
        if not ok:
            dest.unlink(missing_ok=True)
        return ok
    except Exception as exc:
        print(f"dl fail: {exc}", flush=True)
        dest.unlink(missing_ok=True)
        return False


async def _tts_sentence(text: str, dest: Path) -> float:
    import edge_tts

    # FaridNeural: best available free Persian neural voice
    await edge_tts.Communicate(text, "fa-IR-FaridNeural").save(str(dest))
    return max(0.8, _probe(dest))


def _build_synced_audio(work: Path) -> tuple[Path, list[tuple[float, float, str]], float]:
    parts_dir = work / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    timeline: list[tuple[float, float, str]] = []
    files: list[Path] = []
    t = 0.0

    async def gen() -> None:
        nonlocal t
        for i, s in enumerate(SENTENCES):
            p = parts_dir / f"p{i:02d}.mp3"
            dur = await _tts_sentence(s, p)
            files.append(p)
            # Caption shows clean text without excessive harakat clutter on screen
            caption = (
                s.replace("َ", "")
                .replace("ِ", "")
                .replace("ُ", "")
                .replace("ً", "")
                .replace("ٌ", "")
                .replace("ٍ", "")
                .replace("ّ", "ّ")  # keep tashdid lightly
            )
            # simpler caption cleanup: keep readable form
            caption_map = [
                "شفق قطبی چیست؟",
                "خورشید پلاسما را به بیرون می‌فرستد.",
                "میدان مغناطیسی زمین، ذرات را به سمت قطب‌ها هدایت می‌کند.",
                "گازهای جو برانگیخته می‌شوند و آسمان روشن می‌شود.",
                "رنگ به ارتفاع و شیمی بستگی دارد.",
                "بامو · @12bamo",
            ]
            cap = caption_map[i] if i < len(caption_map) else s
            timeline.append((t, t + dur, cap))
            t += dur + 0.08

    asyncio.run(gen())

    silence = parts_dir / "sil.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=24000:cl=mono",
            "-t",
            "0.08",
            "-q:a",
            "9",
            "-acodec",
            "libmp3lame",
            str(silence),
        ],
        check=True,
        capture_output=True,
    )
    lst = parts_dir / "list.txt"
    lines = []
    for i, f in enumerate(files):
        lines.append(f"file '{f.resolve()}'")
        if i < len(files) - 1:
            lines.append(f"file '{silence.resolve()}'")
    lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    full = work / "assets" / "narration.mp3"
    full.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(full)],
        check=True,
        capture_output=True,
    )
    duration = min(28.0, _probe(full) + 0.3)
    return full, timeline, duration


def _build_vertical_film(work: Path, duration: float) -> Path:
    clips_dir = work / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    for mid in MIXKIT_IDS:
        url = f"https://assets.mixkit.co/videos/{mid}/{mid}-720.mp4"
        p = clips_dir / f"mix_{mid}.mp4"
        if _download(url, p):
            clips.append(p)
            print(f"video ok {p.name}", flush=True)
        if len(clips) >= 2:
            break
    if not clips:
        raise RuntimeError("no stock video")

    tmp = work / "_film"
    tmp.mkdir(exist_ok=True)
    segs = []
    per = max(5.0, duration / len(clips))
    for i, c in enumerate(clips):
        seg = tmp / f"s{i}.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(c),
                "-t",
                f"{per:.2f}",
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                str(seg),
            ],
            check=True,
            capture_output=True,
        )
        segs.append(seg)

    if len(segs) == 1:
        raw = segs[0]
    else:
        raw = tmp / "xf.mp4"
        d0, d1 = _probe(segs[0]), _probe(segs[1])
        fade = 0.5
        off = max(0.1, d0 - fade)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(segs[0]),
                "-i",
                str(segs[1]),
                "-filter_complex",
                f"[0:v][1:v]xfade=transition=fade:duration={fade}:offset={off:.2f}[v]",
                "-map",
                "[v]",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                str(raw),
            ],
            check=True,
            capture_output=True,
        )

    out = work / "assets" / "film.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(raw),
            "-t",
            f"{duration:.2f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    return out


def _write_html(work: Path, timeline: list[tuple[float, float, str]], duration: float) -> None:
    beat_divs = []
    gsap = []
    for i, (start, end, text) in enumerate(timeline):
        bid = f"beat-{i}"
        slot = max(0.6, end - start)
        beat_divs.append(
            f'      <div id="{bid}" class="beat" data-start="{start:.2f}" '
            f'data-duration="{slot:.2f}" data-track-index="{10 + i}">{html_lib.escape(text)}</div>'
        )
        gsap.append(
            f'      tl.fromTo("#{bid}", {{opacity: 0, y: 18}}, '
            f'{{opacity: 1, y: 0, duration: 0.25, ease: "power2.out"}}, {start:.2f});'
        )
        out_at = max(start + 0.4, end - 0.12)
        gsap.append(f'      tl.to("#{bid}", {{opacity: 0, duration: 0.18}}, {out_at:.2f});')

    ds = f"{duration:.2f}"
    index = f"""<!doctype html>
<html lang="fa" dir="rtl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>{html_lib.escape(TITLE)}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@700;900&display=block" rel="stylesheet" />
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      html, body {{
        width: 1080px; height: 1920px; overflow: hidden; background: #000;
        font-family: "Vazirmatn", Tahoma, sans-serif; color: #fff; direction: rtl;
      }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; }}
      #film {{
        position: absolute; inset: 0; width: 100%; height: 100%;
        object-fit: cover; z-index: 0;
      }}
      .scrim {{
        position: absolute; inset: 0; z-index: 2; pointer-events: none;
        background: linear-gradient(180deg,
          rgba(0,0,0,0.25) 0%, rgba(0,0,0,0.1) 40%,
          rgba(0,0,0,0.5) 70%, rgba(0,0,0,0.78) 100%);
      }}
      .beat {{
        position: absolute; left: 40px; right: 40px; bottom: 280px;
        text-align: center; font-weight: 900; font-size: 46px; line-height: 1.4;
        opacity: 0; z-index: 5;
        text-shadow: 0 3px 16px rgba(0,0,0,0.95), 0 0 4px #000;
      }}
      #brand {{
        position: absolute; left: 0; right: 0; bottom: 100px; text-align: center;
        font-weight: 700; font-size: 26px; opacity: 0; z-index: 6;
        color: rgba(255,255,255,0.9); text-shadow: 0 2px 10px #000;
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{ds}" data-width="1080" data-height="1920">
      <video id="film" class="clip" src="assets/film.mp4" data-start="0" data-duration="{ds}"
        data-track-index="0" muted playsinline
        style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;"></video>
      <div class="scrim clip" data-start="0" data-duration="{ds}" data-track-index="1"></div>
{chr(10).join(beat_divs)}
      <div id="brand" class="clip" data-start="0" data-duration="{ds}" data-track-index="30">بامو · @12bamo</div>
      <audio id="vo" class="clip" src="assets/narration.mp3" data-start="0" data-duration="{ds}"
        data-track-index="40" data-volume="1"></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(gsap)}
      tl.fromTo("#brand", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, {max(0.2, duration - 1.6):.2f});
      tl.to({{}}, {{ duration: {ds} }}, 0);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (work / "index.html").write_text(index, encoding="utf-8")


def main() -> int:
    work = Path("/tmp/bamo-html-compare")
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    _audio, timeline, duration = _build_synced_audio(work)
    print(json.dumps({"duration": duration, "spoken": SENTENCES, "captions": [t[2] for t in timeline]}, ensure_ascii=False), flush=True)

    _build_vertical_film(work, duration)
    _write_html(work, timeline, duration)

    out = OUT_DIR / f"BAMO_HTML_TTSFIX_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        _run(["npx", "--yes", "hyperframes@0.9.19", "render", "--gpu", "-o", str(out)], cwd=work, timeout=900)
    except Exception:
        _run(["npx", "--yes", "hyperframes@0.9.19", "render", "-o", str(out)], cwd=work, timeout=900)

    if not out.exists() or out.stat().st_size < 50_000:
        raise SystemExit("HTML render failed")
    print(json.dumps({"ok": True, "path": str(out), "engine": "html_hyperframes", "size": out.stat().st_size}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
