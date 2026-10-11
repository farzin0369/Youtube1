"""Low-cost vertical stock/abstract video assembly with Persian captions."""
from __future__ import annotations

import json
import logging
import math
import os
import random
import subprocess
import textwrap
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from PIL import Image, ImageDraw, ImageFont
from app.utils import env

WIDTH, HEIGHT, FPS = 720, 1280, 24


def _get_with_backoff(request_factory, *, attempts: int = 3):
    """Retry Pexels network/rate-limit/server failures with capped exponential backoff."""
    import requests

    for attempt in range(attempts):
        response = None
        try:
            response = request_factory()
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == attempts - 1:
                    response.raise_for_status()
                try:
                    retry_after = float(response.headers.get("Retry-After", "0"))
                except (TypeError, ValueError):
                    retry_after = 0
                response.close()
                time.sleep(min(10.0, max(float(2 ** attempt), retry_after, 1.0)))
                continue
            response.raise_for_status()
            return response
        except requests.RequestException:
            if response is not None:
                status = getattr(response, "status_code", 0)
                response.close()
                if status and status != 429 and status < 500:
                    raise
            if attempt == attempts - 1:
                raise
            time.sleep(min(8.0, float(2 ** attempt)))
    raise RuntimeError("Pexels request exhausted its retry budget")


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True, timeout=30,
    )
    value = float(result.stdout.strip())
    if value <= 0:
        raise RuntimeError("Media duration is not positive")
    return value


def _pexels_results(keyword: str, api_key: str, per_page: int = 20) -> list[dict[str, Any]]:
    import requests
    response = _get_with_backoff(lambda: requests.get(
        "https://api.pexels.com/v1/videos/search",
        params={"query": keyword, "orientation": "portrait", "per_page": per_page, "size": "medium"},
        headers={"Authorization": api_key}, timeout=(10, 35),
    ))
    try:
        return list(response.json().get("videos") or [])
    finally:
        response.close()


def _choose_file(video: dict[str, Any]) -> dict[str, Any] | None:
    files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("link")]
    if not files:
        return None
    portrait = [f for f in files if (f.get("height") or 0) >= (f.get("width") or 1)]
    pool = portrait or files
    # Prefer a source large enough for 720x1280, but avoid downloading unnecessarily huge masters.
    sufficient = [f for f in pool if (f.get("height") or 0) >= 960]
    pool = sufficient or pool
    return min(pool, key=lambda f: (f.get("width") or 10_000) * (f.get("height") or 10_000))


def fetch_stock(keywords: list[str], out_dir: Path, count: int = 18) -> tuple[list[Path], list[str]]:
    """Fetch a bounded set of distinct Pexels clips and keep courtesy credits."""
    api_key = (env("PEXELS_API_KEY") or "").strip()
    if not api_key:
        return [], []
    videos: list[dict[str, Any]] = []
    seen: set[str] = set()
    for keyword in keywords[:5]:
        try:
            for video in _pexels_results(keyword, api_key):
                video_id = str(video.get("id") or "")
                if not video_id or video_id in seen or not _choose_file(video):
                    continue
                seen.add(video_id)
                videos.append(video)
                if len(videos) >= count:
                    break
        except Exception as exc:
            logging.getLogger(__name__).warning("Pexels query failed (%s); using available/local fallback clips.", type(exc).__name__)
        if len(videos) >= count:
            break
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    credits: list[str] = []
    import requests
    for video in videos[:count]:
        chosen = _choose_file(video)
        if not chosen:
            continue
        target = out_dir / f"pexels_{video['id']}.mp4"
        try:
            with _get_with_backoff(lambda: requests.get(chosen["link"], stream=True, timeout=(10, 60))) as response:
                response.raise_for_status()
                total = 0
                with target.open("wb") as dst:
                    for block in response.iter_content(1024 * 1024):
                        if not block:
                            continue
                        total += len(block)
                        if total > 80 * 1024 * 1024:
                            raise ValueError("clip exceeds 80 MiB safety limit")
                        dst.write(block)
            if target.stat().st_size < 50_000:
                raise ValueError("downloaded clip is too small")
            paths.append(target)
            user = video.get("user") or {}
            credit = f"Pexels video by {user.get('name', 'creator')}: {video.get('url', '')}"
            if credit not in credits:
                credits.append(credit)
        except Exception as exc:
            target.unlink(missing_ok=True)
            logging.getLogger(__name__).warning("Pexels clip skipped (%s).", type(exc).__name__)
    return paths, credits


