"""Extends BAMO's AI scene director with compound 3D prefab kinds.

Not to be confused with app/bamo_scene_kit.py (parametric props expanded into primitives);
the two are independent and can coexist.

The original director (app/bamo_ai_director.py) is left untouched. install() wraps
its normalize/validate functions so prefab kinds (figure, column, dome, wave_field,
...) pass through its strict validator as placeholders and are restored afterwards,
and appends the prefab vocabulary to the director's system prompt.

Disable with BAMO_PREFABS=0. Idempotent.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_PREFAB_FILE = Path(__file__).resolve().parents[1] / "scripts" / "bamo_prefabs.py"
_spec = importlib.util.spec_from_file_location("bamo_prefabs_shared", _PREFAB_FILE)
prefabs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prefabs)

_EXTRA_HINTS = (
    (("قرآن", "آیه", "تفسیر", "حدیث", "دعا", "نماز", "اهل بیت", "quran", "hadith", "prayer"),
     "religious: respectful symbolic imagery only (light, dome, arch, columns, open_book, calligraphic geometry). Never depict holy persons as figures."),
    (("فوتبال", "ورزش", "رکورد", "مسابقه", "بازیکن", "football", "sport", "record", "match"),
     "sports: a pitch or track with figure athletes, ball, and motion; show the actual move or record being described."),
    (("طنز", "خنده", "بامزه", "کمدی", "funny", "comedy", "joke"),
     "comedy: original figure characters in an exaggerated situation with a clear setup and punchline action."),
    (("تاریخ", "معماری", "شهر", "بنا", "ancient", "city", "castle", "temple"),
     "history: reconstruct the place with column, arch, dome, tower, house or pyramid prefabs plus figures at human scale."),
)


def to_prefab(kind: Any) -> str | None:
    canonical = prefabs.canonical_kind(str(kind or ""))
    return canonical if canonical in prefabs.PREFAB_KINDS else None


def install(director: Any = None) -> bool:
    if director is None:
        import app.bamo_ai_director as director

    if getattr(director, "_BAMO_SCENE_KIT", False):
        return False
    original_normalize = director.normalize_scene_graph
    original_validate = director.validate_scene_graph

    def normalize_with_prefabs(raw: Any) -> Any:
        if isinstance(raw, dict) and isinstance(raw.get("objects"), list):
            tagged = []
            for item in raw["objects"]:
                if isinstance(item, dict) and to_prefab(item.get("kind")):
                    item = dict(item)
                    item["_prefab"] = to_prefab(item.get("kind"))
                    item["kind"] = "sphere"  # placeholder accepted by the strict validator
                tagged.append(item)
            raw = {**raw, "objects": tagged}
        return original_normalize(raw)

    def validate_with_prefabs(raw: Any) -> dict[str, Any]:
        marks = []
        if isinstance(raw, dict) and isinstance(raw.get("objects"), list):
            marks = [item.get("_prefab") if isinstance(item, dict) else None for item in raw["objects"]]
        result = original_validate(raw)
        for obj, mark in zip(result["objects"], marks):
            if mark:
                obj["kind"] = mark
        return result

    director.normalize_scene_graph = normalize_with_prefabs
    director.validate_scene_graph = validate_with_prefabs
    director.SYSTEM = director.SYSTEM + "\n\n" + prefabs.PROMPT_SECTION
    director._DOMAIN_HINTS = _EXTRA_HINTS + tuple(director._DOMAIN_HINTS)
    director._BAMO_SCENE_KIT = True
    return True
