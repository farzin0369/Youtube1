#!/usr/bin/env python3
"""TTV sample with PER-SENTENCE visual matching.

Each spoken line gets a stock clip chosen for that line's meaning.
"""
from __future__ import annotations

import argparse
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
sys.path.insert(0, str(ROOT))

from ttv.core.scene_generator import SceneGenerator
from ttv.core.text_analyzer import TextAnalyzer

OUT_DIR = ROOT / "outputs" / "daily"
UA = "Mozilla/5.0 (compatible; BAMO-TTV/1.0)"

# idea-00002 — each line has its OWN relevant Mixkit clip id(s)
IDEA = {
    "id": "idea-00002",
    "title_fa": "هتلی که همیشه جا دارد",
    "spoken": [
        "صبر کن...",
        "یه هتل بی‌نهایت اتاق داره... و همه پره.",
        "ولی بازم جا داره برای مهمون جدید!",
        "چطور؟",
        "هر مهمون از اتاق اِن... می‌ره به اتاق دو برابر اِن.",
        "اتاق‌های فرد... همه‌ش خالی می‌شه.",
        "بی‌نهایت... مثل عدد معمولی رفتار نمی‌کنه.",
        "این... هتل هیلبرتِه.",
        "بامو. یوزرنیم ما: دوازده بامو.",
    ],
    "captions": [
        "صبر کن…",
        "هتل بی‌نهایت… همه پره",
        "ولی بازم جا داره؟!",
        "چطور؟",
        "هر مهمون → اتاق ۲ برابر",
        "اتاق‌های فرد خالی می‌شن",
        "بی‌نهایت ≠ عدد معمولی",
        "هتل هیلبرت",
        "بامو · @12bamo",
    ],
    # MATCHED visuals — hotel door, corridor, stairs, infinity hall
    "visuals_per_line": [
        [32960],           # infinity corridor — hook tension
        [21817, 22223],    # hotel door / hotel stairs — hotel is full
        [21900],           # room service / hotel interior — still has room
        [32960],           # how? infinity corridor
        [21817, 22392],    # door + checkout — move guest to 2n
        [22223, 32960],    # stairs + infinite corridor — odd rooms free
        [32960],           # infinity abstract corridor
        [21817],           # hotel door — Hilbert hotel
        [22223],           # brand on hotel stairs
    ],
    "yt_title": "هتل بی‌نهایت همیشه جا داره؟! 🤯",
    "yt_desc": (
        "صبر کن… یه هتل بی‌نهایت اتاق داره و همه پره.\n"
        "ولی بازم جا داره برای مهمون جدید!\n\n"
        "هتل هیلبرت و مفهوم بی‌نهایت شمارا.\n\n"
        "بامو | @12bamo\n"
        "#shorts #ریاضی #علم #بامو #هیلبرت"
    ),
    "yt_tags": ["shorts", "ریاضی", "علم", "بامو", "هیلبرت", "بی‌نهایت", "BAMO"],
}


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
    if dest.exists() and dest.stat().st_size > 80_000:
        return True
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp, dest.open("wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        ok = dest.exists() and dest.stat().st_size > 80_000
        if not ok:
            dest.unlink(missing_ok=True)
        return ok
    except Exception as exc:
        print(f"dl fail: {exc}", flush=True)
        dest.unlink(missing_ok=True)
        return False


def _fetch_mix(mid: int, dest_dir: Path) -> Path | None:
    dest = dest_dir / f"mix_{mid}.mp4"
    url = f"https://assets.mixkit.co/videos/{mid}/{mid}-720.mp4"
    if _download(url, dest):
        print(f"matched clip ok {dest.name}", flush=True)
        return dest
    return None


async def _tts_male_energy(text: str, dest: Path) -> float:
    import edge_tts

    dest.parent.mkdir(parents=True, exist_ok=True)
    voice = "fa-IR-FaridNeural"
    await edge_tts.Communicate(text, voice, rate="+12%", pitch="+3Hz").save(str(dest))
    if not dest.exists() or dest.stat().st_size < 500:
        await edge_tts.Communicate(text, voice).save(str(dest))
    return max(0.7, _probe(dest))


def _build_audio(work: Path, spoken: list[str], captions: list[str]):
    parts_dir = work / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    timeline: list[tuple[float, float, str]] = []
    t = 0.0

    async def gen() -> None:
        nonlocal t
        for i, s in enumerate(spoken):
            p = parts_dir / f"p{i:02d}.mp3"
            dur = await _tts_male_energy(s, p)
            gap = 0.12 if i <= 2 else 0.08
            files.append(p)
            cap = captions[i] if i < len(captions) else s
            timeline.append((t, t + dur, cap))
            t += dur + gap

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
    duration = min(32.0, _probe(full) + 0.35)
    return full, timeline, duration


def _build_matched_film(
    work: Path,
    timeline: list[tuple[float, float, str]],
    visuals_per_line: list[list[int]],
    duration: float,
) -> Path:
    """One relevant clip segment per spoken line (hard visual sync)."""
    clips_dir = work / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    tmp = work / "_film"
    tmp.mkdir(exist_ok=True)

    # cache downloads
    cache: dict[int, Path] = {}
    for ids in visuals_per_line:
        for mid in ids:
            if mid not in cache:
                p = _fetch_mix(mid, clips_dir)
                if p:
                    cache[mid] = p

    if not cache:
        raise RuntimeError("no matched stock clips downloaded")

    segs: list[Path] = []
    for i, (start, end, _cap) in enumerate(timeline):
        slot = max(1.2, end - start + 0.05)
        ids = visuals_per_line[i] if i < len(visuals_per_line) else list(cache.keys())
        src = None
        for mid in ids:
            if mid in cache:
                src = cache[mid]
                break
        if src is None:
            src = next(iter(cache.values()))

        seg = tmp / f"line_{i:02d}.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(src),
                "-t",
                f"{slot:.2f}",
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,eq=saturation=1.08:contrast=1.04",
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
        print(f"visual line {i}: {src.name} for {slot:.2f}s", flush=True)

    # xfade chain between line segments
    if len(segs) == 1:
        raw = segs[0]
    else:
        inputs = []
        for s in segs:
            inputs.extend(["-i", str(s)])
        durs = [_probe(s) for s in segs]
        fade = 0.25
        parts = []
        prev = "[0:v]"
        acc = durs[0]
        out_l = "[0:v]"
        for i in range(1, len(segs)):
            out_l = f"[x{i}]"
            off = max(0.05, acc - fade)
            parts.append(
                f"{prev}[{i}:v]xfade=transition=fade:duration={fade}:offset={off:.2f}{out_l}"
            )
            prev = out_l
            acc = acc + durs[i] - fade
        raw = tmp / "xf.mp4"
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    *inputs,
                    "-filter_complex",
                    ";".join(parts),
                    "-map",
                    out_l,
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
        except Exception:
            # fallback concat
            lst = tmp / "list.txt"
            lst.write_text("".join(f"file '{p.resolve()}'\n" for p in segs), encoding="utf-8")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(raw)],
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


