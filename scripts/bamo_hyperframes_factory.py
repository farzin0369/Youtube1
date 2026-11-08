#!/usr/bin/env python3
"""Render one BAMO Short as a custom HyperFrames composition.

Never reuses the official kinetic-type promo (that is HyperFrames marketing).
Each render is idea-specific: title, hook lines, narration audio, brand endcard.
"""
from __future__ import annotations

import asyncio
import html
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "daily"


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 900) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True, timeout=timeout)


def _tts(text: str, dest: Path) -> float:
    """Generate English narration; return approximate duration seconds."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    async def gen() -> None:
        import edge_tts

        await edge_tts.Communicate(text, "en-US-GuyNeural").save(str(dest))

    asyncio.run(gen())
    # probe duration
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
        # ~2.6 words/sec spoken
        words = max(1, len(text.split()))
        dur = words / 2.55
    print(f"tts -> {dest} ({dur:.2f}s)", flush=True)
    return max(8.0, min(28.0, dur))


def _split_beats(title: str, hook: str, narration: str) -> list[str]:
    """Short on-screen lines (not the full narration dump)."""
    lines: list[str] = []
    t = (title or "").strip()
    if t:
        lines.append(t)
    h = (hook or "").strip()
    if h and h.lower() not in t.lower():
        lines.append(h)
    # pull 2–3 punchy sentences from narration (skip brand tag)
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
) -> None:
    work.mkdir(parents=True, exist_ok=True)
    (work / "assets").mkdir(exist_ok=True)
    beats = _split_beats(title, hook, narration)
    # equal time slots with small overlap-free windows
    slot = max(2.2, (duration - 0.6) / max(1, len(beats)))
    # escape for HTML text nodes
    safe = [html.escape(b) for b in beats]

    # Build beat divs + GSAP timeline entries
    beat_divs = []
    gsap_lines = []
    for i, text in enumerate(safe):
        start = 0.15 + i * slot
        bid = f"beat-{i}"
        beat_divs.append(
            f'      <div id="{bid}" class="beat" data-start="{start:.2f}" '
            f'data-duration="{slot:.2f}" data-track-index="{10 + i}">'
            f"{text}</div>"
        )
        # slam in, hold, exit
        gsap_lines.append(
            f'      tl.fromTo("#{bid}", '
            f'{{opacity: 0, scale: 0.82, y: 40}}, '
            f'{{opacity: 1, scale: 1, y: 0, duration: 0.45, ease: "power3.out"}}, '
            f"{start:.2f});"
        )
        hold_end = start + slot - 0.35
        gsap_lines.append(
            f'      tl.to("#{bid}", '
            f'{{opacity: 0, scale: 1.06, y: -24, duration: 0.3, ease: "power2.in"}}, '
            f"{hold_end:.2f});"
        )

    duration_s = f"{duration:.2f}"
    index = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>BAMO Short</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;700;900&display=block" rel="stylesheet" />
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      html, body {{
        margin: 0;
        width: 1080px;
        height: 1920px;
        overflow: hidden;
        background: #07070c;
        font-family: "Inter", system-ui, sans-serif;
        color: #f4f4f8;
      }}
      #root {{
        position: relative;
        width: 1080px;
        height: 1920px;
        overflow: hidden;
        background: radial-gradient(ellipse at 50% 20%, #1a1a2e 0%, #07070c 55%, #000 100%);
      }}
      .grid {{
        position: absolute; inset: 0;
        background-image:
          linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
        background-size: 80px 80px;
        opacity: 0.55;
        pointer-events: none;
      }}
      .glow {{
        position: absolute;
        width: 700px; height: 700px;
        left: 50%; top: 28%;
        transform: translate(-50%, -50%);
        background: radial-gradient(circle, rgba(80,120,255,0.22) 0%, transparent 70%);
        filter: blur(8px);
        pointer-events: none;
      }}
      .beat {{
        position: absolute;
        left: 64px; right: 64px;
        top: 42%;
        transform: translateY(-50%);
        text-align: center;
        font-weight: 900;
        font-size: 64px;
        line-height: 1.15;
        letter-spacing: -0.02em;
        opacity: 0;
        text-shadow: 0 8px 40px rgba(0,0,0,0.55);
        z-index: 5;
      }}
      #brand {{
        position: absolute;
        left: 0; right: 0; bottom: 120px;
        text-align: center;
        font-weight: 700;
        font-size: 28px;
        letter-spacing: 0.18em;
        color: rgba(244,244,248,0.72);
        opacity: 0;
        z-index: 6;
      }}
      #accent {{
        position: absolute;
        left: 50%; top: 18%;
        transform: translateX(-50%);
        width: 120px; height: 4px;
        border-radius: 4px;
        background: linear-gradient(90deg, #5b8cff, #a78bfa);
        opacity: 0;
        z-index: 4;
      }}
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="{duration_s}"
      data-width="1080"
      data-height="1920"
    >
      <div class="grid clip" data-start="0" data-duration="{duration_s}" data-track-index="0"></div>
      <div class="glow clip" id="glow" data-start="0" data-duration="{duration_s}" data-track-index="1"></div>
      <div id="accent" class="clip" data-start="0" data-duration="{duration_s}" data-track-index="2"></div>
{chr(10).join(beat_divs)}
      <div id="brand" class="clip" data-start="0" data-duration="{duration_s}" data-track-index="30">BAMO · @12bamo</div>
      <audio
        id="vo"
        class="clip"
        src="assets/narration.mp3"
        data-start="0"
        data-duration="{duration_s}"
        data-track-index="40"
        data-volume="1"
      ></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#accent", {{ opacity: 0, scaleX: 0.2 }}, {{ opacity: 1, scaleX: 1, duration: 0.5, ease: "power2.out" }}, 0.05);
      tl.fromTo("#glow", {{ opacity: 0.4, scale: 0.9 }}, {{ opacity: 1, scale: 1.08, duration: {duration_s}, ease: "none" }}, 0);
{chr(10).join(gsap_lines)}
      tl.fromTo("#brand", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, {max(0.2, duration - 2.2):.2f});
      // pad timeline to full slot (HyperFrames hides short timelines)
      tl.to({{}}, {{ duration: {duration_s} }}, 0);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (work / "index.html").write_text(index, encoding="utf-8")
    meta = {
        "duration": duration,
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "title": title,
        "brand": "BAMO",
    }
    (work / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def render_short(
    narration: str,
    out_mp4: Path,
    *,
    title: str = "",
    hook: str = "",
    workdir: Path | None = None,
) -> Path:
    work = workdir or Path("/tmp/bamo-pro")
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    # 1) narration first — duration drives composition length
    audio_path = work / "assets" / "narration.mp3"
    duration = _tts(narration, audio_path)
    # pad a little for endcard
    duration = min(28.0, duration + 1.2)

    # 2) idea-specific composition (NOT the HyperFrames promo example)
    _write_composition(
        work,
        title=title or "BAMO Fact",
        hook=hook or "",
        narration=narration,
        duration=duration,
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
    print(f"render ok -> {out_mp4} ({out_mp4.stat().st_size} bytes)", flush=True)
    return out_mp4


if __name__ == "__main__":
    text = (
        "Time is not the same for everyone. "
        "Near a black hole, one second can equal years on Earth. "
        "GPS satellites already correct for this every day. "
        "Relativity is not theory on a chalkboard. It runs the modern world. "
        "BAMO. Follow at twelve bamo."
    )
    title = "Time Is Not the Same for Everyone"
    hook = "Near a black hole, one second can equal years on Earth."
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
    dest = OUT_DIR / "BAMO_daily_latest.mp4"
    render_short(text, dest, title=title, hook=hook)
    print(json.dumps({"ok": True, "path": str(dest)}))
