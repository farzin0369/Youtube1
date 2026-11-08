#!/usr/bin/env python3
"""Render BAMO Shorts with topic-relevant A-roll + kinetic captions + TTS.

Visuals are fetched from NASA/Wikimedia by idea topic (e.g. astronomy → space
imagery), Ken-Burns motion applied, then HyperFrames composites captions + VO.
"""
from __future__ import annotations

import asyncio
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "daily"
sys.path.insert(0, str(ROOT))

from scripts.bamo_visuals import collect_visuals, images_to_kenburns_clip


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 900) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True, timeout=timeout)


def _tts(text: str, dest: Path, voice: str = "en-US-GuyNeural") -> float:
    dest.parent.mkdir(parents=True, exist_ok=True)

    async def gen() -> None:
        import edge_tts

        await edge_tts.Communicate(text, voice).save(str(dest))

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
        words = max(1, len(text.split()))
        dur = words / 2.55
    print(f"tts -> {dest} ({dur:.2f}s)", flush=True)
    return max(10.0, min(28.0, dur))


def _split_beats(title: str, hook: str, narration: str) -> list[str]:
    lines: list[str] = []
    t = (title or "").strip()
    if t:
        lines.append(t)
    h = (hook or "").strip()
    if h and h.lower() not in t.lower():
        lines.append(h)
    body = re.sub(r"\s*BAMO\..*$", "", narration or "", flags=re.I).strip()
    parts = re.split(r"(?<=[.!?])\s+", body)
    for p in parts:
        p = p.strip()
        if not p or len(p) < 12:
            continue
        if p.lower() in {x.lower() for x in lines}:
            continue
        lines.append(p)
        if len(lines) >= 5:
            break
    if len(lines) < 2:
        lines.append("Curiosity in under 30 seconds.")
    lines.append("BAMO · @12bamo")
    return lines[:6]


def _write_composition(
    work: Path,
    *,
    title: str,
    hook: str,
    narration: str,
    duration: float,
    has_aroll: bool,
) -> None:
    work.mkdir(parents=True, exist_ok=True)
    (work / "assets").mkdir(exist_ok=True)
    beats = _split_beats(title, hook, narration)
    slot = max(2.4, (duration - 0.8) / max(1, len(beats)))
    safe = [html.escape(b) for b in beats]

    beat_divs = []
    gsap_lines = []
    for i, text in enumerate(safe):
        start = 0.2 + i * slot
        bid = f"beat-{i}"
        beat_divs.append(
            f'      <div id="{bid}" class="beat" data-start="{start:.2f}" '
            f'data-duration="{slot:.2f}" data-track-index="{10 + i}">{text}</div>'
        )
        gsap_lines.append(
            f'      tl.fromTo("#{bid}", {{opacity: 0, y: 36, scale: 0.92}}, '
            f'{{opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "power3.out"}}, {start:.2f});'
        )
        hold_end = start + slot - 0.35
        gsap_lines.append(
            f'      tl.to("#{bid}", {{opacity: 0, y: -18, duration: 0.28, ease: "power2.in"}}, {hold_end:.2f});'
        )

    duration_s = f"{duration:.2f}"
    aroll_html = ""
    if has_aroll:
        aroll_html = f"""
      <video
        id="a-roll"
        class="clip"
        src="assets/aroll.mp4"
        data-start="0"
        data-duration="{duration_s}"
        data-track-index="0"
        muted
        playsinline
        style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;"
      ></video>
      <div class="scrim clip" data-start="0" data-duration="{duration_s}" data-track-index="1"></div>
"""
    else:
        aroll_html = f'<div class="fallback-bg clip" data-start="0" data-duration="{duration_s}" data-track-index="0"></div>\n'

    index = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>BAMO Short</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@600;800;900&display=block" rel="stylesheet" />
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      html, body {{
        margin: 0; width: 1080px; height: 1920px; overflow: hidden;
        background: #050508; font-family: "Inter", system-ui, sans-serif; color: #fff;
      }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; }}
      .fallback-bg {{
        position: absolute; inset: 0;
        background: radial-gradient(ellipse at 50% 30%, #1b2240 0%, #07070c 60%, #000 100%);
      }}
      .scrim {{
        position: absolute; inset: 0; z-index: 2;
        background: linear-gradient(180deg,
          rgba(0,0,0,0.35) 0%,
          rgba(0,0,0,0.15) 35%,
          rgba(0,0,0,0.55) 70%,
          rgba(0,0,0,0.75) 100%);
        pointer-events: none;
      }}
      .beat {{
        position: absolute; left: 48px; right: 48px; bottom: 280px;
        text-align: center; font-weight: 900; font-size: 48px; line-height: 1.2;
        letter-spacing: -0.02em; opacity: 0; z-index: 5;
        text-shadow: 0 4px 24px rgba(0,0,0,0.85), 0 0 2px rgba(0,0,0,0.9);
      }}
      #brand {{
        position: absolute; left: 0; right: 0; bottom: 96px; text-align: center;
        font-weight: 700; font-size: 26px; letter-spacing: 0.16em;
        color: rgba(255,255,255,0.85); opacity: 0; z-index: 6;
        text-shadow: 0 2px 12px rgba(0,0,0,0.8);
      }}
      #accent {{
        position: absolute; left: 50%; bottom: 420px; transform: translateX(-50%);
        width: 100px; height: 3px; border-radius: 3px; z-index: 4; opacity: 0;
        background: linear-gradient(90deg, #5b8cff, #c4b5fd);
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration_s}" data-width="1080" data-height="1920">
{aroll_html}
      <div id="accent" class="clip" data-start="0" data-duration="{duration_s}" data-track-index="3"></div>
{chr(10).join(beat_divs)}
      <div id="brand" class="clip" data-start="0" data-duration="{duration_s}" data-track-index="30">BAMO · @12bamo</div>
      <audio id="vo" class="clip" src="assets/narration.mp3" data-start="0" data-duration="{duration_s}" data-track-index="40" data-volume="1"></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#accent", {{ opacity: 0, scaleX: 0.3 }}, {{ opacity: 1, scaleX: 1, duration: 0.45 }}, 0.1);
{chr(10).join(gsap_lines)}
      tl.fromTo("#brand", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.35 }}, {max(0.3, duration - 2.0):.2f});
      tl.to({{}}, {{ duration: {duration_s} }}, 0);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (work / "index.html").write_text(index, encoding="utf-8")
    (work / "meta.json").write_text(
        json.dumps(
            {"duration": duration, "width": 1080, "height": 1920, "fps": 30, "title": title, "brand": "BAMO"},
            indent=2,
        ),
        encoding="utf-8",
    )