def _font(size: int):
    for candidate in (
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_thumbnail(title: str, text: str, out_path: Path) -> Path:
    width, height = 1280, 720
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    top, bottom = (13, 24, 43), (55, 55, 82)
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(width):
            glow = max(0, 1 - math.sqrt(((x - 980) / 720) ** 2 + ((y - 120) / 600) ** 2))
            pixels[x, y] = tuple(min(255, int(c + glow * (8, 22, 18)[i])) for i, c in enumerate(color))
    draw = ImageDraw.Draw(image)
    draw.ellipse((850, -170, 1420, 400), outline=(207, 179, 112), width=5)
    draw.ellipse((905, -115, 1365, 345), outline=(207, 179, 112), width=2)
    draw.rounded_rectangle((70, 64, 330, 124), radius=20, fill=(193, 157, 91))
    brand_font = _font(30)
    brand = str(env("CHANNEL_BRAND") or "ImamAli110")[:24]
    try:
        draw.text((200, 94), brand, font=brand_font, fill=(20, 28, 43), anchor="mm", direction="rtl", language="fa")
    except TypeError:
        draw.text((100, 78), brand, font=brand_font, fill=(20, 28, 43))
    headline = textwrap.fill(text or title, width=20)
    font = _font(86)
    lines = headline.splitlines()[:3]
    y = 270 - 58 * (len(lines) - 1)
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font, direction="rtl", language="fa")
            x = (width - (bbox[2] - bbox[0])) // 2
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0), direction="rtl", language="fa")
            draw.text((x, y), line, font=font, fill=(255, 246, 224), direction="rtl", language="fa")
        except TypeError:
            draw.text((width // 2, y), line, font=font, fill=(255, 246, 224), anchor="mm")
        y += 112
    draw.text((width // 2, 650), "تأملی برای رشد آرام و واقعی", font=_font(29), fill=(211, 211, 216), anchor="mm")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, quality=92)
    return out_path


def _fallback_still(path: Path, seed: int) -> None:
    rng = random.Random(seed)
    colors = [(14, 27, 45), (31, 47, 66), (44, 38, 57), (21, 44, 49), (42, 45, 65)]
    a, b = colors[seed % len(colors)], colors[(seed + 2) % len(colors)]
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        c = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        draw.line((0, y, WIDTH, y), fill=c)
    for _ in range(16):
        x, y = rng.randint(-100, WIDTH + 100), rng.randint(-100, HEIGHT + 100)
        radius = rng.randint(20, 130)
        tone = rng.choice([(95, 110, 113), (119, 99, 79), (65, 99, 104)])
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=tone, width=rng.randint(1, 4))
    image.save(path)


def _local_fallback_videos() -> list[Path]:
    folder = Path("assets/fallback_videos")
    return sorted(p for p in folder.glob("*") if p.suffix.lower() in {".mp4", ".mov", ".m4v"})


def _ambient_track(out_path: Path, duration: float, seed: int) -> Path:
    """Use creator-owned, synthesized soft pads; no stock music is redistributed."""
    user_tracks = sorted(Path("assets/music").glob("*.wav")) + sorted(Path("assets/music").glob("*.mp3"))
    if user_tracks:
        return user_tracks[seed % len(user_tracks)]
    chord_sets = [
        (130.81, 164.81, 196.00), (110.00, 146.83, 174.61),
        (123.47, 155.56, 185.00), (98.00, 130.81, 164.81),
        (146.83, 185.00, 220.00),
    ]
    frequencies = chord_sets[seed % len(chord_sets)]
    duration = max(1.0, duration)
    # Four slow, quiet sine layers produce a restrained, original ambient bed.
    inputs = [f"sine=frequency={freq}:sample_rate=44100:duration={duration:.3f}" for freq in frequencies]
    cmd = ["ffmpeg", "-y"]
    for source in inputs:
        cmd += ["-f", "lavfi", "-i", source]
    mix = "".join(f"[{i}:a]volume={vol:.4f},tremolo=f=0.15:d=0.25[a{i}];" for i, vol in enumerate((0.18, 0.09, 0.045)))
    fade_in = min(3.0, max(0.2, duration * 0.08))
    fade_out = min(4.0, max(0.2, duration / 4.0))
    mix += f"[a0][a1][a2]amix=inputs=3:duration=longest,lowpass=f=900,afade=t=in:st=0:d={fade_in:.3f},"
    fade_start = max(0.0, duration - fade_out)
    mix += f"afade=t=out:st={fade_start:.3f}:d={fade_out:.3f}[aout]"
    cmd += ["-filter_complex", mix, "-map", "[aout]", "-ac", "2", "-c:a", "pcm_s16le", str(out_path)]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=max(180, int(duration * 3)))
    return out_path


def _make_segment(source: Path | None, image_path: Path | None, duration: float, out_path: Path, seed: int) -> None:
    vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},eq=brightness=-0.06:saturation=0.88"
    if source:
        cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(source), "-t", f"{duration:.3f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-pix_fmt", "yuv420p", str(out_path)]
    else:
        zoom = "1+0.0005*on" if seed % 2 == 0 else "1.08-0.0005*on"
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(image_path), "-t", f"{duration:.3f}", "-vf", f"zoompan=z='{zoom}':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", str(out_path)]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=max(180, int(duration * 4)))


