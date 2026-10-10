"""Cinematic render using real motion stock + soft captions (not a static dark slide)."""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont

# MoviePy 1.x still calls PIL.Image.ANTIALIAS, removed in Pillow 10.
# Map the legacy name to the equivalent high-quality resampler so the
# existing MoviePy 1.x renderer remains compatible with current Pillow.
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS  # type: ignore[attr-defined]

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
            # Some free sample hosts reject Python's default urllib user-agent with HTTP 403.
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                    "Accept": "video/mp4,video/*;q=0.9,*/*;q=0.8",
                },
            )
            with urlopen(request, timeout=45) as response, out.open("wb") as target:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
            if out.exists() and out.stat().st_size > 50_000:
                return out
            out.unlink(missing_ok=True)
            print(f"[video] stock download returned an empty or tiny file: {url}")
        except Exception as e:
            out.unlink(missing_ok=True)
            print(f"[video] stock download failed for {url}: {e}")
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


def write_srt(script: str, out_path: Path, total_duration: float, scene_plan_path: Path | None = None) -> Path:
    """Write SRT captions; when a scene plan exists, align captions to scene narration."""
    import json

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    segments: list[str] = []
    plan = None
    if scene_plan_path and Path(scene_plan_path).exists():
        try:
            candidate = json.loads(Path(scene_plan_path).read_text(encoding="utf-8"))
            scenes = candidate.get("scenes", []) if isinstance(candidate, dict) else candidate
            if scenes and all(isinstance(s, dict) and str(s.get("spoken_text") or "").strip() for s in scenes):
                plan = scenes
        except (OSError, ValueError, TypeError):
            plan = None

    if plan:
        weights = [max(1, len(str(scene["spoken_text"]))) for scene in plan]
        total_weight = sum(weights)
        cursor = 0.0
        for scene, weight in zip(plan, weights):
            start = cursor
            cursor += total_duration * weight / total_weight
            end = min(total_duration, cursor)
            text = str(scene.get("on_screen_text") or scene["spoken_text"]).strip()
            segments.append(f"{len(segments) + 1}\n{_srt_time(start)} --> {_srt_time(end)}\n{text}\n")
    else:
        from app.utils import split_sentences
        sentences = split_sentences(script) or [script.strip()]
        sentences = [s for s in sentences if s]
        weights = [max(1, len(s)) for s in sentences]
        total_weight = sum(weights) or 1
        cursor = 0.0
        for sentence, weight in zip(sentences, weights):
            start = cursor
            cursor += total_duration * weight / total_weight
            end = min(total_duration, cursor)
            segments.append(f"{len(segments) + 1}\n{_srt_time(start)} --> {_srt_time(end)}\n{sentence}\n")
    out_path.write_text("\n".join(segments), encoding="utf-8")
    return out_path


def _srt_time(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"
def _burn_captions_ffmpeg(video_in: Path, srt: Path, video_out: Path) -> None:
    """Burn the Persian SRT into the rendered video using FFmpeg/libass."""
    escaped_srt = str(Path(srt).resolve()).replace(":", "\\:").replace("'", "\\'")
    subtitle_filter = (
        f"subtitles='{escaped_srt}':"
        "force_style='FontName=Noto Sans Arabic,FontSize=42,Outline=2,"
        "Shadow=1,MarginV=140,Alignment=2'"
    )
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"eq=brightness=-0.05:saturation=1.1,{subtitle_filter}"
    )
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


def render_video(script: str, audio_path: Path, title: str, kind: str, run_id: str, scene_plan_path: Path | None = None) -> dict[str, Any]:
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
        write_srt(script, srt_path, duration, scene_plan_path=scene_plan_path)

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

        caption_items = []
        if scene_plan_path and Path(scene_plan_path).exists():
            try:
                import json
                candidate = json.loads(Path(scene_plan_path).read_text(encoding="utf-8"))
                source_scenes = candidate.get("scenes", []) if isinstance(candidate, dict) else candidate
                caption_items = [
                    str(item.get("on_screen_text") or item.get("spoken_text") or "").strip()
                    for item in source_scenes if isinstance(item, dict)
                ]
                caption_items = [item for item in caption_items if item]
            except (OSError, ValueError, TypeError):
                caption_items = []
        if not caption_items:
            caption_items = split_sentences(script) or [script[:100]]
        weights = [max(1, len(item)) for item in caption_items]
        total_weight = sum(weights) or 1
        cursor = 0.0
        txt_clips = []
        for i, (sent, weight) in enumerate(zip(caption_items[:40], weights[:40])):
            start_at = cursor
            cursor += duration * weight / total_weight
            segment_duration = max(0.1, min(duration - start_at, cursor - start_at))
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
                    .set_start(start_at)
                    .set_duration(segment_duration)
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

        captions_burned = bool(txt_clips)
        if not captions_burned:
            # MoviePy TextClip may be unavailable when ImageMagick is absent.
            # Use FFmpeg/libass as a real burn-in fallback instead of silently
            # producing a captionless video that the quality gate must reject.
            captioned_path = out_dir / "video_captioned.mp4"
            try:
                _burn_captions_ffmpeg(video_path, srt_path, captioned_path)
                if not captioned_path.is_file() or captioned_path.stat().st_size <= 1024:
                    raise RuntimeError("FFmpeg caption fallback produced an empty file")
                captioned_path.replace(video_path)
                captions_burned = True
            except Exception as caption_error:
                print(f"[video] caption burn-in fallback failed: {caption_error}")
                try:
                    captioned_path.unlink(missing_ok=True)
                except Exception:
                    pass

        return {
            "video_path": str(video_path),
            "thumbnail_path": str(thumb),
            "captions_path": str(srt_path),
            "duration": duration,
            "style": "stock_motion_cinematic",
            "on_screen_captions": captions_burned,
            "ok": True,
        }
    except Exception as e:
        print(f"[video] render failed: {e}")
        write_srt(script, srt_path, 45.0 if kind == "short" else 300.0, scene_plan_path=scene_plan_path)
        return {
            "video_path": None,
            "thumbnail_path": str(thumb),
            "captions_path": str(srt_path),
            "on_screen_captions": False,
            "ok": False,
            "error": str(e),
        }
