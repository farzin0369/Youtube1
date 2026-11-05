"""BAMO application package."""
import os as _os

if _os.getenv("BAMO_PREFABS", "1") != "0":
    try:  # additive extension; must never break package import
        from app import bamo_prefab_director as _prefab_director
        _prefab_director.install()
    except Exception:  # noqa: BLE001
        pass
