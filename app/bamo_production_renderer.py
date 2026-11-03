"""Production adapter for Blender CPU 3D scenes; preview-only until visual approval."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from app.bamo_motion_engine import render_project
from app.bamo_ai_director import direct_scene, ensure_distinct_camera_moves
from app.spiritual_video import (
    _ambient_track, _write_shorts_ass, make_thumbnail,
    probe_duration, probe_stream_duration,
)

# Approval is opt-in and is never inferred from a successful render.
PRODUCTION_VISUALS_APPROVED = os.getenv("BAMO_PRODUCTION_VISUALS_APPROVED", "false").lower() == "true"


def render_bamo_shorts(
    *,
    title: str,
    thumbnail_text: str,
    audio_path: Path,
    captions_path: Path,
    out_dir: Path,
    run_id: str,
    scenes: list[dict[str, Any]],
    scene_timings: list[dict[str, float]],
    hook_overlay: str,
) -> dict[str, Any]:
    """Render four subject-specific Blender 3D scenes, Persian voice, captions and ducked ambience."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if len(scenes) != 4 or len(scene_timings) != 4:
        raise ValueError("BAMO 3D Shorts renderer requires exactly four narrated scenes and timings")

    audio_duration = probe_duration(Path(audio_path))
    starts = [float(row["start_seconds"]) for row in scene_timings]
    if starts[0] < 0 or any(b <= a for a, b in zip(starts, starts[1:])):
        raise ValueError("TTS scene start times must be strictly increasing")
    boundaries = starts[1:] + [audio_duration]
    durations = [end - start for start, end in zip(starts, boundaries)]
    if any(duration < 0.5 for duration in durations):
        raise ValueError("Each authored 3D scene must last at least 0.5 seconds")

    render_scenes = []
    visual_plans = []
    story_context = " | ".join(str(item.get("spoken_text") or "") for item in scenes)
    prior_theses = []
    prior_cameras = []
    for scene, duration in zip(scenes, durations):
        narration = str(scene.get("spoken_text") or "").strip()
        visual_prompt = str(scene.get("visual_query") or "").strip()
        overlay = str(scene.get("on_screen_text") or "").strip()
        if not narration or not visual_prompt or not overlay:
            raise ValueError("Each 3D scene needs narration, a specific visual query, and Persian overlay text")
        plan = direct_scene(
            narration=narration, visual_brief=visual_prompt, overlay=overlay,
            duration_seconds=duration, story_context=story_context,
            previous_visual_theses=prior_theses, previous_camera_moves=prior_cameras,
        )
        prior_theses.append(plan["visual_thesis"])
        prior_cameras.append(plan["camera"]["move"])
        visual_plans.append(plan)
    ensure_distinct_camera_moves(visual_plans)
    for plan, duration, scene in zip(visual_plans, durations, scenes):
        render_scenes.append({
            "duration": duration,
            "text": str(scene.get("on_screen_text") or "").strip(),
            "narration": str(scene.get("spoken_text") or "").strip(),
            "visual_prompt": str(scene.get("visual_query") or "").strip(),
            "background": "",
            "accent": "",
            "scene_graph": {key: plan[key] for key in ("camera", "palette", "objects", "relationships", "visual_thesis")},
        })

    signatures = [
        tuple((obj["kind"], tuple(obj["position"]), obj["role"]) for obj in plan["objects"])
        for plan in visual_plans
    ]
    if len(set(signatures)) != len(signatures):
        raise ValueError("AI director repeated an identical 3D composition within one Short")

    project = {"format": "short", "fps": 24, "scenes": render_scenes}
    silent_path = out_dir / "bamo-3d-silent.mp4"
    render_project(project, silent_path, audio=None)

    ass_path = _write_shorts_ass(
        Path(captions_path), out_dir / "captions-burned.ass",
        hook=hook_overlay, duration=audio_duration,
    )
    music_path = _ambient_track(
        out_dir / "ambient.wav", audio_duration, sum(map(ord, run_id)),
        profile="shorts", scene_durations=durations,
    )
    thumbnail_path = make_thumbnail(title, thumbnail_text, out_dir / "thumbnail.jpg")
    final_path = out_dir / "video.mp4"
    escaped_subs = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    mix = (
        "[1:a]highpass=f=70,acompressor=threshold=0.16:ratio=2:attack=12:release=220,"
        "loudnorm=I=-16:TP=-2:LRA=8,asetpts=PTS-STARTPTS,asplit=2[voice][voice_key];"
        "[2:a]volume=0.16,asetpts=PTS-STARTPTS[bed];"
        "[bed][voice_key]sidechaincompress=threshold=0.035:ratio=5:attack=12:release=280,"
        f"apad=whole_dur={audio_duration:.3f},atrim=duration={audio_duration:.3f},asetpts=PTS-STARTPTS[ducked];"
        "[voice][ducked]amix=inputs=2:duration=longest:dropout_transition=0,"
        f"alimiter=limit=0.96,apad=pad_dur=0.25,atrim=duration={audio_duration:.3f}[aout]"
    )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(silent_path), "-i", str(audio_path), "-stream_loop", "-1", "-i", str(music_path),
        "-filter_complex", mix, "-map", "0:v:0", "-map", "[aout]",
        "-vf", f"subtitles='{escaped_subs}'", "-t", f"{audio_duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(final_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=max(900, int(audio_duration * 18)))
    if not final_path.is_file() or final_path.stat().st_size < 100_000:
        raise RuntimeError("Approved 3D renderer produced an empty final MP4")

    width, height = 1080, 1920
    visual_review_path = out_dir / "visual-review.json"
    from app.bamo_visual_review import validate_visual_review
    visual_review = validate_visual_review(visual_review_path, expected_scenes=4)
    plans_grounded = visual_review.get("ok") is True
    production_approved = PRODUCTION_VISUALS_APPROVED and plans_grounded
    return {
        "ok": True,
        "video_path": str(final_path),
        "thumbnail_path": str(thumbnail_path),
        "captions_path": str(captions_path),
        "burned_captions_path": str(ass_path),
        "duration_seconds": probe_duration(final_path),
        "audio_duration_seconds": probe_stream_duration(final_path, "a:0"),
        "visual_source": "bamo-cpu-3d-motion",
        "contains_synthetic_visuals": True,
        "stock_clip_count": 0,
        "visual_scene_count": len(render_scenes),
        "pexels_credits": [],
        "music_source": "procedurally generated original ambience",
        "on_screen_captions": True,
        "video_width": width,
        "video_height": height,
        "video_format": "shorts",
        "caption_font_size": 52,
        "caption_animation_profile": "phrase-pop-fade-v1",
        "persian_text_shaping": "noto-naskh-unicode-rtl",
        "hook_overlay": str(hook_overlay or ""),
        "scene_query_match": False,
        "scene_visual_alignment_verified": plans_grounded,
        "visual_alignment_status": "human_frame_review_passed" if plans_grounded else "not_verified_requires_frame_level_review",
        "visual_review_path": str(visual_review_path),
        "visual_review_evidence": visual_review,
        "production_visuals_approved": production_approved,
        "visual_quality_tier": "blender-cpu-3d-preview",
        "scene_visual_plans": visual_plans,
        "camera_motion": [plan.get("camera", {}).get("move") for plan in visual_plans],
        "ai_director_provider_models": sorted({plan.get("provider", "unknown") for plan in visual_plans}),
        "ai_scene_theses": [plan.get("visual_thesis") for plan in visual_plans],
        "render_backend": "blender-cycles-cpu",
        "test_visuals_only": False,
        "music_ducking": True,
        "renderer": "BAMO Blender CPU 3D cinematic preview (not yet production-approved)",
    }
