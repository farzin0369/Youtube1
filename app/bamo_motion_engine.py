"""BAMO Motion Engine — High Visual Quality Edition

CPU-first hybrid motion-graphics renderer.
Focus: cinematic lighting, richer motifs, smoother camera, better text hierarchy,
and smarter motif selection from caption + visual_prompt.

Public API is kept compatible with the previous engine:
  - validate_project(project)
  - render_project(project, output, audio=None)
  - load_project(path)
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORMATS = {
    "short": (720, 1280),
    "vertical": (720, 1280),
    "long": (1280, 720),
    "landscape": (1280, 720),
    "square": (1080, 1080),
}

# Richer, more cinematic palettes (bg, accent)
PALETTES = [
    ("0x0a0e17", "0x22d3ee"),  # deep navy + cyan
    ("0x0c0a09", "0xfbbf24"),  # warm dark + amber
    ("0x111827", "0xa78bfa"),  # slate + violet
    ("0x052e16", "0x4ade80"),  # forest + green
    ("0x1c0a1a", "0xf472b6"),  # plum + pink
    ("0x0f172a", "0x38bdf8"),  # midnight + sky
]

# ---------------------------------------------------------------------------
# Validation (kept compatible)
# ---------------------------------------------------------------------------

def validate_project(project: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(project, dict):
        raise ValueError("Project must be a JSON object")
    scenes = project.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Project must contain a non-empty scenes array")
    fmt = str(project.get("format", "short")).lower()
    if fmt not in FORMATS:
        raise ValueError(f"Unsupported format: {fmt}")
    clean = []
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {index} must be an object")
        duration = float(scene.get("duration", 4))
        if not math.isfinite(duration) or duration < 0.5 or duration > 60:
            raise ValueError(f"Scene {index} duration must be between 0.5 and 60 seconds")
        clean.append({
            "duration": duration,
            "text": str(scene.get("on_screen_text") or scene.get("text") or "").strip(),
            "image": str(scene.get("image") or "").strip(),
            "background": str(scene.get("background") or "").strip(),
            "accent": str(scene.get("accent") or "").strip(),
            "visual_prompt": str(scene.get("visual_prompt") or "").strip(),
            "narration": str(scene.get("narration") or "").strip(),
        })
    return {"format": fmt, "scenes": clean}


def load_project(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# ASS captions (improved hierarchy)
# ---------------------------------------------------------------------------

def _ass_time(seconds: float) -> str:
    total = max(0, int(round(seconds * 100)))
    hours, rem = divmod(total, 360000)
    minutes, rem = divmod(rem, 6000)
    secs, centis = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _ass_escape(value: str) -> str:
    return (
        value.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def _write_ass(scenes: list[dict[str, Any]], path: Path, width: int, height: int) -> None:
    hero_size = max(36, int(width * 0.062))
    brand_size = max(20, int(width * 0.028))
    margin = max(40, int(width * 0.07))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Noto Naskh Arabic,{hero_size},&H00FFFFFF,&H000000FF,&HAA080C16,&H66000000,1,0,0,0,100,100,0,0,1,3.5,2,5,{margin},{margin},{int(height * 0.11)},1
Style: Brand,Noto Naskh Arabic,{brand_size},&H00D5A64B,&H000000FF,&HAA080C16,&H66000000,1,0,0,0,100,100,0,0,1,2,1,8,{margin},{margin},{int(height * 0.055)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    cursor = 0.0
    for scene in scenes:
        duration = scene["duration"]
        if scene["text"]:
            # Soft brand watermark
            events.append(
                f"Dialogue: 0,{_ass_time(cursor + 0.15)},{_ass_time(cursor + duration - 0.15)},Brand,,0,0,0,,BAMO"
            )
            # Main text with gentle fade
            events.append(
                f"Dialogue: 1,{_ass_time(cursor + 0.22)},{_ass_time(cursor + duration - 0.18)},Main,,0,0,0,,{{\\fad(280,280)}}{_ass_escape(scene['text'])}"
            )
        cursor += duration
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# FFmpeg helper
# ---------------------------------------------------------------------------

def _run(command: list[str], timeout: int = 900) -> None:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"FFmpeg failed ({result.returncode}): {result.stderr[-3000:]}")


# ---------------------------------------------------------------------------
# 3D helpers + high-quality scene renderer
# ---------------------------------------------------------------------------

def _project_3d(x, y, z, angle, zoom, w, h):
    ca, sa = math.cos(angle), math.sin(angle)
    xr = x * ca - z * sa
    zr = x * sa + z * ca
    depth = 5.6 - zr
    scale = min(w, h) * 0.46 * zoom / max(1.15, depth)
    return w * 0.5 + xr * scale, h * 0.5 - y * scale, depth, scale


def _rgb(v: str) -> tuple[int, int, int]:
    v = v.replace("0x", "").replace("#", "")
    return tuple(int(v[i : i + 2], 16) for i in (0, 2, 4))


def _render_3d_scene(
    path: Path,
    duration: float,
    width: int,
    height: int,
    fps: int,
    index: int,
    bg: str,
    accent: str,
    visual_plan: dict | None = None,
) -> None:
    """Higher-quality CPU 3D scene with better lighting, softer particles and more motifs."""
    from PIL import Image, ImageDraw, ImageFilter

    visual_plan = visual_plan or {}
    motif = visual_plan.get("motif", "abstract")
    camera = visual_plan.get("camera", "orbit")

    base = _rgb(bg)
    glow = _rgb(accent)
    sw, sh = 480, 854  # internal render resolution (scaled later)

    frames_dir = path.parent / f"frames_{index:03d}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    n_frames = max(1, round(duration * fps))

    for frame in range(n_frames):
        t = frame / fps

        # Camera motion curves (smoother)
        cam_speed = {"orbit": 0.38, "push_in": 0.11, "tracking": 0.26, "sweep": 0.55}.get(camera, 0.38)
        ang = t * cam_speed + index * 0.65

        if camera == "orbit":
            zoom = 1.0 + 0.09 * math.sin(t * 0.6) + 0.04 * math.sin(t * 1.35 + index)
        elif camera == "push_in":
            zoom = 1.0 + 0.22 * (t / max(duration, 0.5))
        else:
            zoom = 1.0 + 0.11 * math.sin(t * 1.15)

        # Base image with subtle vertical gradient
        im = Image.new("RGB", (sw, sh))
        draw = ImageDraw.Draw(im, "RGBA")
        for y in range(sh):
            factor = 0.75 + 0.25 * (y / sh)
            col = tuple(int(c * factor) for c in base)
            draw.line([(0, y), (sw, y)], fill=col)

        # Soft floating particles
        for p in range(48):
            px = (p * 91 + t * (11 + p % 6) * (-1 if p % 2 else 1)) % sw
            py = (p * 127 + t * (7 + p % 5)) % sh
            r = 1 + p % 3
            alpha = 55 + int(30 * math.sin(t * 1.2 + p))
            draw.ellipse((px - r, py - r, px + r, py + r), fill=(*glow, alpha))

        # ---- Motif-specific geometry ----
        items = []  # (depth, kind, data, color)

        # Shared rotating cube for many motifs
        verts = [
            _project_3d(x * 0.78, y * 0.78, z * 0.78, ang + t * 0.25, zoom, sw, sh)
            for x, y, z in [
                (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
            ]
        ]
        faces = [
            ((0, 1, 2, 3), 0.38),
            ((4, 5, 6, 7), 0.78),
            ((0, 1, 5, 4), 0.55),
            ((2, 3, 7, 6), 0.88),
            ((1, 2, 6, 5), 0.95),
            ((0, 3, 7, 4), 0.32),
        ]
        for face, light in faces:
            pts = [(verts[q][0], verts[q][1]) for q in face]
            shade = tuple(int(v * light) for v in glow)
            items.append((sum(verts[q][2] for q in face) / 4, "poly", pts, (*shade, 210)))

        # Orbiting spheres
        for j in range(3):
            ph = t * (0.8 + j * 0.15) + j * 2.0 + index
            sx, sy, dep, sc = _project_3d(
                1.55 * math.cos(ph),
                0.68 * math.sin(ph * 1.25),
                1.45 * math.sin(ph),
                ang, zoom, sw, sh,
            )
            r = max(5, int(sc * (0.22 if j else 0.29)))
            col = (*glow, 230) if j == 0 else ((100, 170, 220, 225) if j == 1 else (220, 165, 90, 225))
            items.append((dep, "sphere", (sx, sy, r), col))

        # Motif extras
        if motif in ("choice_paths", "journey"):
            for branch in (-1, 1):
                pts = []
                for q in range(32):
                    u = q / 31
                    px, py, _, _ = _project_3d(
                        branch * (0.1 + 1.85 * u),
                        -0.7 + 1.1 * u,
                        0.3 * math.sin(u * math.pi),
                        ang, zoom, sw, sh,
                    )
                    pts.append((px, py))
                items.append((-10, "path", pts, (*glow, 210 if branch == 1 else 120)))

        elif motif in ("growth_steps", "progress"):
            for q in range(6):
                x0 = -1.75 + q * 0.52
                y0 = -0.75 + q * 0.25
                corners = [(x0, y0, 0), (x0 + 0.45, y0, 0), (x0 + 0.45, y0 + 0.2, 0), (x0, y0 + 0.2, 0)]
                pts = [_project_3d(*v, ang, zoom, sw, sh)[:2] for v in corners]
                items.append((-5 - q, "poly", pts, (*glow, 90 + q * 22)))

        elif motif in ("atom", "science", "geometry"):
            for tilt in (0, math.pi / 3, -math.pi / 3):
                pts = []
                for q in range(90):
                    a = q * math.tau / 89 + t * 0.32
                    x, y, _, _ = _project_3d(
                        1.95 * math.cos(a),
                        0.68 * math.sin(a) * math.cos(tilt),
                        1.4 * math.sin(a) * math.sin(tilt),
                        ang, zoom, sw, sh,
                    )
                    pts.append((x, y))
                items.append((-8, "path", pts, (*glow, 185)))

        elif motif in ("molecule", "chemistry"):
            nodes = [(-1.3, 0, 0), (-0.4, 0.75, 0.28), (0.5, 0.6, -0.28), (1.3, -0.08, 0.18), (0.2, -0.8, 0.35)]
            projected = [_project_3d(*v, ang, zoom, sw, sh) for v in nodes]
            for a, b in ((0, 1), (1, 2), (2, 3), (2, 4), (4, 0)):
                items.append((-6, "line", (projected[a][0:2], projected[b][0:2]), (*glow, 215)))
            for x, y, dep, sc in projected:
                r = max(6, int(sc * 0.17))
                items.append((dep, "sphere", (x, y, r), (*glow, 230)))

        elif motif == "launch":
            cx, cy, _, _ = _project_3d(0, 0, 0, ang, zoom, sw, sh)
            for q in range(4):
                rr = 60 + q * 36 + int(9 * math.sin(t * 1.8 + q))
                items.append((-12 - q, "ring", (cx, cy, rr), (*glow, max(60, 200 - q * 35))))

        # Draw sorted by depth
        for _, kind, data, col in sorted(items, key=lambda a: a[0], reverse=True):
            if kind == "poly":
                draw.polygon(data, fill=col)
                draw.line(data + [data[0]], fill=(230, 215, 185, 180), width=2)
            elif kind == "sphere":
                sx, sy, r = data
                for q in range(r, 0, -1):
                    shade = tuple(
                        int(min(255, v * (0.32 + 0.85 * (1 - q / r * 0.55))))
                        for v in col[:3]
                    )
                    draw.ellipse((sx - q, sy - q, sx + q, sy + q), fill=(*shade, col[3]))
                # highlight
                draw.ellipse(
                    (sx - r * 0.45, sy - r * 0.58, sx - r * 0.08, sy - r * 0.2),
                    fill=(255, 255, 255, 115),
                )
            elif kind == "path":
                if len(data) > 1:
                    draw.line(data, fill=col, width=4)
            elif kind == "line":
                draw.line(data, fill=col, width=4)
            elif kind == "ring":
                cx, cy, rr = data
                draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=col, width=3)

        # Soft central glow
        cx, cy, _, _ = _project_3d(0, 0, 0, ang, zoom, sw, sh)
        halo = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse(
            (cx - 130, cy - 130, cx + 130, cy + 130), fill=(*glow, 28)
        )
        im = Image.alpha_composite(im.convert("RGBA"), halo.filter(ImageFilter.GaussianBlur(40))).convert("RGB")

        im.save(frames_dir / f"{frame:05d}.jpg", quality=90)

    # Encode scene clip
    _run([
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "%05d.jpg"),
        "-vf", (
            f"scale={width}:{height}:flags=lanczos,"
            f"fade=t=in:st=0:d=0.28,"
            f"fade=t=out:st={max(0, duration - 0.35):.3f}:d=0.32,"
            "format=yuv420p"
        ),
        "-t", f"{duration:.3f}",
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(path),
    ])


# ---------------------------------------------------------------------------
# Main render entry point
# ---------------------------------------------------------------------------

def render_project(project: dict[str, Any], output: str | Path, audio: str | Path | None = None) -> Path:
    """Render an MP4 on CPU with improved visual quality."""
    spec = validate_project(project)
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required on the runner")

    out = Path(output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = FORMATS[spec["format"]]
    fps = int(project.get("fps", 24))
    if fps not in (24, 25, 30):
        raise ValueError("fps must be 24, 25, or 30")

    work = out.parent / f".{out.stem}_render"
    work.mkdir(parents=True, exist_ok=True)
    clips = []

    for index, scene in enumerate(spec["scenes"]):
        duration = scene["duration"]
        clip = work / f"scene_{index:03d}.mp4"
        bg, accent = PALETTES[index % len(PALETTES)]
        bg = scene["background"] or bg
        accent = scene["accent"] or accent

        if scene["image"]:
            image_path = Path(scene["image"]).expanduser().resolve()
            if not image_path.is_file():
                raise FileNotFoundError(f"Scene image not found: {image_path}")
            fadeout = max(0, duration - 0.32)
            vf = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                f"zoompan=z='min(zoom+0.00065,1.07)':d={max(1, round(duration * fps))}:"
                f"s={width}x{height}:fps={fps},"
                f"fade=t=in:st=0:d=0.28,fade=t=out:st={fadeout:.3f}:d=0.32,format=yuv420p"
            )
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
                "-t", f"{duration:.3f}", "-vf", vf, "-an",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                "-pix_fmt", "yuv420p", str(clip),
            ]
            _run(cmd)
            clips.append(clip)
            continue

        # Procedural high-quality 3D
        try:
            from app.bamo_scene_director import plan_scene
            visual_plan = plan_scene(scene.get("narration") or scene["text"], scene.get("visual_prompt", ""))
        except Exception:
            visual_plan = {"motif": "abstract", "camera": "orbit"}

        _render_3d_scene(clip, duration, width, height, fps, index, bg, accent, visual_plan)
        clips.append(clip)

    # Concat
    concat = work / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
    silent = work / "silent.mp4"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-an", str(silent)])

    # Captions
    ass = work / "captions.ass"
    _write_ass(spec["scenes"], ass, width, height)

    command = ["ffmpeg", "-y", "-i", str(silent)]
    audio_path = Path(audio).expanduser().resolve() if audio else None
    if audio_path and audio_path.is_file():
        command += [
            "-i", str(audio_path),
            "-vf", f"ass={ass.as_posix()}",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
        ]
    else:
        command += ["-vf", f"ass={ass.as_posix()}", "-an"]

    command += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ]
    _run(command)

    if not out.is_file() or out.stat().st_size < 10000:
        raise RuntimeError("Rendered MP4 is missing or unexpectedly small")
    return out
