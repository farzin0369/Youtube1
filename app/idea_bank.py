"""Deterministic short-script packs so production can reach LTX without LLM."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from app.spiritual_shorts import validate_short_content
from app.utils import ROOT

BANK_PATH = ROOT / "config" / "idea_bank_shorts.json"


def _load_bank() -> list[dict[str, Any]]:
    raw = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    items = raw.get("items") if isinstance(raw, dict) else None
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"idea bank empty or invalid: {BANK_PATH}")
    return [item for item in items if isinstance(item, dict)]


def idea_bank_enabled() -> bool:
    flag = (os.getenv("USE_IDEA_BANK") or "").strip().lower()
    return flag in {"1", "true", "yes", "always", "only"}


def pick_idea_bank_content(history: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return one validated short pack from the bank, preferring unused topics."""
    items = _load_bank()
    recent = history.get("recent", []) if isinstance(history, dict) else []
    used_topics = {
        re.sub(r"\s+", "", str(row.get("topic") or row.get("title") or "").casefold())
        for row in recent[-40:]
        if isinstance(row, dict)
    }
    ordered = sorted(
        items,
        key=lambda item: (
            re.sub(r"\s+", "", str(item.get("topic") or "").casefold()) in used_topics,
            str(item.get("topic") or ""),
        ),
    )
    last_error = ""
    for item in ordered:
        try:
            payload = dict(item)
            scenes = payload.get("scenes")
            if isinstance(scenes, list) and len(scenes) == 4:
                lines = [
                    re.sub(r"\s+", " ", str(scene.get("spoken_text") or "")).strip()
                    for scene in scenes
                    if isinstance(scene, dict)
                ]
                if len(lines) == 4 and all(lines):
                    payload["script"] = " ".join(lines)
            result = validate_short_content(
                payload,
                [str(r.get("title") or "") for r in recent if isinstance(r, dict)],
                min_words=20,
                max_words=60,
            )
            result["generated_by"] = "idea_bank"
            result["idea_bank_topic"] = str(item.get("topic") or result.get("topic") or "")
            return result
        except (ValueError, TypeError) as exc:
            last_error = str(exc)
            continue
    raise RuntimeError("no idea-bank item passed QA: " + last_error[:240])
