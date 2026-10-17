"""Rights-aware, heuristic short-clip extraction prototype.

This module does not download third-party videos or publish to YouTube. It only
processes a local source file when the caller explicitly confirms they have
permission to use it. Candidate ranking is a simple scene-change heuristic,
not a claim of AI virality prediction.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


def _tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required executable not found: {name}")
    return path


def probe_duration(source: Path) -> float:
    result = subprocess.run(
        [_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(source)],
        check=True, capture_output=True, text=True,
    )
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("Could not read source video duration") from exc
    if duration <= 0:
        raise RuntimeError("Source video has no positive duration")
    return duration


def detect_scene_times(source: Path) -> list[float]:
    """Return scene-change timestamps using FFmpeg's built-in scene detector."""
    command = [
        _tool("ffmpeg"), "-hide_banner", "-i", str(source), "-vf",
        "select='gt(scene,0.25)',showinfo", "-an", "-f", "null", "-",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    log = (result.stderr or "") + "\n" + (result.stdout or "")
    times = []
    for match in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", log):
        value = float(match.group(1))
        if value >= 0:
            times.append(value)
    # FFmpeg can return a non-zero code for some decoders even after logging frames.
    return sorted(set(times))


def rank_candidates(duration: float, clip_seconds: float, scene_times: Sequence[float], count: int) -> list[dict[str, float | int]]:
    if clip_seconds < 5 or clip_seconds > 90:
        raise ValueError("clip_seconds must be between 5 and 90")
    if count < 1 or count > 10:
        raise ValueError("count must be between 1 and 10")
    if duration < clip_seconds:
        raise ValueError(f"Source is {duration:.1f}s; it must be at least {clip_seconds}s")

    last_start = duration - clip_seconds
    starts = {0.0, round(last_start, 3)}
    starts.update(round(max(0.0, min(last_start, t - clip_seconds / 2)), 3) for t in scene_times)
    # Add a sparse grid so sources with few scene changes still produce candidates.
    step = max(5.0, clip_seconds / 2)
    cursor = 0.0
    while cursor <= last_start:
        starts.add(round(cursor, 3))
        cursor += step

    candidates = []
    for start in starts:
        end = start + clip_seconds
        scene_count = sum(start <= t <= end for t in scene_times)
        # Scene activity is only a transparent heuristic; it is not a viral score.
        candidates.append({"start": float(start), "duration": float(clip_seconds), "scene_changes": int(scene_count)})
    candidates.sort(key=lambda item: (-int(item["scene_changes"]), float(item["start"])))

    selected: list[dict[str, float | int]] = []
    for candidate in candidates:
        start = float(candidate["start"])
        end = start + clip_seconds
        if all(end <= float(old["start"]) or start >= float(old["start"]) + clip_seconds for old in selected):
            selected.append(candidate)
            if len(selected) == count:
                break
    return sorted(selected, key=lambda item: float(item["start"]))


def render_vertical_clip(source: Path, destination: Path, start: float, duration: float) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    subprocess.run(
        [_tool("ffmpeg"), "-hide_banner", "-y", "-ss", f"{start:.3f}", "-i", str(source),
         "-t", f"{duration:.3f}", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "22", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(destination)],
        check=True, capture_output=True, text=True,
    )


def build_clips(source: Path, output_dir: Path, *, clip_seconds: float = 30.0, count: int = 3,
                rights_confirmed: bool = False) -> dict:
    if not rights_confirmed:
        raise PermissionError("Confirm rights to use this source with rights_confirmed=True")
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source}")
    duration = probe_duration(source)
    scenes = detect_scene_times(source)
    candidates = rank_candidates(duration, clip_seconds, scenes, count)
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    for index, candidate in enumerate(candidates, start=1):
        filename = f"candidate_{index:02d}_{int(candidate['start']):04d}s.mp4"
        target = output_dir / filename
        render_vertical_clip(source, target, float(candidate["start"]), float(candidate["duration"]))
        rendered.append({**candidate, "file": filename})
    manifest = {
        "source_name": source.name,
        "source_duration_seconds": round(duration, 3),
        "rights_confirmed_by_caller": True,
        "selection_method": "ffmpeg_scene_change_heuristic_not_viral_prediction",
        "format": "1080x1920_vertical_h264_aac",
        "candidates": rendered,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
