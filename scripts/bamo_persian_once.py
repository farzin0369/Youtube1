#!/usr/bin/env python3
"""Persian-only BAMO Short: REAL still photos (NASA/Wikimedia), not video A-roll.

Each caption beat can show a different real photograph with mild Ken-Burns motion.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.bamo_brain import append_history, mark_used, select_idea
from scripts.bamo_visuals import collect_visuals

FA_BY_TITLE: dict[str, dict[str, str]] = {
    "Time Is Not the Same for Everyone": {
        "title": "زمان برای همه یکسان نیست",
        "hook": "نزدیک سیاه‌چاله یک ثانیه می‌تواند برابر سال‌ها روی زمین باشد",
        "narration": (
            "زمان برای همه یکسان نیست. نزدیک سیاه‌چاله، ساعت‌ها نسبت به زمین کندتر می‌چرخند. "
            "ماهواره‌های جی‌پی‌اس هر روز اثر نسبیت را اصلاح می‌کنند؛ وگرنه نقشه‌ها منحرف می‌شدند. "
            "این فقط نظریه روی تخته نیست؛ مهندسی واقعی است. بامو. دنبال کنید at twelve bamo."
        ),
        "category": "black hole space physics",
        "search": "black hole nebula galaxy earth from space",
    },
    "Auroras Are Solar Wind Meeting Magnetospheres": {
        "title": "شفق قطبی چیست؟",
        "hook": "ذرات باردار جو بالایی را روشن می‌کنند",
        "narration": (
            "خورشید پلاسما به بیرون می‌فرستد. میدان مغناطیسی زمین ذرات را به سمت قطب‌ها هدایت می‌کند "
            "و گازهای جو را برانگیخته می‌کند. رنگ به ارتفاع و شیمی بستگی دارد. آب‌وهوای فضایی که دیده می‌شود. "
            "بامو. دنبال کنید at twelve bamo."
        ),
        "category": "aurora",
        "search": "aurora borealis northern lights earth from space",
    },
    "Most of the Universe Is Invisible": {
        "title": "بیشتر جهان نامرئی است",
        "hook": "کهکشان‌ها برای جرم دیده‌شده خیلی تند می‌چرخند",
        "narration": (
            "ستاره‌های لبهٔ کهکشان‌ها طوری حرکت می‌کنند که انگار جرم نادیده‌ای هست. "
            "فیزیکدانان آن را ماده تاریک می‌نامند. گرانشش را می‌بینیم، نورش را نه. "
            "بامو. دنبال کنید at twelve bamo."
        ),
        "category": "galaxy",
        "search": "galaxy milky way dark matter cosmos",
    },
    "Why the Sky Is Blue": {
        "title": "چرا آسمان آبی است؟",
        "hook": "نور خورشید به مولکول‌های هوا می‌خورد و آبی بیشتر پخش می‌شود",
        "narration": (
            "نور خورشید سفید است، اما آسمان آبی دیده می‌شود. مولکول‌های هوا طول‌موج‌های کوتاه آبی را "
            "قوی‌تر پخش می‌کنند. در غروب مسیر نور در جو طولانی‌تر است و قرمز و نارنجی غالب می‌شوند. "
            "فیزیک ساده‌ای که هر روز می‌بینید. بامو. دنبال کنید at twelve bamo."
        ),
        "category": "sky atmosphere",
        "search": "blue sky atmosphere earth sunset",
    },
    "Why Large Models Hallucinate": {
        "title": "چرا مدل‌های بزرگ توهم می‌سازند؟",
        "hook": "متن محتمل پیش‌بینی می‌کنند نه حقیقت تأییدشده",
        "narration": (
            "مدل‌های زبانی برای محتمل‌ترین توکن بعدی بهینه می‌شوند. وقتی شواهد کم است، "
            "حدس‌های روان هنوز می‌توانند مطمئن به نظر برسند. خروجی را پیش‌نویس قابل راستی‌آزمایی ببینید، "
            "نه وحی. بامو. دنبال کنید at twelve bamo."
        ),
        "category": "ai",
        "search": "computer circuit data center neural network",
    },
    "Why 23 People Make a Shared Birthday Likely": {
        "title": "چرا در بیست‌وسه نفر احتمال تولد مشترک بالاست؟",
        "hook": "ترکیب‌ها سریع‌تر از شهود ما رشد می‌کنند",
        "narration": (
            "در اتاقی با بیست‌وسه نفر، احتمال اینکه دو نفر یک روز تولد مشترک داشته باشند "
            "بیش از پنجاه درصد است. شما با یک تاریخ ثابت مقایسه نمی‌کنید؛ همهٔ جفت‌ها را با هم می‌سنجید. "
            "احتمال، شمارش دقیق را پاداش می‌دهد نه حس درونی را. بامو. دنبال کنید at twelve bamo."
        ),
        "category": "math",
        "search": "people crowd celebration birthday mathematics",
    },
}


def _tts_fa(text: str, dest: Path) -> float:
    dest.parent.mkdir(parents=True, exist_ok=True)

    async def gen() -> None:
        import edge_tts

        await edge_tts.Communicate(text, "fa-IR-FaridNeural").save(str(dest))

    asyncio.run(gen())
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(dest),
            ],
            text=True,
        ).strip()
        dur = float(out)
    except Exception:
        dur = max(10.0, len(text) / 11.0)
    print(f"tts-fa -> {dest} ({dur:.2f}s)", flush=True)
    return max(10.0, min(28.0, dur))


def _caption_timeline(title: str, hook: str, narration: str, duration: float) -> list[tuple[float, float, str]]:
    lines: list[str] = []
    if title.strip():
        lines.append(title.strip())
    if hook.strip() and hook.strip() not in lines:
        lines.append(hook.strip())
    body = re.sub(r"\s*بامو\..*$", "", narration, flags=re.I).strip()
    for p in re.split(r"(?<=[.!?؟])\s+", body):
        p = p.strip()
        if len(p) < 8:
            continue
        if p in lines:
            continue
        lines.append(p)
        if len(lines) >= 5:
            break
    lines.append("بامو · @12bamo")

    usable = max(6.0, duration - 0.8)
    weights = [max(4, len(x)) for x in lines]
    total_w = sum(weights) or 1
    timeline: list[tuple[float, float, str]] = []
    t = 0.12
    for line, w in zip(lines, weights):
        slot = usable * (w / total_w)
        slot = max(1.9, min(6.5, slot))
        end = min(duration - 0.12, t + slot)
        timeline.append((t, end, line))
        t = end + 0.06
        if t >= duration - 0.4:
            break
    return timeline


def _copy_photos(photos: list[Path], assets: Path, n: int) -> list[str]:
    """Copy real photos into assets/ as photo_00.jpg … return relative src list."""
    out: list[str] = []
    if not photos:
        return out
    for i in range(n):
        src = photos[i % len(photos)]
        ext = src.suffix.lower() if src.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"
        name = f"photo_{i:02d}{ext}"
        dest = assets / name
        shutil.copy2(src, dest)
        out.append(f"assets/{name}")
    return out


def _render_fa(
    *,
    title: str,
    hook: str,
    narration: str,
    category: str,
    search: str,
    out_mp4: Path,
) -> Path:
    work = Path("/tmp/bamo-fa")
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    assets = work / "assets"
    assets.mkdir(parents=True)

    duration = _tts_fa(narration, assets / "narration.mp3")
    duration = min(28.0, duration + 0.8)
    timeline = _caption_timeline(title, hook, narration, duration)

    # REAL images only — ignore videos from collector
    images, _videos = collect_visuals(
        search or title,
        category or "space",
        assets / "raw",
        hook=hook,
        max_images=6,
        max_videos=0,
    )
    if not images:
        images, _ = collect_visuals(
            "nebula galaxy earth from space",
            "astronomy",
            assets / "raw2",
            hook="cosmos",
            max_images=6,
            max_videos=0,
        )
    print(f"real photos: {len(images)}", flush=True)

    photo_srcs = _copy_photos(images, assets, max(1, len(timeline)))

    # Build photo layers + caption beats
    photo_divs: list[str] = []
    beat_divs: list[str] = []
    gsap_lines: list[str] = []

    if photo_srcs:
        for i, (start, end, _text) in enumerate(timeline):
            src = photo_srcs[i % len(photo_srcs)]
            pid = f"photo-{i}"
            slot = max(0.8, end - start)
            # mild continuous scale motion via CSS animation driven by GSAP
            photo_divs.append(
                f'      <img id="{pid}" class="photo clip" src="{src}" '
                f'data-start="{start:.2f}" data-duration="{slot:.2f}" data-track-index="{i}" '
                f'alt="" />'
            )
            # fade in/out; slow zoom while visible
            gsap_lines.append(
                f'      tl.fromTo("#{pid}", '
                f'{{opacity: 0, scale: 1.0}}, '
                f'{{opacity: 1, scale: 1.08, duration: 0.45, ease: "power1.out"}}, {start:.2f});'
            )
            out_at = max(start + 0.6, end - 0.35)
            gsap_lines.append(
                f'      tl.to("#{pid}", {{opacity: 0, scale: 1.12, duration: 0.35, ease: "power1.in"}}, {out_at:.2f});'
            )
    else:
        photo_divs.append(
            f'      <div class="fallback clip" data-start="0" data-duration="{duration:.2f}" data-track-index="0"></div>'
        )

    for i, (start, end, text) in enumerate(timeline):
        bid = f"beat-{i}"
        slot = max(0.8, end - start)
        beat_divs.append(
            f'      <div id="{bid}" class="beat" data-start="{start:.2f}" '
            f'data-duration="{slot:.2f}" data-track-index="{20 + i}">{html.escape(text)}</div>'
        )
        gsap_lines.append(
            f'      tl.fromTo("#{bid}", {{opacity: 0, y: 22}}, '
            f'{{opacity: 1, y: 0, duration: 0.3, ease: "power2.out"}}, {start:.2f});'
        )
        out_at = max(start + 0.5, end - 0.28)
        gsap_lines.append(
            f'      tl.to("#{bid}", {{opacity: 0, y: -8, duration: 0.22, ease: "power2.in"}}, {out_at:.2f});'
        )

    duration_s = f"{duration:.2f}"
    index = f"""<!doctype html>
