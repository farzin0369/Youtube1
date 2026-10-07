"""Render slides + audio + captions + thumbnail."""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.utils import OUTPUT_DIR, split_sentences


def _font(size: int):
    for c in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_thumbnail(title: str, out_path: Path, kind: str) -> Path:
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), (18, 32, 48))
    draw = ImageDraw.Draw(img)
    for i in range(h):
        draw.line([(0, i), (w, i)], fill=(min(18 + i // 50, 40), min(32 + i // 40, 60), min(48 + i // 30, 80)))
    draw.rectangle([40, 40, w - 40, h - 40], outline=(200, 180, 120), width=3)
    title_font, sub_font = _font(48), _font(28)
    y = 220
    for line in textwrap.fill(title, width=28).split("\n"):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        draw.text(((w - (bbox[2] - bbox[0])) / 2, y), line, fill=(240, 230, 200), font=title_font)
        y += 60
    draw.text((60, h - 100), "شورت" if kind == "short" else "ویدیو", fill=(200, 180, 120), font=sub_font)
    draw.text((w - 320, h - 100), "imamali.110", fill=(180, 170, 150), font=sub_font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=92)
    return out_path


def make_slide_image(text: str) -> Image.Image:
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), (12, 24, 36))
    draw = ImageDraw.Draw(img)
    for i in range(h):
        draw.line([(0, i), (w, i)], fill=(12 + i // 40, 24 + i // 35, 36 + i // 30))
    draw.rectangle([30, 30, w - 30, h - 30], outline=(180, 160, 100), width=2)
    font = _font(40)
    lines = []
    for para in text.split("\n"):
        lines.extend(textwrap.wrap(para, width=32) or [""])
    lines = lines[:10]
    y = max(80, (h - len(lines) * 52) // 2)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text(((w - (bbox[2] - bbox[0])) / 2, y), line, fill=(235, 225, 200), font=font)
        y += 52
    return img


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
        from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips

        audio = AudioFileClip(str(audio_path))
        duration = float(audio.duration) if audio.duration else (45.0 if kind == "short" else 300.0)
        write_srt(script, srt_path, duration)
        sentences = (split_sentences(script) or [script[:150]])[: (8 if kind == "short" else 16)]
        slot = duration / max(len(sentences), 1)
        clips = []
        for sent in sentences:
            img_path = out_dir / f"slide_{len(clips):03d}.png"
            make_slide_image(sent).save(img_path)
            clips.append(ImageClip(str(img_path)).set_duration(slot))
        if not clips:
            img_path = out_dir / "slide_000.png"
            make_slide_image(title).save(img_path)
            clips = [ImageClip(str(img_path)).set_duration(duration)]
        video = concatenate_videoclips(clips, method="compose").set_audio(audio).set_duration(duration)
        video.write_videofile(str(video_path), fps=24, codec="libx264", audio_codec="aac", threads=2, logger=None)
        audio.close()
        video.close()
        return {"video_path": str(video_path), "thumbnail_path": str(thumb), "captions_path": str(srt_path), "duration": duration, "ok": True}
    except Exception as e:
        print(f"[video] failed: {e}")
        write_srt(script, srt_path, 45.0 if kind == "short" else 300.0)
        return {"video_path": None, "thumbnail_path": str(thumb), "captions_path": str(srt_path), "ok": False, "error": str(e)}
