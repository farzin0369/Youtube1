"""Studio entry point: the production 3D Shorts renderer with scene-kit props enabled.

Runs `app.bamo_production_renderer.render_bamo_shorts` unchanged, except that its
`direct_scene` call is temporarily replaced by `direct_scene_with_props`. Nothing is
patched permanently, so the original renderer keeps working for existing callers.
Any kit failure falls back to the director's own validated primitive plan.
"""
from __future__ import annotations

from typing import Any


def render_bamo_shorts(**kwargs: Any) -> dict[str, Any]:
    import app.bamo_production_renderer as base
    from app.bamo_scene_kit import direct_scene_with_props

    original = base.direct_scene
    base.direct_scene = direct_scene_with_props
    try:
        result = base.render_bamo_shorts(**kwargs)
    finally:
        base.direct_scene = original
    result["scene_kit_enabled"] = True
    return result
