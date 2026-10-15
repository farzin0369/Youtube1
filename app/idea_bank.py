"""Curated Shorts idea bank: validated scripts for reliable daily production."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from app.spiritual_shorts import validate_short_content

LOGGER = logging.getLogger(__name__)

DEFAULT_BANK_PATH = Path(__file__).resolve().parents[1] / "data" / "shorts_idea_bank.json"
STATE_KEY_NEXT = "idea_bank_next_index"


def _bank_path() -> Path:
    env = (os.getenv("SHORTS_IDEA_BANK_PATH") or "").strip()
    return Path(env) if env else DEFAULT_BANK_PATH


def load_bank() -> list[dict[str, Any]]:
    path = _bank_path()
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    ideas = payload.get("ideas") if isinstance(payload, dict) else payload
    if not isinstance(ideas, list):
        return []
    return [row for row in ideas if isinstance(row, dict)]


def next_bank_idea(history: dict[str, Any]) -> dict[str, Any] | None:
    """Return the next unused curated idea, validated against current QA rules."""
    ideas = load_bank()
    if not ideas:
        return None
    recent = history.get("recent", []) if isinstance(history, dict) else []
    titles = [str(row.get("title") or "") for row in recent[-30:] if isinstance(row, dict)]
    used_ids = {
        str(row.get("idea_id") or "")
        for row in recent
        if isinstance(row, dict) and row.get("idea_id")
    }
    try:
        start = int(history.get(STATE_KEY_NEXT) or 0)
    except (TypeError, ValueError):
        start = 0
    start = max(0, start) % max(len(ideas), 1)
    order = list(range(start, len(ideas))) + list(range(0, start))
    for idx in order:
        raw = ideas[idx]
        idea_id = str(raw.get("id") or f"bank-{idx + 1}")
        if idea_id in used_ids:
            continue
        try:
            validated = validate_short_content(raw, titles)
        except (ValueError, TypeError) as exc:
            LOGGER.warning("bank idea %s failed QA and was skipped (%s)", idea_id, str(exc)[:120])
            continue
        validated["generated_by"] = "idea-bank"
        validated["idea_id"] = idea_id
        history[STATE_KEY_NEXT] = idx + 1
        LOGGER.info(
            "selected curated idea id=%s topic=%r words=%s",
            idea_id,
            validated.get("topic"),
            validated.get("word_count"),
        )
        return validated
    return None
