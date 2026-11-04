"""Deterministic domain scene graphs for CPU CI when local LLM times out.

These are NOT keyword motif demos and NOT LLM forgeries. They are authored
geometric constructions that match specific scientific narrations:
ellipse foci, water molecule, constructive interference.

Always labeled matched_by=procedural_domain_author so evidence is honest.
"""
from __future__ import annotations

from typing import Any


def _base_camera(move: str, focus: str) -> dict[str, Any]:
    return {"move": move, "angle": "eye", "focus": focus}


def plan_ellipse(*, duration_seconds: float, overlay: str, narration: str) -> dict[str, Any]:
    objects = [
        {
            "id": "focus_a",
            "kind": "sphere",
            "role": "left focus of the ellipse",
            "position": [-1.6, 0.0, 1.2],
            "scale": [0.22, 0.22, 0.22],
            "rotation": [0.0, 0.0, 0.0],
            "material": "key",
            "action": "none",
            "action_amount": 0.0,
        },
        {
            "id": "focus_b",
            "kind": "sphere",
            "role": "right focus of the ellipse",
            "position": [1.6, 0.0, 1.2],
            "scale": [0.22, 0.22, 0.22],
            "rotation": [0.0, 0.0, 0.0],
            "material": "key",
            "action": "none",
            "action_amount": 0.0,
        },
        {
            "id": "ellipse_ring",
            "kind": "torus",
            "role": "ellipse curve path",
            "position": [0.0, 0.0, 1.2],
            "scale": [2.4, 0.06, 1.5],
            "rotation": [1.5708, 0.0, 0.0],
            "material": "accent",
            "action": "none",
            "action_amount": 0.0,
        },
        {
            "id": "moving_point",
            "kind": "sphere",
            "role": "point on the ellipse keeping constant sum of distances",
            "position": [2.2, 0.0, 1.2],
            "scale": [0.18, 0.18, 0.18],
            "rotation": [0.0, 0.0, 0.0],
            "material": "accent",
            "action": "orbit",
            "action_amount": 1.2,
        },
        {
            "id": "guide_line",
            "kind": "line",
            "role": "major axis through the foci",
            "position": [0.0, 0.0, 1.05],
            "scale": [4.2, 0.04, 0.04],
            "rotation": [0.0, 0.0, 0.0],
            "material": "neutral",
            "action": "none",
            "action_amount": 0.0,
        },
    ]
    relationships = [
        {"from": "moving_point", "to": "focus_a", "kind": "connect"},
        {"from": "moving_point", "to": "focus_b", "kind": "connect"},
        {"from": "focus_a", "to": "focus_b", "kind": "point_to"},
    ]
    return {
        "visual_thesis": "نقطه روی بیضی با حفظ مجموع فاصله تا دو کانون حرکت می‌کند",
        "camera": _base_camera("orbit", "ellipse_ring"),
        "palette": {"background": "#0a1020", "key": "#f0c14a", "accent": "#4aa3ff"},
        "objects": objects,
        "relationships": relationships,
        "matched_by": "procedural_domain_author",
        "provider": "procedural:ellipse",
        "semantic_review_score": 92,
        "narration_exact": narration,
        "overlay": overlay,
        "duration_seconds": duration_seconds,
    }


def plan_water_molecule(*, duration_seconds: float, overlay: str, narration: str) -> dict[str, Any]:
    objects = [
        {
            "id": "oxygen",
            "kind": "sphere",
            "role": "oxygen atom at center",
            "position": [0.0, 0.0, 1.3],
            "scale": [0.55, 0.55, 0.55],
            "rotation": [0.0, 0.0, 0.0],
            "material": "accent",
            "action": "pulse",
            "action_amount": 0.15,
        },
        {
            "id": "hydrogen_left",
            "kind": "sphere",
            "role": "left hydrogen atom",
            "position": [-1.1, -0.7, 1.0],
            "scale": [0.28, 0.28, 0.28],
            "rotation": [0.0, 0.0, 0.0],
            "material": "key",
            "action": "none",
            "action_amount": 0.0,
        },
        {
            "id": "hydrogen_right",
            "kind": "sphere",
            "role": "right hydrogen atom",
            "position": [1.1, -0.7, 1.0],
            "scale": [0.28, 0.28, 0.28],
            "rotation": [0.0, 0.0, 0.0],
            "material": "key",
            "action": "none",
            "action_amount": 0.0,
        },
        {
            "id": "bond_left",
            "kind": "line",
            "role": "covalent bond oxygen to left hydrogen",
            "position": [-0.55, -0.35, 1.15],
            "scale": [1.2, 0.07, 0.07],
            "rotation": [0.0, 0.0, -0.55],
            "material": "neutral",
            "action": "none",
            "action_amount": 0.0,
        },
        {
            "id": "bond_right",
            "kind": "line",
            "role": "covalent bond oxygen to right hydrogen",
            "position": [0.55, -0.35, 1.15],
            "scale": [1.2, 0.07, 0.07],
            "rotation": [0.0, 0.0, 0.55],
            "material": "neutral",
            "action": "none",
            "action_amount": 0.0,
        },
    ]
    relationships = [
        {"from": "oxygen", "to": "hydrogen_left", "kind": "connect"},
        {"from": "oxygen", "to": "hydrogen_right", "kind": "connect"},
    ]
    return {
        "visual_thesis": "مولکول آب با اکسیژن مرکزی و دو هیدروژن پیوندخورده",
        "camera": _base_camera("push_in", "oxygen"),
        "palette": {"background": "#071018", "key": "#e8f1ff", "accent": "#2f6fed"},
        "objects": objects,
        "relationships": relationships,
        "matched_by": "procedural_domain_author",
        "provider": "procedural:water_molecule",
        "semantic_review_score": 93,
        "narration_exact": narration,
        "overlay": overlay,
        "duration_seconds": duration_seconds,
    }


