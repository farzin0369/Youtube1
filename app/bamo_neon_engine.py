"""BAMO Neon Motion Engine: CPU renderer for luminous mathematical motion graphics.

Produces deterministic procedural frames: neon curves, particle orbits, additive
bloom, accumulating trails, geometric webs, camera drift and synchronized captions.
It is a specialist visual engine, separate from the existing generic 3D renderer.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageEnhance

SIZES = {
    "short": (720, 1280), "vertical": (720, 1280),
    "long": (1280, 720), "landscape": (1280, 720),
    "square": (1080, 1080),
}
PALETTES = {
    "cyan": ((91, 231, 255), (170, 105, 255), (255, 192, 91)),
    "violet": ((183, 127, 255), (90, 224, 255), (255, 119, 190)),
    "gold": ((255, 204, 105), (255, 125, 96), (120, 220, 255)),
    "emerald": ((91, 245, 190), (105, 175, 255), (255, 205, 115)),
}

def validate(project: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(project, dict) or not isinstance(project.get("scenes"), list) or not project["scenes"]:
        raise ValueError("Project requires a non-empty scenes array")
    fmt = str(project.get("format", "short")).lower()
    if fmt not in SIZES:
        raise ValueError(f"Unsupported format: {fmt}")
    fps = int(project.get("fps", 30))
    if fps not in (24, 25, 30):
        raise ValueError("fps must be 24, 25 or 30")
    scenes = []
    for i, raw in enumerate(project["scenes"], 1):
        if not isinstance(raw, dict):
            raise ValueError(f"Scene {i} must be an object")
        duration = float(raw.get("duration", 5))
        if not math.isfinite(duration) or not 1 <= duration <= 60:
            raise ValueError(f"Scene {i} duration must be between 1 and 60 seconds")
        palette = str(raw.get("palette", "cyan")).lower()
        if palette not in PALETTES:
            raise ValueError(f"Scene {i} has unknown palette: {palette}")
        scenes.append({
            "duration": duration,
            "text": str(raw.get("text", raw.get("on_screen_text", ""))).strip(),
            "narration": str(raw.get("narration", "")).strip(),
            "motif": str(raw.get("motif", "ellipse_mesh")).lower(),
            "palette": palette,
            "phase": str(raw.get("phase", "auto")).lower(),
            "camera": str(raw.get("camera", "slow_orbit")).lower(),
            "visual_brief": str(raw.get("visual_brief", "")).strip(),
        })
    return {"format": fmt, "fps": fps, "scenes": scenes}


def _point(cx: float, cy: float, rx: float, ry: float, angle: float, zoom: float, drift: float):
    x = rx * math.cos(angle)
    y = ry * math.sin(angle)
    c, s = math.cos(drift), math.sin(drift)
    return (cx + zoom * (x*c - y*s), cy + zoom * (x*s + y*c))


def _draw_glow(canvas: Image.Image, layer: Image.Image, blur: int = 18, gain: float = 1.5):
    halo = layer.filter(ImageFilter.GaussianBlur(blur))
    halo = ImageEnhance.Brightness(halo).enhance(gain)
    canvas.alpha_composite(halo)
    canvas.alpha_composite(layer)


def _render_scene(pipe, scene: dict[str, Any], duration: float, fps: int,
                  width: int, height: int, scene_index: int):
    # Render at 2/3 target dimensions, then let FFmpeg upscale with Lanczos.
    w, h = max(320, width * 2 // 3), max(568, height * 2 // 3)
    cx, cy = w / 2, h / 2
    scale = min(w, h) * .52
    cyan, violet, gold = PALETTES[scene["palette"]]
    motif = scene["motif"]
    trail = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    total = max(1, round(duration * fps))
    for frame in range(total):
        t = frame / fps
        p = frame / max(1, total - 1)
        drift = .10 * math.sin(t * .23) + .035 * math.sin(t * .61)
        zoom = 1 + .055 * math.sin(t * .28)
        if scene["camera"] == "push_in":
            zoom *= 1 + .10 * p
        elif scene["camera"] == "orbit":
            drift += .12 * p
        bg = Image.new("RGBA", (w, h), (3, 5, 17, 255))
        # Subtle star field gives depth without becoming generic stock footage.
        stars = ImageDraw.Draw(bg, "RGBA")
        for k in range(44):
            sx = (k * 97 + int(t * (5 + k % 5))) % w
            sy = (k * 173 + int(t * (3 + k % 7))) % h
            stars.ellipse((sx, sy, sx + 1.5, sy + 1.5), fill=(120, 170, 220, 60))
        fresh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(fresh, "RGBA")
        rx, ry = scale * .78, scale * 1.05
        # Main luminous ellipse / orbit.
        ellipse_pts = [_point(cx, cy, rx, ry, q * math.tau / 240, zoom, drift)
                       for q in range(241)]
        d.line(ellipse_pts, fill=(*cyan, 230), width=max(2, w // 260), joint="curve")
        # Fine inner orbit and anchor points.
        for ring in (0.72, 0.88):
            pts = [_point(cx, cy, rx*ring, ry*ring, q*math.tau/180, zoom, drift)
                   for q in range(181)]
            d.line(pts, fill=(*violet, 48), width=1)
        # Moving points and their accumulating trajectories.
        count = 7 if p < .24 else 12
        nodes = []
        for k in range(count):
            phase = t * (.48 + .055*k) + k * math.tau / count
            a = phase + .18 * math.sin(t * .7 + k)
            px, py = _point(cx, cy, rx*.84, ry*.84, a, zoom, drift)
            nodes.append((px, py))
            color = cyan if k % 3 == 0 else (violet if k % 3 == 1 else gold)
            r = max(4, w // 105)
            d.ellipse((px-r*2, py-r*2, px+r*2, py+r*2), fill=(*color, 35))
            d.ellipse((px-r, py-r, px+r, py+r), fill=(*color, 255))
            d.ellipse((px-r*.35, py-r*.35, px+r*.35, py+r*.35), fill=(255,255,255,255))
        # Stage progression: sparse rays -> connected geometry -> dense mesh -> light burst.
        stage = min(3, int(p * 4))
        if motif in ("ellipse_mesh", "neon_geometry", "geometry", "number_theory"):
            pairs = []
            if stage == 0:
                pairs = [(0, 3), (1, 4)]
            elif stage == 1:
                pairs = [(i, (i+2) % count) for i in range(count)]
            else:
                pairs = [(i, j) for i in range(count) for j in range(i+1, count)
                         if (j-i) <= (3 if stage == 2 else 5)]
            for i, j in pairs:
                alpha = 105 if stage < 2 else 145
                d.line((nodes[i], nodes[j]), fill=(*violet, alpha), width=max(1, w//500))
            if stage >= 2:
                # Radiating chords converge on a moving focus.
                focus = _point(cx, cy, rx*.22, ry*.22, -t*.7, zoom, drift)
                for pt in nodes:
                    d.line((pt, focus), fill=(*cyan, 120), width=1)
        elif motif in ("wave", "interference"):
            wave = []
            for q in range(240):
                x = w*.12 + q*w*.76/239
                u = q/239*math.tau*2.5
                y = cy + math.sin(u-t*2.3)*scale*.28 + math.sin(u*2.0+t)*scale*.10
                wave.append((x,y))
            d.line(wave, fill=(*cyan,235), width=max(2,w//300))
            for q in range(0,240,12):
                d.line((wave[q], (wave[q][0],cy)), fill=(*violet,95), width=1)
        elif motif in ("atom", "molecule"):
            for tilt in (0, math.pi/3, -math.pi/3):
                pts=[]
                for q in range(181):
                    a=q*math.tau/180+t*.35
                    x,y=_point(cx,cy,scale*.62,scale*.25,a,zoom,tilt)
                    pts.append((x,y))
                d.line(pts,fill=(*cyan,190),width=max(2,w//320))
        elif motif in ("radial", "burst", "sun"):
            for q in range(64):
                a=q*math.tau/64+t*.18
                x,y=_point(cx,cy,scale*.92,scale*.92,a,zoom,0)
                d.line((cx,cy,x,y),fill=(*gold,110),width=1)
        # Bright radial event at the climax, with multi-layer additive glow.
        if p > .68:
            burst = min(1.0, (p-.68)/.22)
            focus = _point(cx, cy, rx*.30, ry*.30, -t*.8, zoom, drift)
            for k in range(36):
                a=k*math.tau/36+t*.12
                length=scale*(.18+.62*burst)
                end=(focus[0]+math.cos(a)*length, focus[1]+math.sin(a)*length)
                d.line((focus,end),fill=(*gold, int(35+130*burst)),width=max(1,w//420))
        # Cumulative trails decay slowly, so motion leaves a luminous memory.
        trail = Image.blend(trail, fresh, .18)
        frame_img = bg
        _draw_glow(frame_img, trail, blur=max(12,w//28), gain=2.15)
        _draw_glow(frame_img, fresh, blur=max(4,w//70), gain=1.45)
        # Soft vignette.
        mask = Image.new("L", (w,h), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse((-w*.18,-h*.08,w*1.18,h*1.08), fill=210)
        mask = ImageChops.invert(mask).filter(ImageFilter.GaussianBlur(max(20,w//12)))
        shade = Image.new("RGBA",(w,h),(0,0,0,0))
        shade.putalpha(mask.point(lambda v: int(v*.62)))
        frame_img.alpha_composite(shade)
        rgb = frame_img.convert("RGB").resize((width,height),Image.Resampling.LANCZOS)
        pipe.stdin.write(rgb.tobytes())


def _write_captions(scenes: list[dict[str, Any]], path: Path, width: int, height: int):
    font = max(30, int(width * .052))
    brand = max(18, int(width * .026))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Noto Naskh Arabic,{font},&H00FFFFFF,&H000000FF,&HCC070B18,&HBB080D1B,1,0,0,0,100,100,0,0,3,10,1,8,48,48,54,1
Style: Brand,Noto Sans,{brand},&H00D7C8FF,&H000000FF,&HAA050817,&H00000000,1,0,0,0,100,100,1,0,1,2,1,2,20,20,36,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def stamp(seconds: float) -> str:
        n = max(0, round(seconds * 100))
        hh, rem = divmod(n, 360000)
        mm, rem = divmod(rem, 6000)
        ss, cc = divmod(rem, 100)
        return f"{hh}:{mm:02d}:{ss:02d}.{cc:02d}"
    events = []
    cursor = 0.0
    for scene in scenes:
        end = cursor + scene["duration"]
        text = scene["text"].replace("\\", r"\\").replace("{", r"\\{").replace("}", r"\\}").replace("\n", r"\\N")
        if text:
            events.append(f"Dialogue: 0,{stamp(cursor+.12)},{stamp(end-.12)},Caption,,0,0,0,,{{\\fad(180,180)}}{text}")
            events.append(f"Dialogue: 1,{stamp(cursor+.12)},{stamp(end-.12)},Brand,,0,0,0,,BAMO  •  #12bamo")
        cursor = end
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def render_project(project: dict[str, Any], output: str | Path,
                   audio: str | Path | None = None) -> Path:
    spec = validate(project)
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required")
    out = Path(output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = SIZES[spec["format"]]
    fps = spec["fps"]
    work = out.parent / f".{out.stem}_neon"
    work.mkdir(parents=True, exist_ok=True)
    silent = work / "silent.mp4"
    cmd = ["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{width}x{height}",
           "-r",str(fps),"-i","-","-an","-c:v","libx264","-preset","ultrafast",
           "-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",str(silent)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert proc.stdin is not None
        for i, scene in enumerate(spec["scenes"]):
            _render_scene(proc, scene, scene["duration"], fps, width, height, i)
        proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        code = proc.wait(timeout=1800)
        if code:
            raise RuntimeError(f"FFmpeg encoding failed: {stderr[-2500:]}")
    except Exception:
        proc.kill()
        proc.wait()
        raise
    # Captions are generated from the same scene timeline; audio is muxed without
    # stretching or silently changing narration timing.
    ass = work / "captions.ass"
    _write_captions(spec["scenes"], ass, width, height)
    final_cmd = ["ffmpeg","-y","-i",str(silent)]
    audio_path = Path(audio).expanduser().resolve() if audio else None
    if audio_path:
        if not audio_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        final_cmd += ["-i",str(audio_path),"-map","0:v:0","-map","1:a:0",
                      "-vf",f"ass={ass.as_posix()}","-c:a","aac","-b:a","192k","-shortest"]
    else:
        final_cmd += ["-vf",f"ass={ass.as_posix()}","-an"]
    final_cmd += ["-c:v","libx264","-preset","veryfast","-crf","19",
                  "-pix_fmt","yuv420p","-movflags","+faststart",str(out)]
    result = subprocess.run(final_cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode:
        raise RuntimeError(f"Final mux failed: {result.stderr[-2500:]}")
    if not out.is_file() or out.stat().st_size < 10_000:
        raise RuntimeError("Output MP4 is missing or unexpectedly small")
    return out


def load_project(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Render BAMO neon mathematical motion graphics on CPU")
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audio")
    args = parser.parse_args()
    result = render_project(load_project(args.project), args.output, args.audio)
    print(f"RENDER_OK: {result} ({result.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
