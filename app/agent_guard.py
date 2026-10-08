"""Production safety/quality gate for the private ImamAli110 agent."""
from __future__ import annotations
from typing import Any

BRAND_TAGS = ["#ImamAli110", "#The110Path", "#ImamAli"]
FORBIDDEN = ["نفرت", "توهین", "تهدید", "خودکشی", "محتوای جنسی"]

def validate_package(data: dict[str, Any], kind: str) -> dict[str, Any]:
    title = str(data.get("title") or "").strip()
    script = str(data.get("script") or "").strip()
    tags = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()]
    sources = [str(x).strip() for x in (data.get("sources") or []) if str(x).strip()]
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