def _write_html(work: Path, timeline: list[tuple[float, float, str]], duration: float, title: str) -> None:
    beats, gsap = [], []
    for i, (start, end, text) in enumerate(timeline):
        bid = f"beat-{i}"
        slot = max(0.55, end - start)
        size = 56 if i == 0 else (52 if i <= 2 else 46)
        beats.append(
            f'      <div id="{bid}" class="beat" style="font-size:{size}px" '
            f'data-start="{start:.2f}" data-duration="{slot:.2f}" data-track-index="{10 + i}">'
            f"{html_lib.escape(text)}</div>"
        )
        gsap.append(
            f'      tl.fromTo("#{bid}", {{opacity:0,y:28,scale:0.94}}, '
            f'{{opacity:1,y:0,scale:1,duration:0.3,ease:"power3.out"}}, {start:.2f});'
        )
        out_at = max(start + 0.4, end - 0.1)
        gsap.append(f'      tl.to("#{bid}", {{opacity:0,y:-12,duration:0.18}}, {out_at:.2f});')

    brand_at = max(0.4, duration - 2.2)
    ds = f"{duration:.2f}"
    html = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1080, height=1920" />
  <title>{html_lib.escape(title)}</title>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@700;900&display=block" rel="stylesheet" />
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      width: 1080px; height: 1920px; overflow: hidden; background: #000;
      font-family: "Vazirmatn", Tahoma, sans-serif; color: #fff; direction: rtl;
    }}
    #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; }}
    .scrim {{
      position: absolute; inset: 0; z-index: 2; pointer-events: none;
      background: linear-gradient(180deg,
        rgba(0,0,0,0.4) 0%, rgba(0,0,0,0.15) 35%,
        rgba(0,0,0,0.5) 68%, rgba(0,0,0,0.88) 100%);
    }}
    .beat {{
      position: absolute; left: 32px; right: 32px; bottom: 320px;
      text-align: center; font-weight: 900; line-height: 1.4;
      opacity: 0; z-index: 5;
      text-shadow: 0 4px 24px rgba(0,0,0,0.95), 0 0 6px #000;
    }}
    #brand-wrap {{
      position: absolute; left: 40px; right: 40px; bottom: 90px;
      text-align: center; opacity: 0; z-index: 8;
    }}
    #brand-name {{
      font-weight: 900; font-size: 72px; letter-spacing: 2px;
      background: linear-gradient(90deg, #fff 0%, #7dd3fc 50%, #c4b5fd 100%);
      -webkit-background-clip: text; background-clip: text;
      -webkit-text-fill-color: transparent;
      filter: drop-shadow(0 4px 18px rgba(0,0,0,0.9));
      line-height: 1.1;
    }}
    #brand-handle {{
      margin-top: 10px; font-weight: 700; font-size: 34px;
      color: rgba(255,255,255,0.95);
      text-shadow: 0 2px 12px #000;
    }}
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="{ds}" data-width="1080" data-height="1920">
    <video id="film" class="clip" src="assets/film.mp4" data-start="0" data-duration="{ds}"
      data-track-index="0" muted playsinline
      style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;"></video>
    <div class="scrim clip" data-start="0" data-duration="{ds}" data-track-index="1"></div>
{chr(10).join(beats)}
    <div id="brand-wrap" class="clip" data-start="0" data-duration="{ds}" data-track-index="30">
      <div id="brand-name">بامو</div>
      <div id="brand-handle">@12bamo</div>
    </div>
    <audio id="vo" class="clip" src="assets/narration.mp3" data-start="0" data-duration="{ds}"
      data-track-index="40" data-volume="1"></audio>
  </div>
  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join(gsap)}
    tl.fromTo("#brand-wrap",
      {{ opacity: 0, y: 30, scale: 0.9 }},
      {{ opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "power3.out" }},
      {brand_at:.2f});
    tl.to({{}}, {{ duration: {ds} }}, 0);
    window.__timelines["main"] = tl;
  </script>