<html lang="fa" dir="rtl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>بامو</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@700;900&display=block" rel="stylesheet" />
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      html, body {{
        margin: 0; width: 1080px; height: 1920px; overflow: hidden;
        background: #050508; font-family: "Vazirmatn", Tahoma, sans-serif;
        color: #fff; direction: rtl;
      }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      .photo {{
        position: absolute; inset: 0; width: 100%; height: 100%;
        object-fit: cover; opacity: 0; z-index: 1;
        transform-origin: center center;
      }}
      .fallback {{
        position: absolute; inset: 0;
        background: radial-gradient(ellipse at 50% 30%, #1b2240 0%, #07070c 60%, #000 100%);
      }}
      .scrim {{
        position: absolute; inset: 0; z-index: 2; pointer-events: none;
        background: linear-gradient(180deg,
          rgba(0,0,0,0.30) 0%, rgba(0,0,0,0.12) 40%,
          rgba(0,0,0,0.55) 72%, rgba(0,0,0,0.82) 100%);
      }}
      .beat {{
        position: absolute; left: 40px; right: 40px; bottom: 260px;
        text-align: center; font-weight: 900; font-size: 42px; line-height: 1.4;
        opacity: 0; z-index: 5;
        text-shadow: 0 3px 18px rgba(0,0,0,0.95), 0 0 3px #000;
      }}
      #brand {{
        position: absolute; left: 0; right: 0; bottom: 88px; text-align: center;
        font-weight: 700; font-size: 26px; color: rgba(255,255,255,0.9);
        opacity: 0; z-index: 6; text-shadow: 0 2px 10px rgba(0,0,0,0.9);
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration_s}" data-width="1080" data-height="1920">
{chr(10).join(photo_divs)}
      <div class="scrim clip" data-start="0" data-duration="{duration_s}" data-track-index="15"></div>
{chr(10).join(beat_divs)}
      <div id="brand" class="clip" data-start="0" data-duration="{duration_s}" data-track-index="40">بامو · @12bamo</div>
      <audio id="vo" class="clip" src="assets/narration.mp3" data-start="0" data-duration="{duration_s}" data-track-index="50" data-volume="1"></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(gsap_lines)}
      tl.fromTo("#brand", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, {max(0.2, duration - 1.8):.2f});
      tl.to({{}}, {{ duration: {duration_s} }}, 0);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (work / "index.html").write_text(index, encoding="utf-8")

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["npx", "--yes", "hyperframes@0.9.19", "render", "--gpu", "-o", str(out_mp4)],
            cwd=str(work),
            check=True,
            timeout=900,
        )
    except Exception:
        subprocess.run(
            ["npx", "--yes", "hyperframes@0.9.19", "render", "-o", str(out_mp4)],
            cwd=str(work),
            check=True,
            timeout=900,
        )
    if not out_mp4.exists() or out_mp4.stat().st_size < 50_000:
        raise RuntimeError(f"FA render failed: {out_mp4}")
    print(f"render-fa ok -> {out_mp4} photos={len(photo_srcs)}", flush=True)
    return out_mp4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--privacy", default="private", choices=["public", "unlisted", "private"])
    args = ap.parse_args()

    idea = None
    for _ in range(15):
        cand = select_idea(prefer_curated=True)
        if (cand.get("title") or "") in FA_BY_TITLE:
            idea = cand
            break
        idea = cand
    assert idea is not None
    title_en = (idea.get("title") or "").strip()
    fa = FA_BY_TITLE.get(title_en) or FA_BY_TITLE["Time Is Not the Same for Everyone"]

    print(json.dumps({"selected": idea.get("id"), "title_fa": fa["title"]}, ensure_ascii=False), flush=True)

    out = ROOT / "outputs" / "daily" / f"BAMO_FA_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.mp4"
    video = _render_fa(
        title=fa["title"],
        hook=fa["hook"],
        narration=fa["narration"],
        category=fa.get("category") or "astronomy",
        search=fa.get("search") or fa.get("category") or "space",
        out_mp4=out,
    )

    upload_result: dict = {"ok": False, "skipped": True}
    if args.publish:
        from app.youtube_client import upload_video

        thumb = video.with_suffix(".jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "2.5", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(thumb)],
            check=True,
            capture_output=True,
        )
        desc = f"{fa['hook']}\n\n{fa['title']}\n\n#shorts #بامو #علم"
        upload_result = upload_video(
            video_path=video,
            title=fa["title"][:100],
            description=desc[:5000],
            tags=["shorts", "بامو", "علم", "BAMO"],
            privacy=args.privacy,
            thumbnail_path=thumb,
            category_id="27",
        )
        if upload_result.get("ok"):
            mark_used(str(idea.get("id")))

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "lang": "fa",
        "idea_id": idea.get("id"),
        "title": fa["title"],
        "video": str(video),
        "upload": upload_result,
        "mode": "real_photos",
    }
    append_history(record)
    print(json.dumps(record, ensure_ascii=False, default=str))
    return 0 if (not args.publish or upload_result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
