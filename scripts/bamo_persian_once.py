#!/usr/bin/env python3
"""Publish one Persian BAMO Short from the curated idea bank."""
from __future__ import annotations

import argparse
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
from scripts.bamo_hyperframes_factory import render_short

# High-quality Persian packages keyed by English title (curated core)
FA_BY_TITLE: dict[str, dict[str, str]] = {
    "Why 23 People Make a Shared Birthday Likely": {
        "title": "چرا در ۲۳ نفر احتمال تولد مشترک بالاست؟",
        "hook": "ترکیب‌ها سریع‌تر از شهود ما رشد می‌کنند.",
        "narration": (
            "در اتاقی با بیست‌وسه نفر، احتمال اینکه دو نفر یک روز تولد مشترک داشته باشند "
            "بیش از پنجاه درصد است. شما با یک تاریخ ثابت مقایسه نمی‌کنید؛ "
            "همهٔ جفت‌ها را با هم می‌سنجید. احتمال، شمارش دقیق را پاداش می‌دهد نه حس درونی را. "
            "بامو. دنبال کنید at twelve bamo."
        ),
    },
    "Time Is Not the Same for Everyone": {
        "title": "زمان برای همه یکسان نیست",
        "hook": "نزدیک سیاه‌چاله، یک ثانیه می‌تواند برابر سال‌ها روی زمین باشد.",
        "narration": (
            "زمان برای همه یکسان نیست. نزدیک سیاه‌چاله، ساعت‌ها نسبت به زمین کندتر می‌چرخند. "
            "ماهواره‌های GPS هر روز اثر نسبیت را اصلاح می‌کنند؛ وگرنه نقشه‌ها منحرف می‌شدند. "
            "این فقط نظریه روی تخته نیست؛ مهندسی واقعی است. بامو. دنبال کنید at twelve bamo."
        ),
    },
    "Why the Sky Is Blue": {
        "title": "چرا آسمان آبی است؟",
        "hook": "نور خورشید به مولکول‌های هوا می‌خورد و آبی بیشتر پخش می‌شود.",
        "narration": (
            "نور خورشید سفید است، اما آسمان آبی دیده می‌شود. مولکول‌های هوا طول‌موج‌های کوتاه آبی را "
            "قوی‌تر پخش می‌کنند. در غروب مسیر نور در جو طولانی‌تر است و قرمز و نارنجی غالب می‌شوند. "
            "فیزیک ساده‌ای که هر روز می‌بینید. بامو. دنبال کنید at twelve bamo."
        ),
    },
    "Why Large Models Hallucinate": {
        "title": "چرا مدل‌های بزرگ توهم می‌سازند؟",
        "hook": "متن محتمل پیش‌بینی می‌کنند — نه حقیقت تأییدشده.",
        "narration": (
            "مدل‌های زبانی برای محتمل‌ترین توکن بعدی بهینه‌ می‌شوند. وقتی شواهد کم است، "
            "حدس‌های روان هنوز می‌توانند مطمئن به نظر برسند. خروجی را پیش‌نویس قابل راستی‌آزمایی ببینید، "
            "نه وحی. بامو. دنبال کنید at twelve bamo."
        ),
    },
    "Auroras Are Solar Wind Meeting Magnetospheres": {
        "title": "شفق قطبی چیست؟",
        "hook": "ذرات باردار جو بالایی را روشن می‌کنند.",
        "narration": (
            "خورشید پلاسما به بیرون می‌فرستد. میدان مغناطیسی زمین ذرات را به سمت قطب‌ها هدایت می‌کند "
            "و گازهای جو را برانگیخته می‌کند. رنگ به ارتفاع و شیمی بستگی دارد. آب‌وهوای فضایی که دیده می‌شود. "
            "بامو. دنبال کنید at twelve bamo."
        ),
    },
    "Most of the Universe Is Invisible": {
        "title": "بیشتر جهان نامرئی است",
        "hook": "کهکشان‌ها برای جرم دیده‌شده خیلی تند می‌چرخند.",
        "narration": (
            "ستاره‌های لبهٔ کهکشان‌ها طوری حرکت می‌کنند که انگار جرم نادیده‌ای هست. "
            "فیزیکدانان آن را ماده تاریک می‌نامند. گرانشش را می‌بینیم، نورش را نه. "
            "بامو. دنبال کنید at twelve bamo."
        ),
    },
    "The Infinite Hotel That Always Has Room": {
        "title": "هتل بی‌نهایتی که همیشه جا دارد",
        "hook": "هتلی با اتاق‌های بی‌نهایت پر است — و هنوز مهمان جدید می‌پذیرد.",
        "narration": (
            "هتل هیلبرت کاملاً پر است، اما هنوز می‌تواند مهمان تازه بپذیرد. "
            "هر مهمان از اتاق n به اتاق دو برابر n می‌رود. همهٔ اتاق‌های فرد آزاد می‌شوند. "
            "بی‌نهایت شمارا مثل عددهای روزمره رفتار نمی‌کند. بامو. دنبال کنید at twelve bamo."
        ),
    },
    "Why Your Brain Deletes Most of What You See": {
        "title": "چرا مغز بیشترِ آنچه می‌بینید را حذف می‌کند؟",
        "hook": "همین الان چیزی بزرگ را از دست دادید — و مغزتان مقصر است.",
        "narration": (
            "چشم‌ها خیلی بیشتر از آنچه ذهن ثبت می‌کند می‌گیرند. در آزمایش‌های کوریِ تغییر، "
            "افراد گوریلی را که از صحنه رد می‌شود نمی‌بینند. مغز دوربین نیست؛ ویرایشگر بی‌رحم است. "
            "بامو. دنبال کنید at twelve bamo."
        ),
    },
}


