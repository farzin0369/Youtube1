"""Production safety/quality gate for the private ImamAli110 agent."""
from __future__ import annotations
from typing import Any

BRAND_TAGS = ["#ImamAli110", "#The110Path", "#ImamAli"]
FORBIDDEN = ["خودکشی", "محتوای جنسی", "porn", "sexual content"]

def validate_package(data: dict[str, Any], kind: str) -> dict[str, Any]:
    title = str(data.get("title") or "").strip()
    script = str(data.get("script") or "").strip()
    tags = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()]
    sources = [str(x).strip() for x in (data.get("sources") or []) if str(x).strip()]
    scenes = data.get("scene_plan") if isinstance(data.get("scene_plan"), list) else []
    errors: list[str] = []
    warnings: list[str] = []

    if not title:
        errors.append("missing_title")
    elif not title.startswith("Imam Ali ✨"):
        errors.append("title_must_start_with_Imam_Ali")
    if not script:
        errors.append("missing_script")
    if not sources:
        errors.append("missing_sources")
    if not scenes:
        errors.append("missing_scene_plan")
    else:
        spoken: list[str] = []
        for index, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                errors.append(f"invalid_scene_{index}")
                continue
            for key in ("spoken_text", "visual_prompt", "on_screen_text"):
                if not str(scene.get(key) or "").strip():
                    errors.append(f"scene_{index}_missing_{key}")
            if len(str(scene.get("on_screen_text") or "").split()) > 8:
                errors.append(f"scene_{index}_on_screen_text_too_long")
            try:
                if float(scene.get("duration_hint_seconds") or 0) <= 0:
                    errors.append(f"scene_{index}_invalid_duration")
            except (TypeError, ValueError):
                errors.append(f"scene_{index}_invalid_duration")
            spoken.append(str(scene.get("spoken_text") or "").strip())
        if spoken and " ".join(spoken) != script:
            errors.append("script_must_equal_scene_spoken_text")
    if kind == "short" and not (30 <= int(data.get("duration_hint_seconds") or 0) <= 60):
        warnings.append("short_duration_hint_outside_30_60")
    if not any("امام علی" in t.lower() or "imam ali" in t.lower() for t in tags):
        warnings.append("missing_imam_ali_tag")
    if not any("نهج" in s or "قرآن" in s or "قرآن کریم" in s for s in sources):
        warnings.append("source_not_recognized_by_gate")
    lower = (title + " " + script).lower()
    if any(x in lower for x in FORBIDDEN):
        errors.append("forbidden_content_detected")

    return {"ok": not errors, "errors": errors, "warnings": warnings}

def enforce(data: dict[str, Any], kind: str) -> dict[str, Any]:
    result = validate_package(data, kind)
    if not result["ok"]:
        raise RuntimeError("Production quality gate failed: " + ", ".join(result["errors"]))
    data["tags"] = list(dict.fromkeys(BRAND_TAGS + [str(x) for x in (data.get("tags") or [])]))[:20]
    data["quality_gate"] = result
    return data
