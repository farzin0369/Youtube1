"""LTX-Video rendering adapter for the ImamAli110 spiritual production pipeline."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from app.ltx_video_engine import generate_ltx_film
from app.spiritual_video import _write_shorts_ass, make_thumbnail


def _probe(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    seconds = float(result.stdout.strip())
    if seconds <= 0:
        raise RuntimeError(f"Invalid media duration: {path}")
    return seconds


def _sentences(text: str) -> list[str]:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if not value:
        return []
    parts = re.split(r"(?<=[.!?؟۔])\s+", value)
    return [part.strip() for part in parts if part.strip()]


def _visual_prompt(spoken: str, hint: str, kind: str) -> str:
    orientation = "vertical 9:16" if kind == "short" else "horizontal 16:9"
    hint = re.sub(r"\s+", " ", str(hint or "")).strip()
    return (
        f"Cinematic high-end 3D animated visual metaphor for this Persian spiritual narration: {spoken}. "
        f"Visual concept: {hint or spoken}. Compose for {orientation}. Natural human anatomy, "
        "subtle continuous character and environmental motion, rich realistic materials, volumetric light, "
        "slow deliberate camera movement, emotionally legible storytelling, no text, no subtitles, "
        "no logos, no watermarks, no duplicate faces, no extra limbs."
    )


def _scene_plan(content: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    scenes: list[dict[str, Any]] = []
    if kind == "short":
        source_scenes = content.get("scenes") or []
        for scene in source_scenes:
            spoken = re.sub(r"\s+", " ", str(scene.get("spoken_text") or "")).strip()
            if not spoken:
                continue
            hint = str(scene.get("visual_query") or scene.get("visual_prompt") or "")
            scenes.append({
                "spoken_text": spoken,
                "visual_prompt": _visual_prompt(spoken, hint, kind),
                "on_screen_text": str(scene.get("on_screen_text") or spoken).strip(),
                "duration_hint_seconds": max(1.0, len(spoken.split()) / 2.4),
            })
    else:
        for section in content.get("sections") or []:
            heading = str(section.get("heading") or "").strip()
            for sentence in _sentences(str(section.get("text") or "")):
                scenes.append({
                    "spoken_text": sentence,
                    "visual_prompt": _visual_prompt(sentence, heading, kind),
                    "on_screen_text": sentence,
                    "duration_hint_seconds": max(1.0, len(sentence.split()) / 2.4),
                })
    expected = re.sub(r"\s+", " ", str(content.get("script") or "")).strip()
    actual = " ".join(scene["spoken_text"] for scene in scenes)
    actual = re.sub(r"\s+", " ", actual).strip()
    if not scenes or actual != expected:
        raise RuntimeError("LTX scene plan does not exactly cover the narration; refusing mismatched visuals.")
    if kind == "short" and len(scenes) != 4:
        raise RuntimeError(f"ImamAli110 Shorts require exactly four narration-matched scenes; got {len(scenes)}.")
    return scenes


def render_ltx_video(
    *,
    content: dict[str, Any],
    audio_path: Path,
    captions_path: Path,
    out_dir: Path,
    run_id: str,
    video_format: str,
    scene_timings: list[dict[str, Any]] | None = None,
    hook_overlay: str = "",
) -> dict[str, Any]:
    """Render LTX motion scenes, mux the real narration, burn captions and return QA metadata."""
    if video_format not in {"shorts", "long"}:
        raise ValueError("video_format must be 'shorts' or 'long'")
    kind = "short" if video_format == "shorts" else "long"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_path, captions_path = Path(audio_path), Path(captions_path)
    if not audio_path.is_file() or not captions_path.is_file():
        raise RuntimeError("LTX render requires existing narration audio and timed captions.")
    audio_seconds = _probe(audio_path)
    plan = _scene_plan(content, kind)
    raw_video = out_dir / "ltx_silent.mp4"
    muxed_video = out_dir / "ltx_narrated.mp4"
    final_video = out_dir / "video.mp4"
    ass_path = out_dir / "captions_burned.ass"

    ltx_meta = generate_ltx_film(
        str(content["script"]), str(content["title"]), raw_video,
        kind=kind, seed=110, scene_plan=plan, target_duration_seconds=audio_seconds,
    )
    safe_hook = " ".join(str(hook_overlay or content.get("scenes", [{}])[0].get("on_screen_text") or "").split()[:5]) if kind == "short" else ""
    if kind == "short":
        _write_shorts_ass(
            captions_path, ass_path,
            hook=safe_hook,
            duration=audio_seconds,
        )
        escaped_ass = str(ass_path.resolve()).replace("\\\\", "/")
        caption_filter = f"subtitles='{escaped_ass}':fontsdir='/usr/share/fonts/truetype/noto'"
    else:
        escaped = str(captions_path.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        caption_filter = (
            f"subtitles='{escaped}':force_style="
            "'FontName=Noto Sans Arabic,FontSize=38,Outline=2,Shadow=1,MarginV=60,Alignment=2'"
        )

    pad = max(0.0, audio_seconds - _probe(raw_video))
    pad_filter = f"tpad=stop_mode=clone:stop_duration={pad:.3f},fps=24,format=yuv420p"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_video), "-i", str(audio_path),
        "-vf", pad_filter, "-t", f"{audio_seconds:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", str(muxed_video),
    ], check=True, capture_output=True, text=True)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(muxed_video), "-vf", caption_filter,
        "-t", f"{audio_seconds:.3f}", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "19", "-c:a", "copy", "-movflags", "+faststart", str(final_video),
    ], check=True, capture_output=True, text=True)

    thumbnail = make_thumbnail(
        str(content["title"]), str(content.get("thumbnail_text") or content["title"]),
        out_dir / "thumbnail.jpg",
    )
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", str(final_video),
    ], capture_output=True, text=True, check=True)
    streams = json.loads(probe.stdout).get("streams") or []
    if not streams:
        raise RuntimeError("ffprobe found no video stream in the final LTX output.")
    width, height = int(streams[0]["width"]), int(streams[0]["height"])
    duration = _probe(final_video)
    return {
        **ltx_meta,
        "ok": True,
        "provider": "ltx-video-colab-gpu",
        "visual_source": "ltx-video",
        "visual_scene_count": len(plan),
        "scene_query_match": True,
        "video_path": str(final_video),
        "thumbnail_path": str(thumbnail),
        "captions_path": str(captions_path),
        "burned_captions_path": str(ass_path if kind == "short" else final_video),
        "on_screen_captions": True,
        "duration_seconds": duration,
        "duration": duration,
        "audio_duration_seconds": audio_seconds,
        "video_width": width,
        "video_height": height,
        "video_format": video_format,
        "caption_font_size": 48 if kind == "short" else 38,
        "caption_animation_profile": "phrase-pop-fade-v1" if kind == "short" else "static-readable",
        "persian_text_shaping": "noto-naskh-unicode-rtl" if kind == "short" else "ffmpeg-libass",
        "hook_overlay": safe_hook,
        "background_music_used": False,
        "music_ducking": False,
        "pexels_credits": [],
        "test_visuals_only": False,
        "scene_plan_path": ltx_meta.get("scene_plan_path"),
        "scene_mapping": "exact-narration-scene-plan",
        "resumable": True,
    }