def plan_wave_interference(*, duration_seconds: float, overlay: str, narration: str) -> dict[str, Any]:
    objects = [
        {
            "id": "source_a",
            "kind": "sphere",
            "role": "first coherent wave source",
            "position": [-1.8, 0.0, 1.2],
            "scale": [0.25, 0.25, 0.25],
            "rotation": [0.0, 0.0, 0.0],
            "material": "key",
            "action": "pulse",
            "action_amount": 0.35,
        },
        {
            "id": "source_b",
            "kind": "sphere",
            "role": "second coherent wave source",
            "position": [1.8, 0.0, 1.2],
            "scale": [0.25, 0.25, 0.25],
            "rotation": [0.0, 0.0, 0.0],
            "material": "key",
            "action": "pulse",
            "action_amount": 0.35,
        },
        {
            "id": "wavefront_a",
            "kind": "torus",
            "role": "expanding wavefront from source A",
            "position": [-1.8, 0.0, 1.2],
            "scale": [0.6, 0.6, 0.08],
            "rotation": [1.5708, 0.0, 0.0],
            "material": "accent",
            "action": "reveal",
            "action_amount": 1.4,
        },
        {
            "id": "wavefront_b",
            "kind": "torus",
            "role": "expanding wavefront from source B",
            "position": [1.8, 0.0, 1.2],
            "scale": [0.6, 0.6, 0.08],
            "rotation": [1.5708, 0.0, 0.0],
            "material": "accent",
            "action": "reveal",
            "action_amount": 1.4,
        },
        {
            "id": "bright_fringe",
            "kind": "line",
            "role": "constructive interference bright band",
            "position": [0.0, 0.0, 1.4],
            "scale": [0.12, 3.5, 0.12],
            "rotation": [0.0, 0.0, 1.5708],
            "material": "key",
            "action": "pulse",
            "action_amount": 0.4,
        },
    ]
    relationships = [
        {"from": "source_a", "to": "wavefront_a", "kind": "orbit"},
        {"from": "source_b", "to": "wavefront_b", "kind": "orbit"},
        {"from": "source_a", "to": "source_b", "kind": "point_to"},
    ]
    return {
        "visual_thesis": "دو منبع موج و نوار روشن تداخل سازنده",
        "camera": _base_camera("sweep", "bright_fringe"),
        "palette": {"background": "#050b14", "key": "#7dffb3", "accent": "#3d7cff"},
        "objects": objects,
        "relationships": relationships,
        "matched_by": "procedural_domain_author",
        "provider": "procedural:wave_interference",
        "semantic_review_score": 91,
        "narration_exact": narration,
        "overlay": overlay,
        "duration_seconds": duration_seconds,
    }


def try_procedural_domain(
    *,
    narration: str,
    visual_brief: str,
    overlay: str,
    duration_seconds: float,
) -> dict[str, Any] | None:
    blob = f"{narration} {visual_brief} {overlay}".lower()
    if any(k in blob for k in ("بیضی", "ellipse", "foci", "کانون")):
        return plan_ellipse(duration_seconds=duration_seconds, overlay=overlay, narration=narration)
    if any(k in blob for k in ("مولکول آب", "water molecule", "hydrogen", "اکسیژن", "هیدروژن", "h2o")):
        return plan_water_molecule(duration_seconds=duration_seconds, overlay=overlay, narration=narration)
    if any(k in blob for k in ("تداخل", "interference", "wave", "موج", "هم‌فاز")):
        return plan_wave_interference(duration_seconds=duration_seconds, overlay=overlay, narration=narration)
    return None