def render_video(
    *, title: str, thumbnail_text: str, keywords: list[str], audio_path: Path,
    captions_path: Path, out_dir: Path, run_id: str,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(Path(audio_path))
    # Change visuals every ~18 seconds; stock searches are bounded to five API calls.
    count = max(1, min(24, int(math.ceil(duration / 18.0))))
    stock, credits = fetch_stock(keywords, out_dir / "stock", count=count)
    local_fallbacks = _local_fallback_videos() if not stock else []
    scene_dir = out_dir / "scenes"
    scene_dir.mkdir(exist_ok=True)
    segment_duration = duration / count
    parts: list[Path] = []
    for index in range(count):
        part = scene_dir / f"scene_{index:03d}.mp4"
        if stock:
            source = stock[index % len(stock)]
            _make_segment(source, None, segment_duration, part, index)
        elif local_fallbacks:
            source = local_fallbacks[(index + sum(map(ord, run_id))) % len(local_fallbacks)]
            _make_segment(source, None, segment_duration, part, index)
        else:
            still = scene_dir / f"abstract_{index:03d}.jpg"
            _fallback_still(still, index + sum(map(ord, run_id)))
            _make_segment(None, still, segment_duration, part, index)
        parts.append(part)
    concat_file = out_dir / "scenes.txt"
    concat_file.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
    music = _ambient_track(out_dir / "ambient.wav", duration, sum(map(ord, run_id)))
    thumbnail = make_thumbnail(title, thumbnail_text, out_dir / "thumbnail.jpg")
    final_path = out_dir / "video.mp4"
    escaped_srt = str(Path(captions_path).resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    subtitles = f"subtitles='{escaped_srt}':force_style='FontName=Noto Naskh Arabic,FontSize=36,Outline=3,Shadow=1,MarginV=150,Alignment=2,PrimaryColour=&H00FFFFFF,OutlineColour=&H99000000'"
    mix = "[1:a]volume=1.0[voice];[2:a]volume=0.075[bed];[voice][bed]amix=inputs=2:duration=first:dropout_transition=3[aout]"
    command = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(audio_path), "-stream_loop", "-1", "-i", str(music), "-filter_complex", mix,
        "-map", "0:v:0", "-map", "[aout]", "-vf", subtitles,
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", str(final_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=max(900, int(duration * 8)))
    if not final_path.exists() or final_path.stat().st_size < 100_000:
        raise RuntimeError("FFmpeg produced an empty final video")
    return {
        "video_path": str(final_path), "thumbnail_path": str(thumbnail),
        "captions_path": str(captions_path), "duration_seconds": probe_duration(final_path),
        "visual_source": "pexels" if stock else "local fallback videos" if local_fallbacks else "generated abstract fallback",
        "stock_clip_count": len(stock), "visual_scene_count": count,
        "pexels_credits": credits, "music_source": "local licensed track" if music != out_dir / "ambient.wav" else "procedurally generated original ambience",
        "on_screen_captions": True, "ok": True,
    }