</body>
</html>
"""
    (work / "index.html").write_text(html, encoding="utf-8")


def _make_thumbnail(video: Path, thumb: Path) -> Path:
    frame = thumb.with_suffix(".frame.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-ss", "2.5", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(frame)],
        check=True,
        capture_output=True,
    )
    t1 = "هتل بی‌نهایت"
    t2 = "همیشه جا داره؟!"
    brand = "بامو  @12bamo"
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "eq=saturation=1.15:contrast=1.08,"
        "drawbox=x=0:y=1400:w=1080:h=520:color=black@0.55:t=fill,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{t1}':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=1480:"
        f"borderw=3:bordercolor=black@0.8,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{t2}':fontcolor=white:fontsize=52:x=(w-text_w)/2:y=1570:"
        f"borderw=3:bordercolor=black@0.8,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{brand}':fontcolor=#7dd3fc:fontsize=40:x=(w-text_w)/2:y=1680:"
        f"borderw=2:bordercolor=black@0.7"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(frame), "-vf", vf, "-frames:v", "1", "-q:v", "3", str(thumb)],
        check=True,
        capture_output=True,
    )
    return thumb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--privacy", default="private", choices=["public", "unlisted", "private"])
    args = ap.parse_args()

    work = Path("/tmp/ttv-sample")
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    idea = IDEA
    joined = "\n".join(idea["spoken"])
    analysis = TextAnalyzer().analyze(joined, title=idea["title_fa"])
    plan = SceneGenerator(aspect="portrait").from_analysis(analysis)
    print(
        json.dumps(
            {
                "idea": idea["id"],
                "title": idea["title_fa"],
                "mode": "per_sentence_matched_visuals",
                "tone": analysis.tone,
                "scenes": len(plan.scenes),
                "publish": bool(args.publish),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    _audio, timeline, duration = _build_audio(work, idea["spoken"], idea["captions"])
    _build_matched_film(work, timeline, idea["visuals_per_line"], duration)
    _write_html(work, timeline, duration, idea["title_fa"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    out = OUT_DIR / f"BAMO_TTV_{stamp}.mp4"
    try:
        subprocess.run(
            ["npx", "--yes", "hyperframes@0.9.19", "render", "--gpu", "-o", str(out)],
            cwd=str(work),
            check=True,
            timeout=900,
        )
    except Exception:
        subprocess.run(
            ["npx", "--yes", "hyperframes@0.9.19", "render", "-o", str(out)],
            cwd=str(work),
            check=True,
            timeout=900,
        )

    if not out.exists() or out.stat().st_size < 50_000:
        raise SystemExit("render failed")

    thumb = OUT_DIR / f"BAMO_TTV_{stamp}_thumb.jpg"
    try:
        _make_thumbnail(out, thumb)
    except Exception as exc:
        print(f"thumb warn: {exc}", flush=True)
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "2", "-i", str(out), "-frames:v", "1", "-q:v", "2", str(thumb)],
            check=False,
            capture_output=True,
        )

    upload_result: dict = {"ok": False, "skipped": True}
    if args.publish:
        from app.youtube_client import upload_video

        upload_result = upload_video(
            video_path=out,
            title=idea["yt_title"][:100],
            description=idea["yt_desc"][:5000],
            tags=idea["yt_tags"],
            privacy=args.privacy,
            thumbnail_path=thumb if thumb.exists() else None,
            category_id="27",
        )
        print(json.dumps({"upload": upload_result}, ensure_ascii=False), flush=True)

    meta = {
        "ok": True,
        "idea_id": idea["id"],
        "title": idea["title_fa"],
        "path": str(out),
        "thumb": str(thumb),
        "size": out.stat().st_size,
        "duration": duration,
        "visual_mode": "per_sentence_matched",
        "upload": upload_result,
    }
    print(json.dumps(meta, ensure_ascii=False))
    return 0 if (not args.publish or upload_result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