def _fa_package(idea: dict) -> dict:
    title_en = (idea.get("title") or idea.get("youtube_title") or "").strip()
    if title_en in FA_BY_TITLE:
        return FA_BY_TITLE[title_en]
    # fallback: keep structure, mark Persian frame with translated shell
    hook_en = (idea.get("hook") or "").strip()
    return {
        "title": title_en or "واقعیت علمی",
        "hook": hook_en or "یک حقیقت کوتاه از بانک ایده بامو.",
        "narration": (
            f"{hook_en} "
            f"{(idea.get('narration') or idea.get('summary') or '')} "
            "بامو. دنبال کنید at twelve bamo."
        ),
    }


def _tts_fa(text: str, dest: Path) -> float:
    import asyncio

    dest.parent.mkdir(parents=True, exist_ok=True)

    async def gen() -> None:
        import edge_tts

        # Male Persian neural voice
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
        dur = max(10.0, len(text) / 12.0)
    print(f"tts-fa -> {dest} ({dur:.2f}s)", flush=True)
    return max(10.0, min(28.0, dur))


def _split_fa_beats(title: str, hook: str, narration: str) -> list[str]:
    lines: list[str] = []
    if title.strip():
        lines.append(title.strip())
    if hook.strip() and hook.strip() not in lines:
        lines.append(hook.strip())
    body = re.sub(r"\s*بامو\..*$", "", narration, flags=re.I).strip()
    # Persian sentence split on . ! ? and Arabic question mark
    parts = re.split(r"(?<=[.!?؟])\s+", body)
    for p in parts:
        p = p.strip()
        if len(p) < 10:
            continue
        if p in lines:
            continue
        lines.append(p)
        if len(lines) >= 5:
            break
    lines.append("بامو · @12bamo")
    return lines[:6]


