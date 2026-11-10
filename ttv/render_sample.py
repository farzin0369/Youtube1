#!/usr/bin/env python3
"""TTV viral emotional short — عشق یا وابستگی | one unique visual per line."""
from __future__ import annotations

import argparse
import html as html_lib
import json
import os
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

# Each beat has a UNIQUE Mixkit id that matches the meaning of the line.
IDEA = {
    "id": "emotion-00002",
    "title_fa": "عشق یا وابستگی؟",
    "beats": [
        {
            "spoken": "یک لحظه صبر کن.",
            "caption": "یک لحظه صبر کن…",
            "visual": 3026,  # looking out train window — pause/reflect
            "concept": "مکث / فکر",
        },
        {
            "spoken": "چیزی که اسمش را عشق می‌ذاری، شاید وابستگی باشه.",
            "caption": "عشق؟ یا وابستگی؟",
            "visual": 130,  # couple on crosswalk — relationship question
            "concept": "رابطه / سؤال",
        },
        {
            "spoken": "عشق واقعی حس آرامش می‌ده.",
            "caption": "عشق = آرامش",
            "visual": 1002,  # surfer sunset ocean — calm peace
            "concept": "آرامش",
        },
        {
            "spoken": "وابستگی حس اضطراب و ترس از دست دادن.",
            "caption": "وابستگی = اضطراب",
            "visual": 134,  # man followed in city — anxiety/fear
            "concept": "اضطراب",
        },
        {
            "spoken": "اگه بدون اون شخص نمی‌تونی آروم باشی…",
            "caption": "بدونش آروم نیستی؟",
            "visual": 1024,  # alone on rocks by water — loneliness
            "concept": "تنهایی",
        },
        {
            "spoken": "احتمالاً عاشق نیستی. وابسته شدی.",
            "caption": "وابسته شدی",
            "visual": 2526,  # arms crossed + city — closed/dependent
            "concept": "وابستگی",
        },
        {
            "spoken": "عشق تو را آزادتر می‌کند. وابستگی محدودت می‌کند.",
            "caption": "عشق آزاد می‌کند",
            "visual": 104,  # woman walking through trees — freedom
            "concept": "آزادی",
        },
        {
            "spoken": "تو کامنت بنویس: عشقت آروم‌کننده است یا مضطرب‌کننده؟",
            "caption": "تو کامنت بنویس…",
            "visual": 1510,  # coffee/talk bar — engagement CTA
            "concept": "دعوت به کامنت",
        },
        {
            "spoken": "بامو. یوزرنیم ما دوازده بامو.",
            "caption": "بامو · @12bamo",
            "visual": 1014,  # couple beach walk — warm brand close
            "concept": "برند",
        },
    ],
    "yt_title": "عشق حس آرامشه… وابستگی حس اضطرابه 💔 تو کدومی؟",
    "yt_desc": (
        "چیزی که اسمش را عشق می‌ذاری، شاید وابستگی باشه.\n\n"
        "عشق آزادت می‌کند. وابستگی محدودت می‌کند.\n\n"
        "تو کامنت بنویس: عشقت آروم‌کننده است یا مضطرب‌کننده؟\n\n"
        "بامو | @12bamo\n"
        "#shorts #عشق #وابستگی #روانشناسی #رابطه"
    ),
    "yt_tags": ["shorts", "عشق", "وابستگی", "روانشناسی", "رابطه", "احساس", "بامو", "12bamo"],
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
        print(f"clip ok {mid}", flush=True)
        return dest
    return None


def _build_audio_and_timeline(work: Path, beats: list[dict]):
    spoken = [b["spoken"] for b in beats]
    parts_dir = work / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    engine = "edge"

    if os.environ.get("ELEVENLABS_API_KEY", "").strip():
        from ttv.tts_elevenlabs import synthesize_beats

        meta = synthesize_beats(spoken, parts_dir)
        engine = "elevenlabs"
        timeline = []
        for row, b in zip(meta["timeline"], beats):
            timeline.append(
                {
                    **row,
                    "caption": b["caption"],
                    "visual": b["visual"],
                    "concept": b["concept"],
                }
            )
        narr_src = Path(meta["path"])
        full = work / "assets" / "narration.mp3"
        full.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(narr_src, full)
        duration = min(34.0, max(_probe(full), timeline[-1]["end"] if timeline else 1.0) + 0.05)
        print(json.dumps({"tts_engine": engine, "duration": duration}, ensure_ascii=False), flush=True)
        return full, timeline, duration

    import asyncio
    import edge_tts

    files: list[Path] = []
    timeline = []
    t = 0.0

    async def gen() -> None:
        nonlocal t
        for i, b in enumerate(beats):
            p = parts_dir / f"p{i:02d}.mp3"
            await edge_tts.Communicate(
                b["spoken"], "fa-IR-FaridNeural", rate="+4%", pitch="+0Hz"
            ).save(str(p))
            speech = max(0.7, _probe(p))
            gap = 0.14 if i < len(beats) - 1 else 0.28
            files.append(p)
            timeline.append(
                {
                    "i": i,
                    "start": round(t, 3),
                    "speech_end": round(t + speech, 3),
                    "end": round(t + speech + gap, 3),
                    "speech": speech,
                    "caption": b["caption"],
                    "visual": b["visual"],
                    "concept": b["concept"],
                    "spoken": b["spoken"],
                }
            )
            t += speech + gap

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
            "0.14",
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
    duration = min(34.0, max(_probe(full), timeline[-1]["end"]) + 0.05)
    print(json.dumps({"tts_engine": engine, "duration": duration}, ensure_ascii=False), flush=True)
    return full, timeline, duration


def _build_matched_film(work: Path, timeline: list[dict], duration: float) -> Path:
    clips_dir = work / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    tmp = work / "_film"
    tmp.mkdir(exist_ok=True)

    cache: dict[int, Path] = {}
    for beat in timeline:
        mid = int(beat["visual"])
        if mid not in cache:
            p = _fetch_mix(mid, clips_dir)
            if p:
                cache[mid] = p
            else:
                print(f"WARN missing mix {mid}", flush=True)
    if not cache:
        raise RuntimeError("no matched clips")

    segs: list[Path] = []
    for beat in timeline:
        mid = int(beat["visual"])
        src = cache.get(mid) or next(iter(cache.values()))
        slot = max(0.9, beat["end"] - beat["start"])
        seg = tmp / f"line_{beat['i']:02d}.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(src),
                "-t",
                f"{slot:.3f}",
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,eq=saturation=1.12:contrast=1.06",
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
        print(
            f"VISUAL {beat['i']}: clip={mid} | {beat['concept']} | {beat['spoken'][:40]}",
            flush=True,
        )

    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in segs), encoding="utf-8")
    raw = tmp / "concat.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-an",
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
            "-i",
            str(raw),
            "-t",
            f"{duration:.3f}",
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


