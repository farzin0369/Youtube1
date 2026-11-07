#!/usr/bin/env python3
"""Render one BAMO Short with official HyperFrames kinetic-type quality."""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "daily"


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 900) -> None:
    print("+" , " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True, timeout=timeout)


def _tts(text: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)

    async def gen() -> None:
        import edge_tts

        await edge_tts.Communicate(text, "en-US-GuyNeural").save(str(dest))

    asyncio.run(gen())
    print(f"tts -> {dest}", flush=True)


def _patch_project(project: Path, narration_rel: str = "assets/narration.mp3") -> None:
    index = project / "index.html"
    if not index.exists():
        return
    t = index.read_text(encoding="utf-8")
    t = t.replace("width=1920, height=1080", "width=1080, height=1920")
    t = t.replace("width: 1920px", "width: 1080px")
    t = t.replace("height: 1080px", "height: 1920px")
    t = t.replace('data-width="1920"', 'data-width="1080"')
    t = t.replace('data-height="1080"', 'data-height="1920"')
    # soft brand swaps in graphics layer if present
    graphics = project / "compositions" / "main-graphics.html"
    if graphics.exists():
        g = graphics.read_text(encoding="utf-8")
        g = g.replace("HyperFrames", "BAMO").replace("hyperframes", "BAMO")
        graphics.write_text(g, encoding="utf-8")
    index.write_text(t, encoding="utf-8")


def render_short(narration: str, out_mp4: Path, workdir: Path | None = None) -> Path:
    work = workdir or Path("/tmp/bamo-pro")
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)

    # Official template (same quality language as HyperFrames GitHub samples)
    _run(
        [
            "npx",
            "--yes",
            "hyperframes@0.9.19",
            "init",
            str(work),
            "--example",
            "kinetic-type",
            "--non-interactive",
        ],
        timeout=180,
    )
    # Best-effort registry blocks
    for block in ("cosmic-orb", "gravitational-lens"):
        try:
            _run(
                ["npx", "--yes", "hyperframes@0.9.19", "add", block, "--no-clipboard"],
                cwd=work,
                timeout=120,
            )
        except Exception as exc:
            print(f"block {block} skipped: {exc}", flush=True)

    _patch_project(work)
    _tts(narration, work / "assets" / "narration.mp3")

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    try:
        _run(
            ["npx", "--yes", "hyperframes@0.9.19", "render", "--gpu", "-o", str(out_mp4)],
            cwd=work,
            timeout=900,
        )
    except Exception:
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
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
    dest = OUT_DIR / "BAMO_daily_latest.mp4"
    render_short(text, dest)
    print(json.dumps({"ok": True, "path": str(dest)}))