def _write_fa_composition(work: Path, *, title: str, hook: str, narration: str, duration: float) -> None:
    work.mkdir(parents=True, exist_ok=True)
    (work / "assets").mkdir(exist_ok=True)
    beats = _split_fa_beats(title, hook, narration)
    slot = max(2.4, (duration - 0.6) / max(1, len(beats)))
    safe = [html.escape(b) for b in beats]
    beat_divs = []
    gsap_lines = []
    for i, text in enumerate(safe):
        start = 0.15 + i * slot
        bid = f"beat-{i}"
        beat_divs.append(
            f'      <div id="{bid}" class="beat" data-start="{start:.2f}" '
            f'data-duration="{slot:.2f}" data-track-index="{10 + i}">{text}</div>'
        )
        gsap_lines.append(
            f'      tl.fromTo("#{bid}", {{opacity: 0, scale: 0.85, y: 36}}, '
            f'{{opacity: 1, scale: 1, y: 0, duration: 0.45, ease: "power3.out"}}, {start:.2f});'
        )
        hold_end = start + slot - 0.35
        gsap_lines.append(
            f'      tl.to("#{bid}", {{opacity: 0, scale: 1.05, y: -20, duration: 0.28, ease: "power2.in"}}, {hold_end:.2f});'
        )
    duration_s = f"{duration:.2f}"
    index = f"""<!doctype html>
<html lang="fa" dir="rtl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>BAMO FA</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@500;700;900&display=block" rel="stylesheet" />
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      html, body {{
        margin: 0; width: 1080px; height: 1920px; overflow: hidden;
        background: #07070c; font-family: "Vazirmatn", Tahoma, sans-serif; color: #f4f4f8;
        direction: rtl;
      }}
      #root {{
        position: relative; width: 1080px; height: 1920px; overflow: hidden;
        background: radial-gradient(ellipse at 50% 20%, #1a1a2e 0%, #07070c 55%, #000 100%);
      }}
      .grid {{
        position: absolute; inset: 0;
        background-image:
          linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
        background-size: 80px 80px; opacity: 0.5; pointer-events: none;
      }}
      .glow {{
        position: absolute; width: 700px; height: 700px; left: 50%; top: 28%;
        transform: translate(-50%, -50%);
        background: radial-gradient(circle, rgba(80,120,255,0.22) 0%, transparent 70%);
        filter: blur(8px); pointer-events: none;
      }}
      .beat {{
        position: absolute; left: 56px; right: 56px; top: 42%;
        transform: translateY(-50%); text-align: center;
        font-weight: 900; font-size: 52px; line-height: 1.35;
        opacity: 0; text-shadow: 0 8px 40px rgba(0,0,0,0.55); z-index: 5;
      }}
      #brand {{
        position: absolute; left: 0; right: 0; bottom: 120px; text-align: center;
        font-weight: 700; font-size: 28px; letter-spacing: 0.12em;
        color: rgba(244,244,248,0.75); opacity: 0; z-index: 6;
      }}
      #accent {{
        position: absolute; left: 50%; top: 18%; transform: translateX(-50%);
        width: 120px; height: 4px; border-radius: 4px;
        background: linear-gradient(90deg, #5b8cff, #a78bfa); opacity: 0; z-index: 4;
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration_s}" data-width="1080" data-height="1920">
      <div class="grid clip" data-start="0" data-duration="{duration_s}" data-track-index="0"></div>
      <div class="glow clip" id="glow" data-start="0" data-duration="{duration_s}" data-track-index="1"></div>
      <div id="accent" class="clip" data-start="0" data-duration="{duration_s}" data-track-index="2"></div>
{chr(10).join(beat_divs)}
      <div id="brand" class="clip" data-start="0" data-duration="{duration_s}" data-track-index="30">بامو · @12bamo</div>
      <audio id="vo" class="clip" src="assets/narration.mp3" data-start="0" data-duration="{duration_s}" data-track-index="40" data-volume="1"></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#accent", {{ opacity: 0, scaleX: 0.2 }}, {{ opacity: 1, scaleX: 1, duration: 0.5, ease: "power2.out" }}, 0.05);
      tl.fromTo("#glow", {{ opacity: 0.4, scale: 0.9 }}, {{ opacity: 1, scale: 1.08, duration: {duration_s}, ease: "none" }}, 0);
{chr(10).join(gsap_lines)}
      tl.fromTo("#brand", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, {max(0.2, duration - 2.2):.2f});
      tl.to({{}}, {{ duration: {duration_s} }}, 0);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (work / "index.html").write_text(index, encoding="utf-8")


def _render_fa(title: str, hook: str, narration: str, out_mp4: Path) -> Path:
    work = Path("/tmp/bamo-fa")
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    audio = work / "assets" / "narration.mp3"
    duration = _tts_fa(narration, audio)
    duration = min(28.0, duration + 1.2)
    _write_fa_composition(work, title=title, hook=hook, narration=narration, duration=duration)
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
    print(f"render-fa ok -> {out_mp4} ({out_mp4.stat().st_size} bytes)", flush=True)
    return out_mp4


def _thumb(video: Path) -> Path:
    thumb = video.with_suffix(".jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-ss", "2.5", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(thumb)],
        check=True,
        capture_output=True,
    )
    return thumb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    args = ap.parse_args()

    # Prefer an idea we have a polished FA pack for
    idea = None
    for _ in range(12):
        cand = select_idea(prefer_curated=True)
        if (cand.get("title") or "") in FA_BY_TITLE:
            idea = cand
            break
        idea = cand
    assert idea is not None
    fa = _fa_package(idea)
    print(json.dumps({"selected": idea.get("id"), "title_fa": fa["title"]}, ensure_ascii=False), flush=True)

    out = ROOT / "outputs" / "daily" / f"BAMO_FA_{idea.get('id')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.mp4"
    video = _render_fa(fa["title"], fa["hook"], fa["narration"], out)
    thumb = _thumb(video)

    upload_result: dict = {"ok": False, "skipped": True}
    if args.publish:
        from app.youtube_client import upload_video

        desc = (
            f"{fa['hook']}\n\n{fa['title']}\n\n"
            f"از بانک ایده بامو · Short فارسی\n"
            f"Follow @12bamo\n\n#shorts #بامو #علم #facts #BAMO #12bamo"
        )
        tags = ["shorts", "بامو", "علم", "BAMO", "12bamo", "persian", "science"]
        upload_result = upload_video(
            video_path=video,
            title=fa["title"][:100],
            description=desc[:5000],
            tags=tags,
            privacy=args.privacy,
            thumbnail_path=thumb,
            category_id="27",
        )
        if not upload_result.get("ok") and args.privacy == "public":
            upload_result = upload_video(
                video_path=video,
                title=fa["title"][:100],
                description=desc[:5000],
                tags=tags,
                privacy="unlisted",
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
    }
    append_history(record)
    print(json.dumps(record, ensure_ascii=False, default=str))
    return 0 if (not args.publish or upload_result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
