"""Automated quality gate for finished BAMO videos (replaces manual frame review).

Measures what a careful editor would check before uploading: aspect/resolution,
duration, audio present and at sane loudness, little dead air, a visible and
changing picture (not blank/frozen), a visible first frame (the hook) and
captions. Every threshold is explicit and every failure carries a reason, so the
self-repair loop can act on it. Needs ffmpeg/ffprobe and Pillow.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

DEFAULT_LIMITS = {
    "aspect_tolerance": 0.02,
    "min_seconds": 8.0,
    "max_seconds": 600.0,
    "max_av_gap_seconds": 1.0,
    "mean_volume_db": (-32.0, -8.0),
    "max_silence_ratio": 0.35,
    "min_frame_std": 10.0,
    "frame_mean_range": (12.0, 235.0),
    "min_good_frame_fraction": 0.75,
    "min_mean_motion": 1.5,
    "min_changing_pair_fraction": 0.6,
    "changing_pair_threshold": 1.0,
    "min_first_frame_mean": 10.0,
    "sample_frames": 8,
    "min_bytes": 50_000,
}


def _run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def probe(path: Path) -> dict[str, Any]:
    r = _run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    if r.returncode:
        raise RuntimeError("ffprobe failed: " + r.stderr[-300:])
    data = json.loads(r.stdout)
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    audio = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    dur = float(data["format"].get("duration") or 0)
    return {"width": int(video["width"]) if video else 0, "height": int(video["height"]) if video else 0,
            "duration": dur, "has_audio": audio is not None,
            "audio_duration": float(audio.get("duration") or dur) if audio else 0.0}


def parse_volumedetect(stderr: str) -> float | None:
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", stderr)
    return float(m.group(1)) if m else None


def parse_silence_ratio(stderr: str, duration: float) -> float:
    total = 0.0
    for m in re.finditer(r"silence_duration:\s*([\d.]+)", stderr):
        total += float(m.group(1))
    return min(1.0, total / duration) if duration > 0 else 1.0


def audio_levels(path: Path, duration: float) -> tuple[float | None, float]:
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn",
              "-af", "volumedetect,silencedetect=noise=-45dB:d=0.7", "-f", "null", "-"])
    return parse_volumedetect(r.stderr), parse_silence_ratio(r.stderr, duration)


def extract_frames(path: Path, count: int, duration: float, out_dir: Path) -> list[Path]:
    frames = []
    for i in range(count):
        t = max(0.05, min(duration - 0.1, duration * (i + 0.5) / count)) if i else 0.05
        target = out_dir / f"qc_{i:02d}.png"
        r = _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}",
                  "-i", str(path), "-frames:v", "1", str(target)], timeout=60)
        if r.returncode == 0 and target.is_file() and target.stat().st_size > 200:
            frames.append(target)
    return frames


def _gray(path: Path) -> Image.Image:
    with Image.open(path) as im:
        return im.convert("L").resize((96, 96))


def frame_metrics(frames: list[Path]) -> list[dict[str, float]]:
    out = []
    for p in frames:
        st = ImageStat.Stat(_gray(p))
        out.append({"mean": st.mean[0], "std": st.stddev[0]})
    return out


def motion_scores(frames: list[Path]) -> list[float]:
    grays = [_gray(p) for p in frames]
    return [ImageStat.Stat(ImageChops.difference(a, b)).mean[0] for a, b in zip(grays, grays[1:])]


def _check(checks, name, ok, value, limit=None):
    checks[name] = {"ok": bool(ok), "value": value, **({"limit": limit} if limit is not None else {})}


def evaluate(info: dict[str, Any], mean_volume: float | None, silence_ratio: float,
             fm: list[dict[str, float]], motion: list[float], *, aspect: str = "9:16",
             captions_ok: bool | None = None, limits: dict[str, Any] | None = None) -> dict[str, Any]:
    L = {**DEFAULT_LIMITS, **(limits or {})}
    checks: dict[str, Any] = {}
    w, h = aspect.split(":")
    target = float(w) / float(h)
    actual = info["width"] / info["height"] if info["height"] else 0
    _check(checks, "aspect", abs(actual - target) <= L["aspect_tolerance"] * target, round(actual, 4), aspect)
    _check(checks, "duration", L["min_seconds"] <= info["duration"] <= L["max_seconds"], round(info["duration"], 2),
           [L["min_seconds"], L["max_seconds"]])
    _check(checks, "has_audio", info["has_audio"], info["has_audio"])
    if info["has_audio"]:
        _check(checks, "av_duration_gap", abs(info["audio_duration"] - info["duration"]) <= L["max_av_gap_seconds"],
               round(abs(info["audio_duration"] - info["duration"]), 2), L["max_av_gap_seconds"])
        lo, hi = L["mean_volume_db"]
        _check(checks, "loudness", mean_volume is not None and lo <= mean_volume <= hi, mean_volume, [lo, hi])
        _check(checks, "dead_air", silence_ratio <= L["max_silence_ratio"], round(silence_ratio, 3), L["max_silence_ratio"])
    n = max(1, len(fm))
    lo_m, hi_m = L["frame_mean_range"]
    good = sum(1 for f in fm if f["std"] >= L["min_frame_std"] and lo_m <= f["mean"] <= hi_m)
    _check(checks, "frames_not_blank", fm and good / n >= L["min_good_frame_fraction"], round(good / n, 2),
           L["min_good_frame_fraction"])
    _check(checks, "hook_frame_visible", bool(fm) and fm[0]["mean"] >= L["min_first_frame_mean"] and fm[0]["std"] >= L["min_frame_std"] * 0.5,
           round(fm[0]["mean"], 1) if fm else None, L["min_first_frame_mean"])
    mean_motion = sum(motion) / len(motion) if motion else 0.0
    changing = sum(1 for m in motion if m >= L["changing_pair_threshold"]) / len(motion) if motion else 0.0
    _check(checks, "picture_changes", mean_motion >= L["min_mean_motion"] and changing >= L["min_changing_pair_fraction"],
           {"mean": round(mean_motion, 2), "changing_fraction": round(changing, 2)},
           {"mean": L["min_mean_motion"], "changing_fraction": L["min_changing_pair_fraction"]})
    if captions_ok is not None:
        _check(checks, "captions_present", captions_ok, captions_ok)
    reasons = [name for name, c in checks.items() if not c["ok"]]
    return {"ok": not reasons, "checks": checks, "reasons": reasons}


def qc_video(video: Path, *, aspect: str = "9:16", captions: Path | None = None,
             limits: dict[str, Any] | None = None) -> dict[str, Any]:
    video = Path(video)
    L = {**DEFAULT_LIMITS, **(limits or {})}
    if not video.is_file() or video.stat().st_size < L["min_bytes"]:
        return {"ok": False, "checks": {}, "reasons": ["file_missing_or_tiny"]}
    info = probe(video)
    vol, sil = (audio_levels(video, info["duration"]) if info["has_audio"] else (None, 1.0))
    with tempfile.TemporaryDirectory() as tmp:
        frames = extract_frames(video, L["sample_frames"], info["duration"], Path(tmp))
        fm = frame_metrics(frames)
        motion = motion_scores(frames)
    captions_ok = None if captions is None else (Path(captions).is_file() and Path(captions).stat().st_size > 20)
    report = evaluate(info, vol, sil, fm, motion, aspect=aspect, captions_ok=captions_ok, limits=limits)
    report["info"] = info
    return report
