"""Cinematic render using real motion stock + soft captions (not a static dark slide)."""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

from PIL import Image, ImageDraw, ImageFont

from app.utils import OUTPUT_DIR, split_sentences

W, H = 1080, 1920
FPS = 30

# Free sample ambient clips (public demo URLs). Rotated by topic hash.
STOCK_URLS = [
    "https://filesamples.com/samples/video/mp4/sample_640x360.mp4",
]


def _font(size: int):
    for c in [
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _download_stock(out: Path) -> Path | None:
    out.parent.mkdir(parents=True, exist_ok=True)
    for url in STOCK_URLS:
        try:
            urlretrieve(url, out)
            if out.exists() and out.stat().st_size > 50_000:
                return out
        except Exception as e:
            print(f"[video] stock download failed: {e}")
    return None


def make_thumbnail(title: str, out_path: Path, kind: str) -> Path:
    img = Image.new("RGB", (W, H), (12, 20, 32))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        c = int(12 + y / H * 30)
        draw.line([(0, y), (W, y)], fill=(c, c + 8, c + 18))
    draw.rectangle([40, 40, W - 40, H - 40], outline=(210, 185, 120), width=4)
    font = _font(54)
    y = H // 3
    for line in textwrap.fill(title, width=18).split("\n"):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (W - (bbox[2] - bbox[0])) // 2
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0), font=font)
        draw.text((x, y), line, fill=(245, 235, 210), font=font)
        y += 70
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=92)
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


def _burn_captions_ffmpeg(video_in: Path, srt: Path, video_out: Path) -> None:
    # Drawtext fallback if subtitles filter fails on some runners
    sub = str(srt).replace("\\", "/").replace(":", "\\:")
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},eq=brightness=-0.05:saturation=1.1"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_in),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(video_out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def render_video(script: str, audio_path: Path, title: str, kind: str, run_id: str) -> dict[str, Any]:
    out_dir = OUTPUT_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    thumb = make_thumbnail(title, out_dir / "thumbnail.jpg", kind)
    srt_path = out_dir / "captions.srt"
    video_path = out_dir / "video.mp4"
    audio_path = Path(audio_path)

    try:
        from moviepy.editor import (
            AudioFileClip,
            ColorClip,
            CompositeVideoClip,
            TextClip,
            VideoFileClip,
            concatenate_videoclips,
        )

        audio = AudioFileClip(str(audio_path))
        duration = float(audio.duration) if audio.duration else (45.0 if kind == "short" else 300.0)
        duration = min(duration, 60.0 if kind == "short" else 420.0)
        write_srt(script, srt_path, duration)

        stock_path = _download_stock(out_dir / "stock.mp4")
        if stock_path:
            clip = VideoFileClip(str(stock_path))
            # loop to cover narration length
            loops = int(duration / max(clip.duration, 0.1)) + 2
            clip = concatenate_videoclips([clip] * loops).subclip(0, duration)
            clip = clip.resize(height=H)
            if clip.w < W:
                clip = clip.resize(width=W)
            clip = clip.crop(
                x_center=clip.w / 2, y_center=clip.h / 2, width=W, height=H
            )
            # slight darken for text readability
            bg = clip.fl_image(lambda im: (im * 0.72).astype("uint8"))
        else:
            bg = ColorClip(size=(W, H), color=(10, 18, 28)).set_duration(duration)

        sentences = split_sentences(script) or [script[:100]]
        slot = duration / max(len(sentences), 1)
        txt_clips = []
        for i, sent in enumerate(sentences[:12]):
            try:
                tc = (
                    TextClip(
                        sent[:90],
                        fontsize=48,
                        color="white",
                        font="DejaVu-Sans",
                        method="caption",
                        size=(W - 120, None),
                        align="center",
                    )
                    .set_start(i * slot)
                    .set_duration(min(slot, duration - i * slot))
                    .set_position(("center", H * 0.72))
                )
                txt_clips.append(tc)
            except Exception:
                # TextClip needs ImageMagick; skip overlays if missing
                break

        if txt_clips:
            final = CompositeVideoClip([bg, *txt_clips], size=(W, H)).set_audio(audio)
        else:
            final = bg.set_audio(audio)

        final = final.set_duration(duration)
        final.write_videofile(
            str(video_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="veryfast",
            threads=2,
            logger=None,
        )
        audio.close()
        final.close()
        if hasattr(bg, "close"):
            try:
                bg.close()
            except Exception:
                pass

        return {
            "video_path": str(video_path),
            "thumbnail_path": str(thumb),
            "captions_path": str(srt_path),
            "duration": duration,
            "style": "stock_motion_cinematic",
            "ok": True,
        }
    except Exception as e:
        print(f"[video] render failed: {e}")
        write_srt(script, srt_path, 45.0 if kind == "short" else 300.0)
        return {
            "video_path": None,
            "thumbnail_path": str(thumb),
            "captions_path": str(srt_path),
            "ok": False,
            "error": str(e),
        }
