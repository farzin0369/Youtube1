"""BAMO application package."""
import os as _os

if _os.getenv("BAMO_SCENE_KIT", "1") != "0":
    try:  # additive extension; must never break package import
        from app import bamo_scene_kit as _scene_kit
        _scene_kit.install()
    except Exception:  # noqa: BLE001
        pass
