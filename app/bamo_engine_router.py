"""BAMO topic-aware specialist renderer routing.

The 11 editorial roles produce a structured production decision. This module
maps that decision to specialist renderers; it does not pretend that optional
renderers are installed or that role specifications are live LLM agents.
"""
from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class Engine:
    name: str
    command: str | None = None
    module: str | None = None
    purpose: str = ""

    def available(self) -> bool:
        if self.command and not shutil.which(self.command):
            return False
        if self.module and importlib.util.find_spec(self.module) is None:
            return False
        return True

# Optional specialists are detected at runtime. Core FFmpeg remains the
# dependable compositor/encoder, not a substitute for a missing specialist.
ENGINES = {
    "blender": Engine("Blender", command="blender", purpose="3D scenes, character animation, VFX, camera and lighting"),
    "manim": Engine("Manim Community", command="manim", purpose="mathematics, equations, proofs and geometry"),
    "threejs": Engine("Three.js", command="node", purpose="procedural 3D, particles, astronomy and interactive visualizations"),
    "motion_canvas": Engine("Motion Canvas", command="node", purpose="timeline-driven motion graphics and typography"),
    "hyperframes": Engine("HyperFrames", command="npx", purpose="HTML/CSS composition, captions, overlays and scene assembly"),
    "pyvista": Engine("PyVista", module="pyvista", purpose="scientific and physical 3D visualization"),
    "rdkit": Engine("RDKit", module="rdkit", purpose="chemical structures and molecular visualization"),
    "ffmpeg": Engine("FFmpeg", command="ffmpeg", purpose="audio/video encoding and final muxing"),
}

# Each genre has a primary specialist and purposeful supporting renderers.
# No generic fallback is silently selected when the primary is missing.
ROUTES = {
    "mathematics": ("manim", "motion_canvas", "hyperframes"),
    "geometry": ("manim", "threejs", "blender", "hyperframes"),
    "physics": ("manim", "pyvista", "blender", "hyperframes"),
    "chemistry": ("rdkit", "blender", "threejs", "hyperframes"),
    "science": ("pyvista", "threejs", "manim", "hyperframes"),
    "humor": ("blender", "motion_canvas", "hyperframes"),
    "comedy": ("blender", "motion_canvas", "hyperframes"),
    "character_animation": ("blender", "motion_canvas", "hyperframes"),
    "cinematic": ("blender", "threejs", "hyperframes"),
    "history": ("blender", "motion_canvas", "hyperframes"),
    "religion": ("blender", "motion_canvas", "hyperframes"),
    "philosophy": ("blender", "manim", "motion_canvas", "hyperframes"),
    "sports": ("blender", "threejs", "motion_canvas", "hyperframes"),
    "data": ("threejs", "motion_canvas", "hyperframes"),
    "infographic": ("motion_canvas", "threejs", "hyperframes"),
    "motion_graphics": ("motion_canvas", "threejs", "hyperframes"),
    "general": ("blender", "motion_canvas", "hyperframes"),
}

ALIASES = {
    "math": "mathematics", "funny": "humor", "science_explainer": "science",
    "physics_simulation": "physics", "molecular": "chemistry",
    "3d": "cinematic", "documentary": "history", "sport": "sports",
}

def normalize_genre(genre: str) -> str:
    key = str(genre or "general").strip().lower().replace("-", "_").replace(" ", "_")
    key = ALIASES.get(key, key)
    if key not in ROUTES:
        raise ValueError(f"Unknown BAMO genre '{genre}'. Supply a supported genre; no generic visual fallback is allowed.")
    return key

def route_for_genre(genre: str, *, require_available: bool = False) -> dict:
    """Return the chosen specialist and readiness report for a genre."""
    key = normalize_genre(genre)
    candidates = ROUTES[key]
    checks = [{"key": name, "name": ENGINES[name].name, "available": ENGINES[name].available(),
               "purpose": ENGINES[name].purpose} for name in candidates]
    ready = [item for item in checks if item["available"]]
    primary = checks[0]
    selected = next((item for item in ready if item["key"] == primary["key"]), None)
    if selected is None:
        if require_available:
            raise RuntimeError(
                f"Specialist renderer required for '{key}' is unavailable: {primary['name']}. "
                "Install/enable the specialist; refusing to create an unrelated generic scene."
            )
        selected = None
    return {
        "genre": key,
        "primary_engine": primary["key"],
        "selected_engine": selected["key"] if selected else None,
        "ready": selected is not None,
        "fallback_candidates": [item["key"] for item in ready if item["key"] != primary["key"]],
        "engines": checks,
        "compositor": "ffmpeg",
        "policy": "No silent cross-genre fallback; missing primary specialist must be surfaced for review.",
    }

def validate_agent_decision(decision: dict) -> dict:
    """Validate the 11-agent director's minimum routing handoff."""
    if not isinstance(decision, dict):
        raise ValueError("Agent decision must be an object")
    genre = normalize_genre(decision.get("genre", ""))
    if not str(decision.get("visual_brief", "")).strip():
        raise ValueError("Agent decision must include a concrete visual_brief")
    if not str(decision.get("narration", "")).strip():
        raise ValueError("Agent decision must include narration")
    result = route_for_genre(genre)
    result["visual_brief"] = str(decision["visual_brief"]).strip()
    result["narration"] = str(decision["narration"]).strip()
    result["quality_gates"] = [
        "scene_subject_matches_narration",
        "genre_style_matches_director_decision",
        "scientific_claims_checked_when_applicable",
        "rendered_video_probe_passes",
    ]
    return result
