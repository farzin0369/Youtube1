"""Cinematic spiritual video: slow Ken Burns, gold light, soft captions — not static slides."""
from __future__ import annotations

import math
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.utils import OUTPUT_DIR, split_sentences

W, H = 1280, 720
FPS = 24


def _font(size: int):
    for c in [
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _cinematic_frame(t: float, duration: float, seed: int = 7) -> Image.Image:
    """Procedural cinematic background: deep teal, gold haze, slow drift."""
    img = Image.new("RGB", (W, H))
    px = img.load()
    # slow phase for living motion
    phase = t * 0.15
    for y in range(H):
        for x in range(0, W, 2):  # step 2 for speed; fill neighbor
            nx = x / W + 0.02 * math.sin(phase + y * 0.01)
            ny = y / H + 0.015 * math.cos(phase * 0.8 + x * 0.008)
            # base night teal
            r = int(8 + 18 * ny + 12 * math.sin(nx * 3 + phase))
            g = int(16 + 28 * ny + 10 * math.cos(ny * 2 - phase))
            b = int(28 + 40 * (1 - ny) + 15 * math.sin(phase + nx))
            # gold light pool upper-center
            cx, cy = 0.5 + 0.05 * math.sin(phase * 0.5), 0.35
            d = math.hypot(nx - cx, ny - cy)
            glow = max(0.0, 1.0 - d * 2.2)
            r = min(255, int(r + glow * 90))
            g = min(255, int(g + glow * 70))
            b = min(255, int(b + glow * 25))
            # vignette
            vig = 1.0 - 0.45 * ((nx - 0.5) ** 2 + (ny - 0.5) ** 2) * 4
            r, g, b = int(r * vig), int(g * vig), int(b * vig)
            px[x, y] = (r, g, b)
            if x + 1 < W:
                px[x + 1, y] = (r, g, b)
    # soft blur for filmic look
    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    draw = ImageDraw.Draw(img, "RGBA")
    # thin gold frame
    draw.rectangle([36, 36, W - 36, H - 36], outline=(200, 175, 110, 160), width=2)
    return img.convert("RGB")


def _caption_overlay(text: str, alpha: float = 1.0) -> Image.Image:
    """Semi-transparent lower-third style caption board."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # soft bottom bar
    bar_h = 160
    for i in range(bar_h):
        a = int(160 * (i / bar_h) * alpha)
        draw.line([(0, H - bar_h + i), (W, H - bar_h + i)], fill=(5, 10, 18, a))
    font = _font(34)
    lines = []
    for para in text.split("\n"):
        lines.extend(textwrap.wrap(para, width=36) or [""])
    lines = lines[:3]
    y = H - bar_h + 36
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        # shadow
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0, int(200 * alpha)), font=font)
        draw.text((x, y), line, fill=(245, 235, 210, int(255 * alpha)), font=font)
        y += 42
    return overlay


def make_thumbnail(title: str, out_path: Path, kind: str) -> Path:
    base = _cinematic_frame(2.5, 10.0)
    base = base.convert("RGBA")
    draw = ImageDraw.Draw(base)
    draw.rectangle([40, 40, W - 40, H - 40], outline=(210, 185, 120, 220), width=3)
    title_font, sub = _font(46), _font(26)
    y = 240
    for line in textwrap.fill(title, width=26).split("\n"):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 180), font=title_font)
        draw.text((x, y), line, fill=(245, 235, 210, 255), font=title_font)
        y += 58
    draw.text((60, H - 90), "شورت" if kind == "short" else "ویدیو", fill=(200, 180, 120, 230), font=sub)
    draw.text((W - 300, H - 90), "imamali.110", fill=(180, 170, 150, 230), font=sub)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out_path, quality=93)
    return out_path


def write_srt(script: str, out_path: Path, total_duration: float) -> Path:
    sentences = split_sentences(script) or [script[:200]]
    slot = max(total_duration / len(sentences), 1.5)

    def ts(sec: float) -> str:
        h, m = int(sec // 3600), int((sec % 3600) // 60)
        s, ms = int(sec % 60), int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, sent in enumerate(sentences):
        start, end = i * slot, min((i + 1) * slot, total_duration)
        lines += [str(i + 1), f"{ts(start)} --> {ts(end)}", sent[:180], ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def render_video(script: str, audio_path: Path, title: str, kind: str, run_id: str) -> dict[str, Any]:
    out_dir = OUTPUT_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    thumb = make_thumbnail(title, out_dir / "thumbnail.jpg", kind)
    srt_path = out_dir / "captions.srt"
    video_path = out_dir / "video.mp4"
    audio_path = Path(audio_path)

    try:
        from moviepy.editor import AudioFileClip, VideoClip

        audio = AudioFileClip(str(audio_path))
        duration = float(audio.duration) if audio.duration else (45.0 if kind == "short" else 300.0)
        # cap long renders on CI
        if kind == "long":
            duration = min(duration, 420.0)
        else:
            duration = min(duration, 60.0)

        write_srt(script, srt_path, duration)
        sentences = split_sentences(script) or [script[:120]]
        n = len(sentences)
        slot = duration / max(n, 1)

        # Pre-render a few key background stills and crossfade via time
        # Full per-pixel every frame is too slow; sample backgrounds sparsely + interpolate feel via phase
        cache: dict[int, Image.Image] = {}

        def bg_at(t: float) -> Image.Image:
            key = int(t * 2)  # 2 samples/sec worth of distinct frames
            if key not in cache:
                cache[key] = _cinematic_frame(t, duration)
                # keep cache small
                if len(cache) > 40:
                    cache.pop(next(iter(cache)))
            return cache[key]

        def make_frame(t: float):
            base = bg_at(t).convert("RGBA")
            # which caption
            idx = min(int(t / slot), n - 1)
            # fade caption in/out within slot
            local = t - idx * slot
            fade = 0.35
            if local < fade:
                a = local / fade
            elif local > slot - fade:
                a = max(0.0, (slot - local) / fade)
            else:
                a = 1.0
            cap = _caption_overlay(sentences[idx], alpha=a)
            composed = Image.alpha_composite(base, cap).convert("RGB")
            return np.array(composed)

        video = VideoClip(make_frame, duration=duration).set_fps(FPS).set_audio(audio)
        video.write_videofile(
            str(video_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=2,
            logger=None,
        )
        audio.close()
        video.close()
        return {
            "video_path": str(video_path),
            "thumbnail_path": str(thumb),
            "captions_path": str(srt_path),
            "duration": duration,
            "style": "cinematic_kenburns_caption",
            "ok": True,
        }
    except Exception as e:
        print(f"[video] cinematic render failed: {e}")
        write_srt(script, srt_path, 45.0 if kind == "short" else 300.0)
        return {
            "video_path": None,
            "thumbnail_path": str(thumb),
            "captions_path": str(srt_path),
            "ok": False,
            "error": str(e),
        }