def render_short(
    narration: str,
    out_mp4: Path,
    *,
    title: str = "",
    hook: str = "",
    category: str = "",
    workdir: Path | None = None,
    voice: str = "en-US-GuyNeural",
) -> Path:
    work = workdir or Path("/tmp/bamo-pro")
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    assets = work / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    # 1) Voice first — timing source of truth
    audio_path = assets / "narration.mp3"
    duration = _tts(narration, audio_path, voice=voice)
    duration = min(28.0, duration + 1.0)

    # 2) Topic visuals → Ken Burns A-roll
    has_aroll = False
    try:
        stills = collect_visuals(
            title or "science",
            category or "science",
            assets / "stills",
            hook=hook or "",
            max_assets=4,
        )
        if stills:
            images_to_kenburns_clip(
                stills,
                assets / "aroll.mp4",
                duration=duration,
                width=1080,
                height=1920,
            )
            has_aroll = (assets / "aroll.mp4").exists()
    except Exception as exc:
        print(f"visual pipeline failed (will use fallback bg): {exc}", flush=True)
        has_aroll = False

    # 3) HyperFrames composition: A-roll + captions + VO
    _write_composition(
        work,
        title=title or "BAMO Fact",
        hook=hook or "",
        narration=narration,
        duration=duration,
        has_aroll=has_aroll,
    )

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    try:
        _run(
            ["npx", "--yes", "hyperframes@0.9.19", "render", "--gpu", "-o", str(out_mp4)],
            cwd=work,
            timeout=900,
        )
    except Exception as exc:
        print(f"gpu render failed ({exc}); retrying CPU", flush=True)
        _run(
            ["npx", "--yes", "hyperframes@0.9.19", "render", "-o", str(out_mp4)],
            cwd=work,
            timeout=900,
        )

    if not out_mp4.exists() or out_mp4.stat().st_size < 50_000:
        raise RuntimeError(f"Render failed or output too small: {out_mp4}")
    print(f"render ok -> {out_mp4} ({out_mp4.stat().st_size} bytes) aroll={has_aroll}", flush=True)
    return out_mp4


if __name__ == "__main__":
    text = (
        "Time is not the same for everyone. "
        "Near a black hole, one second can equal years on Earth. "
        "GPS satellites already correct for this every day. "
        "Relativity is not theory on a chalkboard. It runs the modern world. "
        "BAMO. Follow at twelve bamo."
    )
    dest = OUT_DIR / "BAMO_daily_latest.mp4"
    render_short(
        text,
        dest,
        title="Time Is Not the Same for Everyone",
        hook="Near a black hole, one second can equal years on Earth.",
        category="Physics & astrophysics",
    )
    print(json.dumps({"ok": True, "path": str(dest)}))
