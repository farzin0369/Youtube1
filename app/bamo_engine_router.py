"""Single-engine BAMO renderer policy: HyperFrames only."""
from __future__ import annotations
ENGINE = "hyperframes"
HYPERFRAMES_VERSION = "0.8.225"
COMPOSITOR = "ffmpeg"

def route_for_genre(genre: str, *, require_available: bool = False) -> dict:
    key = str(genre or "general").strip().lower().replace("-", "_").replace(" ", "_")
    return {"genre": key, "primary_engine": ENGINE, "selected_engine": ENGINE,
            "ready": True, "renderer_version": HYPERFRAMES_VERSION,
            "compositor": COMPOSITOR,
            "policy": "HyperFrames is the sole video renderer; FFmpeg only muxes audio and encodes."}

def validate_agent_decision(decision: dict) -> dict:
    if not isinstance(decision, dict):
        raise ValueError("Agent decision must be an object")
    if not str(decision.get("visual_brief", "")).strip():
        raise ValueError("Agent decision must include a concrete visual_brief")
    if not str(decision.get("narration", "")).strip():
        raise ValueError("Agent decision must include narration")
    result = route_for_genre(decision.get("genre", "general"))
    result["visual_brief"] = str(decision["visual_brief"]).strip()
    result["narration"] = str(decision["narration"]).strip()
    result["quality_gates"] = ["all_eleven_agent_handoffs_present",
      "scene_visuals_match_scene_narration", "camera_motion_present",
      "voiceover_and_captions_scene_locked", "rendered_video_probe_passes"]
    return result
