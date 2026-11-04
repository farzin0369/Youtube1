#!/usr/bin/env python3
"""Render three separately narrated AI-directed domain videos for CPU preview.

The scene graphs must come from app.bamo_ai_director.direct_scene. This script
never uploads to YouTube, falls back to predefined motifs, or fabricates success.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import traceback
from pathlib import Path
from typing import Any

from app.bamo_ai_director import direct_scene, ensure_distinct_camera_moves
from app.bamo_motion_engine import render_project
from app.spiritual_tts import synthesize_with_captions
from app.spiritual_video import _write_shorts_ass, probe_duration, probe_stream_duration

OUT = Path("output/bamo-ai-three-domain")
SCENES: list[dict[str, str]] = [
    {
        "domain": "mathematics",
        "slug": "ellipse-foci",
        "title": "بیضی و کانون‌های آن",
        "spoken_text": (
            "بیضی فقط یک دایرهٔ کشیده نیست. دو نقطهٔ ثابت به نام کانون دارد. "
            "هر نقطه روی بیضی را انتخاب کن و فاصله‌اش را تا هر کانون اندازه بگیر. "
            "جمع این دو فاصله همیشه ثابت می‌ماند؛ همین قانون، شکل بیضی را تعریف می‌کند."
        ),
        "visual_query": "A 3D ellipse construction with two fixed foci, a moving point on the curve, and two changing distance lines whose sum remains constant",
        "on_screen_text": "بیضی: مجموع فاصله تا دو کانون ثابت است",
    },
    {
        "domain": "chemistry",
        "slug": "water-molecule",
        "title": "ساختار سه‌بعدی مولکول آب",
        "spoken_text": (
            "یک مولکول آب از یک اتم اکسیژن و دو اتم هیدروژن ساخته می‌شود. "
            "پیوندهای کووالانسی، هیدروژن‌ها را به اکسیژن وصل می‌کنند. "
            "مولکول خطی نیست؛ دو پیوند با زاویه‌ای نزدیک به صد و چهار و نیم درجه قرار می‌گیرند."
        ),
        "visual_query": "A scientifically accurate 3D H2O molecule with one large oxygen sphere, two smaller hydrogen spheres, two covalent bonds, and the bent 104.5-degree geometry",
        "on_screen_text": "H₂O: دو پیوند، ساختار خمیده",
    },
    {
        "domain": "physics",
        "slug": "wave-interference",
        "title": "تداخل دو موج",
        "spoken_text": (
            "وقتی دو موج همدوس در یک فاز به هم می‌رسند، دامنه‌هایشان روی هم جمع می‌شود. "
            "در این نقاط، تداخل سازنده موجی قوی‌تر می‌سازد. "
            "اگر اختلاف مسیر نیم‌طول‌موج باشد، تداخل ویرانگر موج را تضعیف می‌کند."
        ),
        "visual_query": "Two coherent in-phase wave sources with expanding circular wavefronts and a spatially correct constructive bright fringe pattern alternating with destructive nodes",
        "on_screen_text": "دو موج: تداخل سازنده و ویرانگر",
    },
]


def _single_scene_duration(timings: list[dict[str, Any]], audio_duration: float) -> float:
    if not isinstance(timings, list) or len(timings) != 1:
        raise ValueError("Persian TTS must return exactly one timing for each topic video")
    try:
        start = float(timings[0]["start_seconds"])
        end = float(timings[0]["end_seconds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Persian TTS returned an invalid topic timing") from exc
    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
        raise ValueError("Persian TTS returned a non-increasing topic timing")
    duration = end - start
    if start > 0.05 or duration < 0.5 or duration > 60:
        raise ValueError("Topic video timing must start at zero and fit the renderer's 0.5–60s range")
    if abs(end - audio_duration) > 0.75:
        raise ValueError("TTS scene timing does not match the measured narration duration")
    return audio_duration


def _sample_frames(video: Path, duration: float, destination: Path) -> list[str]:
    """Save real opening, midpoint and closing frames for each rendered preview."""
    destination.mkdir(parents=True, exist_ok=True)
    sample_times = [0.05, max(0.05, duration / 2), max(0.05, duration - 0.10)]
    paths: list[str] = []
    for label, timestamp in zip(("start", "middle", "end"), sample_times):
        frame = destination / f"{label}.jpg"
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{timestamp:.3f}", "-i", str(video), "-frames:v", "1",
                "-q:v", "2", str(frame),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode or not frame.is_file() or frame.stat().st_size < 1_000:
            raise RuntimeError(f"Could not extract the {label} frame from {video.name}")
        paths.append(str(frame))
    return paths


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _burn_word_timed_captions(
    source_video: Path,
    captions_srt: Path,
    output_video: Path,
    *,
    hook: str,
    duration: float,
) -> Path:
    """Burn verified TTS word-boundary captions and hook into the final MP4."""
    ass = output_video.with_suffix(".ass")
    _write_shorts_ass(captions_srt, ass, hook=hook, duration=duration)
    escaped_ass = str(ass.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source_video),
        "-vf", f"subtitles='{escaped_ass}'",
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
        str(output_video),
    ]
    result = subprocess.run(
        command, check=False, capture_output=True, text=True,
        timeout=max(300, int(duration * 18)),
    )
    if result.returncode or not output_video.is_file() or output_video.stat().st_size < 100_000:
        raise RuntimeError(f"Could not burn word-timed Persian captions into {output_video.name}")
    return ass


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    prepared: list[dict[str, Any]] = []
    plans: list[dict[str, Any]] = []
    prior_theses: list[str] = []
    prior_cameras: list[str] = []

    for scene in SCENES:
        slug = scene["slug"]
        audio = OUT / f"{slug}-voice.mp3"
        captions = OUT / f"{slug}-captions.srt"
        tts = synthesize_with_captions(
            scene["spoken_text"], audio, captions, scenes=[scene],
        )
        if not tts.get("ok") or tts.get("provider") not in {"edge-tts", "elevenlabs"}:
            raise RuntimeError(f"Persian narration failed for {scene['domain']}; refusing a silent proof")
        if not audio.is_file() or audio.stat().st_size < 8_000:
            raise RuntimeError(f"Persian narration is missing or unexpectedly small for {scene['domain']}")
        if not captions.is_file() or captions.stat().st_size < 20:
            raise RuntimeError(f"Persian captions are missing for {scene['domain']}")

        audio_duration = probe_duration(audio)
        duration = _single_scene_duration(tts.get("scene_timings") or [], audio_duration)
        plan = direct_scene(
            narration=scene["spoken_text"],
            visual_brief=scene["visual_query"],
            overlay=scene["on_screen_text"],
            duration_seconds=duration,
            story_context=scene["spoken_text"],
            previous_visual_theses=prior_theses,
            previous_camera_moves=prior_cameras,
        )
        plan["domain"] = scene["domain"]
        plans.append(plan)
        prior_theses.append(plan["visual_thesis"])
        prior_cameras.append(plan["camera"]["move"])
        prepared.append({"scene": scene, "audio": audio, "captions": captions, "tts": tts, "duration": duration})
        (OUT / "ai-scene-graphs.json").write_text(
            json.dumps(plans, ensure_ascii=False, indent=2), encoding="utf-8",
        )

    ensure_distinct_camera_moves(plans)
    theses = [" ".join(str(plan["visual_thesis"]).casefold().split()) for plan in plans]
    if len(set(theses)) != len(plans):
        raise ValueError("AI director repeated an identical visual thesis across domains")
    if any(plan.get("matched_by") != "semantic_ai_director" for plan in plans):
        raise ValueError("Every topic scene must come from the semantic AI director")
    (OUT / "ai-scene-graphs.json").write_text(
        json.dumps(plans, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    videos: list[dict[str, Any]] = []
    for item, plan in zip(prepared, plans):
        scene = item["scene"]
        audio = Path(item["audio"])
        slug = scene["slug"]
        graph = {key: plan[key] for key in ("camera", "palette", "objects", "relationships", "visual_thesis")}
        project = {
            "format": "short",
            "fps": 24,
            "scenes": [{
                "duration": item["duration"],
                "text": scene["on_screen_text"],
                "narration": scene["spoken_text"],
                "visual_prompt": scene["visual_query"],
                "scene_graph": graph,
            }],
        }
        raw_video = render_project(project, OUT / f"{slug}-uncaptioned.mp4", audio=audio)
        if not raw_video.is_file() or raw_video.stat().st_size < 100_000:
            raise RuntimeError(f"Renderer produced an invalid {scene['domain']} MP4")
        video = OUT / f"{slug}.mp4"
        ass_captions = _burn_word_timed_captions(
            raw_video, Path(item["captions"]), video,
            hook=scene["on_screen_text"], duration=item["duration"],
        )
        raw_video.unlink(missing_ok=True)
        video_duration = probe_duration(video)
        video_audio_duration = probe_stream_duration(video, "a:0")
        if not math.isfinite(video_duration) or video_duration <= 0:
            raise RuntimeError(f"Renderer produced an invalid duration for {scene['domain']}")
        if not math.isfinite(video_audio_duration) or video_audio_duration <= 0:
            raise RuntimeError(f"Renderer produced no valid audio stream for {scene['domain']}")
        if abs(video_duration - item["duration"]) > 1.0 or abs(video_audio_duration - item["duration"]) > 1.0:
            raise RuntimeError(f"Audio/video duration mismatch for {scene['domain']}")
        frames = _sample_frames(video, video_duration, OUT / f"{slug}-inspection-frames")
        videos.append({
            "domain": scene["domain"],
            "title": scene["title"],
            "tts_provider": item["tts"].get("provider"),
            "tts_voice": item["tts"].get("voice"),
            "narration_exact": scene["spoken_text"],
            "narration_seconds": item["duration"],
            "video_path": str(video),
            "video_bytes": video.stat().st_size,
            "video_sha256": _sha256(video),
            "video_duration_seconds": video_duration,
            "audio_stream_duration_seconds": video_audio_duration,
            "inspection_frames": frames,
            "provider": plan.get("provider"),
            "critic_provider": plan.get("critic_provider"),
            "semantic_review_score": plan.get("semantic_review_score"),
            "visual_thesis": plan.get("visual_thesis"),
            "camera": plan.get("camera"),
            "object_ids": [obj["id"] for obj in plan["objects"]],
            "object_kinds": [obj["kind"] for obj in plan["objects"]],
            "caption_path": str(item["captions"]),
            "burned_caption_path": str(ass_captions),
        })

    if len({row["video_sha256"] for row in videos}) != len(videos):
        raise RuntimeError("Two topic renders are byte-identical; rejecting non-distinct proof")
    evidence = {
        "kind": "ai_authored_three_separate_domain_preview_videos",
        "public_upload": False,
        "production_visuals_approved": False,
        "qa_status": "technical_preview_only; pixel-level semantic QA and human production approval remain required",
        "videos": videos,
        "limitations": [
            "The renderer executes a constrained grammar of geometric primitives; it is not a character, organic, or photoreal engine.",
            "The semantic critic checks the authored scene graph before rendering; it does not independently inspect rendered pixels.",
        ],
    }
    evidence_path = OUT / "ai-domain-evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "director-failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
