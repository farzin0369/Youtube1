#!/usr/bin/env python3
"""TTV sample: idea bank → Persian rewrite → hard-sync TTS → real video → MP4.

No YouTube upload. Portrait Shorts 1080x1920.
"""
from __future__ import annotations

import asyncio
import html as html_lib
import json
import random
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

# High-virality idea from bank, rewritten in natural Persian.
# Spoken text carefully written for Edge-TTS (no broken harakat).
IDEA = {
    "id": "idea-00001",
    "title_en": "Why Your Brain Deletes Most of What You See",
    "title_fa": "چرا مغز بیشتر چیزهایی که می‌بینی را پاک می‌کند؟",
    "spoken": [
        "چرا مغز بیشتر چیزهایی که می‌بینی را پاک می‌کند؟",
        "چشم‌های تو اطلاعات خیلی زیادی می‌گیرد.",
        "اما ذهن همه را نگه نمی‌دارد.",
        "دانشمندان به این می‌گویند تنگنای توجه.",
        "در آزمایش‌ها، آدم‌ها حتی یک گوریل را وسط صحنه نمی‌بینند.",
        "مغز تو دوربین نیست. یک تدوین‌گر سخت‌گیر است.",
        "بامو. یوزرنیم ما: دوازده بامو.",
    ],
    "captions": [
        "چرا مغز بیشتر دیده‌ها را پاک می‌کند؟",
        "چشم‌ها اطلاعات زیادی می‌گیرند",
        "اما ذهن همه را نگه نمی‌دارد",
        "تنگنای توجه",
        "گاهی حتی گوریل را نمی‌بینیم",
        "مغز دوربین نیست؛ تدوین‌گر است",
        "بامو · @12bamo",
    ],
    "mixkit_ids": [30265, 19649, 26877, 31559],
    "topic": "psychology",
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


async def _tts(text: str, dest: Path) -> float:
    import edge_tts

    dest.parent.mkdir(parents=True, exist_ok=True)
    for voice in ("fa-IR-DilaraNeural", "fa-IR-FaridNeural"):
        try:
            await edge_tts.Communicate(text, voice).save(str(dest))
            if dest.exists() and dest.stat().st_size > 800:
                print(f"tts [{voice}] {dest.name} {_probe(dest):.2f}s", flush=True)
                return max(0.9, _probe(dest))
        except Exception as exc:
            print(f"tts fail {voice}: {exc}", flush=True)
    raise RuntimeError(f"TTS failed: {text}")


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
            dur = await _tts(s, p)
            files.append(p)
            cap = captions[i] if i < len(captions) else s
            timeline.append((t, t + dur, cap))
            t += dur + 0.07

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
            "0.07",
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
    duration = min(28.0, _probe(full) + 0.25)
    return full, timeline, duration


def _build_film(work: Path, duration: float, mix_ids: list[int]) -> Path:
    clips_dir = work / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    for mid in mix_ids:
        url = f"https://assets.mixkit.co/videos/{mid}/{mid}-720.mp4"
        p = clips_dir / f"mix_{mid}.mp4"
        if _download(url, p):
            clips.append(p)
            print(f"stock video ok {p.name}", flush=True)
        if len(clips) >= 3:
            break
    if not clips:
        raise RuntimeError("no stock video downloaded")

    tmp = work / "_film"
    tmp.mkdir(exist_ok=True)
    segs = []
    per = max(4.5, duration / len(clips))
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
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,eq=saturation=1.08:brightness=-0.02",
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
        # chain xfade
        raw = tmp / "xf.mp4"
        inputs = []
        for s in segs:
            inputs.extend(["-i", str(s)])
        durs = [_probe(s) for s in segs]
        fade = 0.45
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
        slot = max(0.6, end - start)
        beats.append(
            f'      <div id="{bid}" class="beat" data-start="{start:.2f}" '
            f'data-duration="{slot:.2f}" data-track-index="{10 + i}">{html_lib.escape(text)}</div>'
        )
        gsap.append(
            f'      tl.fromTo("#{bid}", {{opacity:0,y:20,scale:0.98}}, '
            f'{{opacity:1,y:0,scale:1,duration:0.28,ease:"power2.out"}}, {start:.2f});'
        )
        out_at = max(start + 0.45, end - 0.12)
        gsap.append(f'      tl.to("#{bid}", {{opacity:0,y:-10,duration:0.2}}, {out_at:.2f});')

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
        rgba(0,0,0,0.35) 0%, rgba(0,0,0,0.12) 38%,
        rgba(0,0,0,0.55) 70%, rgba(0,0,0,0.82) 100%);
    }}
    .beat {{
      position: absolute; left: 36px; right: 36px; bottom: 300px;
      text-align: center; font-weight: 900; font-size: 48px; line-height: 1.45;
      opacity: 0; z-index: 5;
      text-shadow: 0 4px 22px rgba(0,0,0,0.95), 0 0 4px #000;
    }}
    #brand {{
      position: absolute; left: 0; right: 0; bottom: 110px; text-align: center;
      font-weight: 700; font-size: 28px; opacity: 0; z-index: 6;
      color: rgba(255,255,255,0.92); text-shadow: 0 2px 12px #000;
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
    <div id="brand" class="clip" data-start="0" data-duration="{ds}" data-track-index="30">بامو · @12bamo</div>
    <audio id="vo" class="clip" src="assets/narration.mp3" data-start="0" data-duration="{ds}"
      data-track-index="40" data-volume="1"></audio>
  </div>
  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join(gsap)}
    tl.fromTo("#brand", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.35 }}, {max(0.3, duration - 1.7):.2f});
    tl.to({{}}, {{ duration: {ds} }}, 0);
    window.__timelines["main"] = tl;
  </script>
</body>
</html>
"""
    (work / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    work = Path("/tmp/ttv-sample")
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    idea = IDEA
    # Also run analyzer for logs / future pipeline
    joined = "\n".join(idea["spoken"][:-1])
    analysis = TextAnalyzer().analyze(joined, title=idea["title_fa"])
    plan = SceneGenerator(aspect="portrait").from_analysis(analysis)
    print(json.dumps({"idea": idea["id"], "analysis_tone": analysis.tone, "plan_scenes": len(plan.scenes)}, ensure_ascii=False), flush=True)

    _audio, timeline, duration = _build_audio(work, idea["spoken"], idea["captions"])
    _build_film(work, duration, idea["mixkit_ids"])
    _write_html(work, timeline, duration, idea["title_fa"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"BAMO_TTV_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.mp4"
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

    meta = {
        "ok": True,
        "idea_id": idea["id"],
        "title": idea["title_fa"],
        "path": str(out),
        "size": out.stat().st_size,
        "duration": duration,
        "engine": "ttv+hyperframes",
        "publish": False,
    }
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
