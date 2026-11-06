"""WebGL 3D motion renderer for BAMO (HTML/WebGL engine).

Uses Playwright to drive the intelligent HTML engine and capture frames,
then assembles a silent MP4 that the production renderer can mix with TTS + music.

This is intentionally designed so the visual brain lives in HTML/JS
(theme detection, motif selection, animation) while Python handles
timing, capture and final muxing with the existing factory pipeline.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _run(cmd: list[str], timeout: int = 600) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {result.stderr[-2000:]}")


def _engine_path() -> Path:
    """Locate the pipeline HTML engine inside the repo."""
    candidates = [
        Path(__file__).resolve().parent.parent / "preview" / "bamo-engine-pipeline.html",
        Path.cwd() / "preview" / "bamo-engine-pipeline.html",
        Path("preview/bamo-engine-pipeline.html"),
    ]
    for p in candidates:
        if p.is_file():
            return p.resolve()
    raise FileNotFoundError("bamo-engine-pipeline.html not found")


def render_html_project(
    project: dict[str, Any],
    output: str | Path,
    *,
    fps: int = 24,
    width: int = 720,
    height: int = 1280,
) -> Path:
    """
    Render a BAMO project (scenes with duration + text + narration) to a silent MP4
    using the HTML/WebGL 3D engine via Playwright screenshots.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for the HTML motion renderer. "
            "Install with: pip install playwright && playwright install chromium"
        ) from exc

    # CI smoke runs may render at reduced device scale and frame rate while
    # preserving the requested MP4 dimensions. Production defaults stay full quality.
    render_scale = float(os.getenv("BAMO_RENDER_SCALE", "1.0"))
    if not 0.1 <= render_scale <= 1.0:
        raise ValueError("BAMO_RENDER_SCALE must be between 0.1 and 1.0")
    fps = int(os.getenv("BAMO_RENDER_FPS", str(fps)))
    if fps < 1 or fps > 60:
        raise ValueError("BAMO_RENDER_FPS must be between 1 and 60")

    out = Path(output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    scenes = project.get("scenes") or []
    if not scenes:
        raise ValueError("Project must contain scenes")

    total_duration = sum(float(s.get("duration", 4)) for s in scenes)
    if total_duration < 1:
        raise ValueError("Total duration too short")

    engine = _engine_path()
    project_b64 = base64.b64encode(
        json.dumps(project, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    work = Path(tempfile.mkdtemp(prefix="bamo_html_"))
    frames_dir = work / "frames"
    frames_dir.mkdir()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=render_scale,
            )

            url = engine.as_uri() + f"?project={project_b64}"
            page.goto(url, wait_until="networkidle", timeout=30000)

            page.wait_for_function("() => window.BAMO && window.BAMO.ready === true && window.BAMO.getState().renderer === 'WebGL'", timeout=15000)

            page.evaluate(
                """(proj) => { window.BAMO.loadProject(proj); window.BAMO.play(); }""",
                project,
            )

            n_frames = max(1, int(round(total_duration * fps)))

            for i in range(n_frames):
                t = i / fps
                page.evaluate(f"window.BAMO.seek({t:.4f})")
                page.wait_for_timeout(15)
                frame_path = frames_dir / f"{i:05d}.jpg"
                page.screenshot(path=str(frame_path), type="jpeg", quality=88)

            browser.close()

        _run([
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "%05d.jpg"),
            "-vf", f"scale={width}:{height}:flags=lanczos,format=yuv420p",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-t", f"{total_duration:.3f}",
            "-an",
            str(out),
        ])

        if not out.is_file() or out.stat().st_size < 20000:
            raise RuntimeError("HTML renderer produced empty or tiny MP4")

        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def is_html_renderer_available() -> bool:
    """Quick check whether Playwright + engine are usable."""
    try:
        import playwright  # noqa: F401
        return _engine_path().is_file()
    except Exception:
        return False
