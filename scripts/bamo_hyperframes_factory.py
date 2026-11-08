#!/usr/bin/env python3
"""BAMO Shorts: animated topic A-roll + narration-synced captions + TTS."""
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

from scripts.bamo_visuals import build_animated_aroll, collect_visuals


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
        dur = max(1, len(text.split())) / 2.55
    print(f"tts -> {dest} ({dur:.2f}s)", flush=True)
    return max(10.0, min(28.0, dur))


def _caption_timeline(title: str, hook: str, narration: str, duration: float) -> list[tuple[float, float, str]]:
    """Return (start, end, text) aligned to narration length by word-weight."""
    lines: list[str] = []
    if title.strip():
        lines.append(title.strip())
    if hook.strip() and hook.strip().lower() not in title.lower():
        lines.append(hook.strip())
    body = re.sub(r"\s*BAMO\..*$", "", narration or "", flags=re.I).strip()
    for p in re.split(r"(?<=[.!?])\s+", body):
        p = p.strip()
        if len(p) < 12:
            continue
        if p.lower() in {x.lower() for x in lines}:
            continue
        lines.append(p)
        if len(lines) >= 5:
            break
    lines.append("BAMO · @12bamo")

    # Word weights for proportional timing; leave 0.4s tail after last caption start area
    usable = max(6.0, duration - 0.8)
    weights = [max(3, len(x.split())) for x in lines]
    total_w = sum(weights) or 1
    timeline: list[tuple[float, float, str]] = []
    t = 0.15
    for i, (line, w) in enumerate(zip(lines, weights)):
        slot = usable * (w / total_w)
        slot = max(1.8, min(6.5, slot))
        end = min(duration - 0.15, t + slot)
        timeline.append((t, end, line))
        t = end + 0.08  # tiny gap so captions don't overlap
        if t >= duration - 0.5:
            break
    return timeline


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
    timeline = _caption_timeline(title, hook, narration, duration)

    beat_divs = []
    gsap_lines = []
    for i, (start, end, text) in enumerate(timeline):
        bid = f"beat-{i}"
        dur_slot = max(0.8, end - start)
        beat_divs.append(
            f'      <div id="{bid}" class="beat" data-start="{start:.2f}" '
            f'data-duration="{dur_slot:.2f}" data-track-index="{10 + i}">{html.escape(text)}</div>'
        )
        # in
        gsap_lines.append(
            f'      tl.fromTo("#{bid}", {{opacity: 0, y: 28}}, '
            f'{{opacity: 1, y: 0, duration: 0.35, ease: "power2.out"}}, {start:.2f});'
        )
        # out slightly before end
        out_at = max(start + 0.5, end - 0.3)
        gsap_lines.append(
            f'      tl.to("#{bid}", {{opacity: 0, y: -12, duration: 0.25, ease: "power2.in"}}, {out_at:.2f});'
        )

    duration_s = f"{duration:.2f}"
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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@700;900&display=block" rel="stylesheet" />
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
        position: absolute; inset: 0; z-index: 2; pointer-events: none;
        background: linear-gradient(180deg,
          rgba(0,0,0,0.25) 0%,
          rgba(0,0,0,0.10) 40%,
          rgba(0,0,0,0.55) 72%,
          rgba(0,0,0,0.78) 100%);
      }}
      .beat {{
        position: absolute; left: 40px; right: 40px; bottom: 260px;
        text-align: center; font-weight: 900; font-size: 44px; line-height: 1.22;
        letter-spacing: -0.02em; opacity: 0; z-index: 5;
        text-shadow: 0 3px 18px rgba(0,0,0,0.9), 0 0 3px rgba(0,0,0,1);
      }}
      #brand {{
        position: absolute; left: 0; right: 0; bottom: 88px; text-align: center;
        font-weight: 700; font-size: 24px; letter-spacing: 0.14em;
        color: rgba(255,255,255,0.88); opacity: 0; z-index: 6;
        text-shadow: 0 2px 10px rgba(0,0,0,0.85);
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration_s}" data-width="1080" data-height="1920">
{aroll_html}
{chr(10).join(beat_divs)}
      <div id="brand" class="clip" data-start="0" data-duration="{duration_s}" data-track-index="30">BAMO · @12bamo</div>
      <audio id="vo" class="clip" src="assets/narration.mp3" data-start="0" data-duration="{duration_s}" data-track-index="40" data-volume="1"></audio>
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
    (work / "meta.json").write_text(
        json.dumps({"duration": duration, "width": 1080, "height": 1920, "fps": 30, "title": title}, indent=2),
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

    # 1) Voice = clock
    audio_path = assets / "narration.mp3"
    duration = _tts(narration, audio_path, voice=voice)
    duration = min(28.0, duration + 0.8)

    # 2) Animated topic A-roll (video preferred, else moving stills)
    has_aroll = False
    try:
        images, videos = collect_visuals(
            title or "science",
            category or "science",
            assets / "media",
            hook=hook or "",
            max_images=5,
            max_videos=2,
        )
        if images or videos:
            build_animated_aroll(
                images,
                videos,
                assets / "aroll.mp4",
                duration=duration,
                width=1080,
                height=1920,
            )
            has_aroll = (assets / "aroll.mp4").exists()
    except Exception as exc:
        print(f"animated aroll failed: {exc}", flush=True)
        has_aroll = False

    # 3) Composition with caption times matched to VO duration
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
