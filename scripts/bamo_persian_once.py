#!/usr/bin/env python3
"""Persian Shorts from REAL stock video (Mixkit + NASA) — not photo Ken-Burns."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.bamo_brain import append_history, mark_used, select_idea
from scripts.bamo_visuals import nasa_media

UA = "Mozilla/5.0 (compatible; BAMOShorts/1.0)"

# Curated Mixkit free video IDs (direct CDN mp4 works: /videos/{id}/{id}-720.mp4)
MIXKIT_BY_TOPIC: dict[str, list[int]] = {
    "space": [14185, 18791, 31559, 19649, 30265],
    "astronomy": [14185, 18791, 31559, 34788],
    "aurora": [34788, 14185, 31559],
    "physics": [18791, 14185, 31559, 19649],
    "galaxy": [14185, 31559, 30265],
    "ai": [30265, 19649, 26877],
    "math": [26877, 19649],
    "default": [14185, 18791, 31559, 19649],
}

FA_BY_TITLE: dict[str, dict[str, str]] = {
    "Time Is Not the Same for Everyone": {
        "title": "زمان برای همه یکسان نیست",
        "hook": "نزدیک سیاه‌چاله یک ثانیه می‌تواند برابر سال‌ها روی زمین باشد",
        "narration": (
            "زمان برای همه یکسان نیست. نزدیک سیاه‌چاله، ساعت‌ها نسبت به زمین کندتر می‌چرخند. "
            "ماهواره‌های جی‌پی‌اس هر روز اثر نسبیت را اصلاح می‌کنند؛ وگرنه نقشه‌ها منحرف می‌شدند. "
            "این فقط نظریه روی تخته نیست؛ مهندسی واقعی است. بامو. دنبال کنید at twelve bamo."
        ),
        "topic": "physics",
        "nasa_q": "black hole",
    },
    "Auroras Are Solar Wind Meeting Magnetospheres": {
        "title": "شفق قطبی چیست؟",
        "hook": "ذرات باردار جو بالایی را روشن می‌کنند",
        "narration": (
            "خورشید پلاسما به بیرون می‌فرستد. میدان مغناطیسی زمین ذرات را به سمت قطب‌ها هدایت می‌کند "
            "و گازهای جو را برانگیخته می‌کند. رنگ به ارتفاع و شیمی بستگی دارد. آب‌وهوای فضایی که دیده می‌شود. "
            "بامو. دنبال کنید at twelve bamo."
        ),
        "topic": "aurora",
        "nasa_q": "aurora",
    },
    "Most of the Universe Is Invisible": {
        "title": "بیشتر جهان نامرئی است",
        "hook": "کهکشان‌ها برای جرم دیده‌شده خیلی تند می‌چرخند",
        "narration": (
            "ستاره‌های لبهٔ کهکشان‌ها طوری حرکت می‌کنند که انگار جرم نادیده‌ای هست. "
            "فیزیکدانان آن را ماده تاریک می‌نامند. گرانشش را می‌بینیم، نورش را نه. "
            "بامو. دنبال کنید at twelve bamo."
        ),
        "topic": "galaxy",
        "nasa_q": "galaxy",
    },
    "Why the Sky Is Blue": {
        "title": "چرا آسمان آبی است؟",
        "hook": "نور خورشید به مولکول‌های هوا می‌خورد و آبی بیشتر پخش می‌شود",
        "narration": (
            "نور خورشید سفید است، اما آسمان آبی دیده می‌شود. مولکول‌های هوا طول‌موج‌های کوتاه آبی را "
            "قوی‌تر پخش می‌کنند. در غروب مسیر نور در جو طولانی‌تر است و قرمز و نارنجی غالب می‌شوند. "
            "فیزیک ساده‌ای که هر روز می‌بینید. بامو. دنبال کنید at twelve bamo."
        ),
        "topic": "space",
        "nasa_q": "earth atmosphere",
    },
    "Why Large Models Hallucinate": {
        "title": "چرا مدل‌های بزرگ توهم می‌سازند؟",
        "hook": "متن محتمل پیش‌بینی می‌کنند نه حقیقت تأییدشده",
        "narration": (
            "مدل‌های زبانی برای محتمل‌ترین توکن بعدی بهینه می‌شوند. وقتی شواهد کم است، "
            "حدس‌های روان هنوز می‌توانند مطمئن به نظر برسند. خروجی را پیش‌نویس قابل راستی‌آزمایی ببینید، "
            "نه وحی. بامو. دنبال کنید at twelve bamo."
        ),
        "topic": "ai",
        "nasa_q": "technology",
    },
}


def _download(url: str, dest: Path, timeout: int = 180) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as f:
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
        print(f"dl fail {url}: {exc}", flush=True)
        dest.unlink(missing_ok=True)
        return False


def _fetch_videos(topic: str, nasa_q: str, dest: Path, need: int = 3) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    # 1) Mixkit curated real stock video
    ids = MIXKIT_BY_TOPIC.get(topic) or MIXKIT_BY_TOPIC["default"]
    for i, mid in enumerate(ids):
        if len(paths) >= need:
            break
        url = f"https://assets.mixkit.co/videos/{mid}/{mid}-720.mp4"
        p = dest / f"mix_{mid}.mp4"
        if _download(url, p):
            paths.append(p)
            print(f"mixkit video ok {p.name}", flush=True)
    # 2) NASA real video if available
    try:
        _imgs, vids = nasa_media(nasa_q or topic, images=0, videos=3)
        for j, url in enumerate(vids):
            if len(paths) >= need + 1:
                break
            p = dest / f"nasa_{j}.mp4"
            if _download(url, p):
                paths.append(p)
                print(f"nasa video ok {p.name}", flush=True)
    except Exception as exc:
        print(f"nasa video skip: {exc}", flush=True)
    return paths


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
        return 5.0


def _build_film_bg(videos: list[Path], out: Path, duration: float, w: int = 1080, h: int = 1920) -> Path:
    """Cut real video clips into a continuous vertical film bed."""
    if not videos:
        raise RuntimeError("no real video clips")
    tmp = out.parent / "_film"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    segs: list[Path] = []
    per = max(4.0, duration / max(1, min(3, len(videos))))
    for i, vid in enumerate(videos[:3]):
        seg = tmp / f"s{i}.mp4"
        # loop each source to cover its slot, crop to vertical 9:16
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(vid),
            "-t",
            f"{per:.2f}",
            "-vf",
            f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=30,eq=brightness=-0.03:saturation=1.05",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            str(seg),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        segs.append(seg)

    if len(segs) == 1:
        raw = segs[0]
    else:
        # xfade between real video segments
        inputs = []
        for s in segs:
            inputs.extend(["-i", str(s)])
        durs = [_probe(s) for s in segs]
        fade = 0.5
        parts = []
        prev = "[0:v]"
        acc = durs[0]
        out_l = "[0:v]"
        for i in range(1, len(segs)):
            out_l = f"[x{i}]"
            off = max(0.1, acc - fade)
            parts.append(f"{prev}[{i}:v]xfade=transition=fade:duration={fade}:offset={off:.2f}{out_l}")
            prev = out_l
            acc = acc + durs[i] - fade
        raw = tmp / "xf.mp4"
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

    # fit exact duration
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
    print(f"film bg -> {out} ({out.stat().st_size} bytes)", flush=True)
    return out


def _tts_fa(text: str, dest: Path) -> float:
    dest.parent.mkdir(parents=True, exist_ok=True)

    async def gen() -> None:
        import edge_tts

        await edge_tts.Communicate(text, "fa-IR-FaridNeural").save(str(dest))

    asyncio.run(gen())
    return max(10.0, min(28.0, _probe(dest)))


def _timeline(title: str, hook: str, narration: str, duration: float) -> list[tuple[float, float, str]]:
    lines: list[str] = []
    if title.strip():
        lines.append(title.strip())
    if hook.strip() and hook.strip() not in lines:
        lines.append(hook.strip())
    body = re.sub(r"\s*بامو\..*$", "", narration, flags=re.I).strip()
    for p in re.split(r"(?<=[.!?؟])\s+", body):
        p = p.strip()
        if len(p) < 8 or p in lines:
            continue
        lines.append(p)
        if len(lines) >= 5:
            break
    lines.append("بامو · @12bamo")
    usable = max(6.0, duration - 0.6)
    weights = [max(4, len(x)) for x in lines]
    tw = sum(weights) or 1
    t = 0.1
    out: list[tuple[float, float, str]] = []
    for line, w in zip(lines, weights):
        slot = max(1.8, min(6.0, usable * (w / tw)))
        end = min(duration - 0.1, t + slot)
        out.append((t, end, line))
        t = end + 0.05
        if t >= duration - 0.4:
            break
    return out


def _ass(timeline: list[tuple[float, float, str]], path: Path) -> None:
    def ts(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        cs = int((sec - int(sec)) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,52,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start, end, text in timeline:
        # ASS uses \N for newline; escape braces
        safe = text.replace("{", "\\{").replace("}", "\\}")
        events.append(f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{safe}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def _mux(bg: Path, audio: Path, ass: Path, out: Path) -> Path:
    # burn Persian subtitles onto real video film + attach audio
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(bg),
        "-i",
        str(audio),
        "-vf",
        f"ass={ass}",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    if not out.exists() or out.stat().st_size < 100_000:
        raise RuntimeError("mux failed")
    return out


def _render_fa(*, title: str, hook: str, narration: str, topic: str, nasa_q: str, out_mp4: Path) -> Path:
    work = Path("/tmp/bamo-film")
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    audio = work / "vo.mp3"
    duration = _tts_fa(narration, audio)
    duration = min(28.0, duration + 0.6)

    clips = _fetch_videos(topic, nasa_q, work / "clips", need=3)
    if not clips:
        raise RuntimeError("could not download any real video footage")

    bg = work / "film_bg.mp4"
    _build_film_bg(clips, bg, duration=duration)

    timeline = _timeline(title, hook, narration, duration)
    ass = work / "captions.ass"
    _ass(timeline, ass)

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    _mux(bg, audio, ass, out_mp4)
    print(f"FILM ok -> {out_mp4} ({out_mp4.stat().st_size} bytes) clips={len(clips)}", flush=True)
    return out_mp4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--privacy", default="private", choices=["public", "unlisted", "private"])
    args = ap.parse_args()

    idea = None
    for _ in range(12):
        cand = select_idea(prefer_curated=True)
        if (cand.get("title") or "") in FA_BY_TITLE:
            idea = cand
            break
        idea = cand
    assert idea is not None
    title_en = (idea.get("title") or "").strip()
    fa = FA_BY_TITLE.get(title_en) or FA_BY_TITLE["Time Is Not the Same for Everyone"]

    print(json.dumps({"selected": idea.get("id"), "title_fa": fa["title"], "mode": "real_video_film"}, ensure_ascii=False), flush=True)

    out = ROOT / "outputs" / "daily" / f"BAMO_FA_FILM_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.mp4"
    video = _render_fa(
        title=fa["title"],
        hook=fa["hook"],
        narration=fa["narration"],
        topic=fa.get("topic") or "space",
        nasa_q=fa.get("nasa_q") or "space",
        out_mp4=out,
    )

    upload_result: dict = {"ok": False, "skipped": True}
    if args.publish:
        from app.youtube_client import upload_video

        thumb = video.with_suffix(".jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "3", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(thumb)],
            check=True,
            capture_output=True,
        )
        upload_result = upload_video(
            video_path=video,
            title=fa["title"][:100],
            description=f"{fa['hook']}\n\n#shorts #بامو #علم",
            tags=["shorts", "بامو", "علم"],
            privacy=args.privacy,
            thumbnail_path=thumb,
            category_id="27",
        )
        if upload_result.get("ok"):
            mark_used(str(idea.get("id")))

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "lang": "fa",
        "mode": "real_video_film",
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