def _write_html(work: Path, timeline: list[dict], duration: float, title: str) -> None:
    beats, gsap = [], []
    for beat in timeline:
        i = beat["i"]
        start = beat["start"]
        end = beat["speech_end"]
        text = beat["caption"]
        bid = f"beat-{i}"
        slot = max(0.5, end - start)
        size = 54 if i == 0 else (50 if i <= 2 else 44)
        beats.append(
            f'      <div id="{bid}" class="beat" style="font-size:{size}px" '
            f'data-start="{start:.2f}" data-duration="{slot:.2f}" data-track-index="{10 + i}">'
            f"{html_lib.escape(text)}</div>"
        )
        gsap.append(
            f'      tl.fromTo("#{bid}", {{opacity:0,y:24,scale:0.96}}, '
            f'{{opacity:1,y:0,scale:1,duration:0.22,ease:"power2.out"}}, {start:.2f});'
        )
        out_at = max(start + 0.35, end - 0.08)
        gsap.append(f'      tl.to("#{bid}", {{opacity:0,y:-10,duration:0.15}}, {out_at:.2f});')

    brand_at = max(0.4, duration - 2.0)
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
        rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.15) 35%,
        rgba(0,0,0,0.5) 68%, rgba(0,0,0,0.9) 100%);
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
      background: linear-gradient(90deg, #fff 0%, #f9a8d4 50%, #c4b5fd 100%);
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
      {{ opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "power3.out" }},
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
        ["ffmpeg", "-y", "-ss", "2.0", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(frame)],
        check=True,
        capture_output=True,
    )
    t1 = "عشق یا وابستگی؟"
    t2 = "تو کدومی؟"
    brand = "بامو  @12bamo"
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "eq=saturation=1.15:contrast=1.08,"
        "drawbox=x=0:y=1400:w=1080:h=520:color=black@0.55:t=fill,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{t1}':fontcolor=white:fontsize=56:x=(w-text_w)/2:y=1480:"
        f"borderw=3:bordercolor=black@0.8,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{t2}':fontcolor=#f9a8d4:fontsize=52:x=(w-text_w)/2:y=1570:"
        f"borderw=3:bordercolor=black@0.8,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{brand}':fontcolor=#c4b5fd:fontsize=40:x=(w-text_w)/2:y=1680:"
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
    beats = idea["beats"]
    joined = "\n".join(b["spoken"] for b in beats)
    analysis = TextAnalyzer().analyze(joined, title=idea["title_fa"])
    _ = SceneGenerator(aspect="portrait").from_analysis(analysis)

    print(
        json.dumps(
            {
                "idea": idea["id"],
                "title": idea["title_fa"],
                "visuals": [b["visual"] for b in beats],
                "concepts": [b["concept"] for b in beats],
                "has_elevenlabs": bool(os.environ.get("ELEVENLABS_API_KEY")),
                "publish": bool(args.publish),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    _audio, timeline, duration = _build_audio_and_timeline(work, beats)
    _build_matched_film(work, timeline, duration)
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
            category_id="22",
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
        "tts": "elevenlabs" if os.environ.get("ELEVENLABS_API_KEY") else "edge",
        "upload": upload_result,
    }
    print(json.dumps(meta, ensure_ascii=False))
    return 0 if (not args.publish or upload_result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
