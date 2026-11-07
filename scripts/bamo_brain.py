#!/usr/bin/env python3
"""BAMO Content Intelligence: pick one unused idea, build YouTube metadata."""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IDEAS = ROOT / "data" / "ideas" / "ideas.jsonl"
HISTORY = ROOT / "data" / "publish_history.jsonl"

DEFAULT_HASHTAGS = [
    "#shorts",
    "#science",
    "#facts",
    "#learning",
    "#BAMO",
    "#12bamo",
]


def _load_ideas() -> list[dict[str, Any]]:
    if not IDEAS.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in IDEAS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _save_ideas(ideas: list[dict[str, Any]]) -> None:
    IDEAS.parent.mkdir(parents=True, exist_ok=True)
    with IDEAS.open("w", encoding="utf-8") as f:
        for idea in ideas:
            f.write(json.dumps(idea, ensure_ascii=False) + "\n")


def select_idea(
    *,
    prefer_category: str | None = None,
    prefer_curated: bool = True,
) -> dict[str, Any]:
    ideas = _load_ideas()
    available = [i for i in ideas if (i.get("status") or "available") == "available"]

    if prefer_curated:
        curated = [i for i in available if i.get("curated") is True]
        if curated:
            available = curated

    if prefer_category:
        cat = [i for i in available if prefer_category.lower() in (i.get("category") or "").lower()]
        if cat:
            available = cat

    if not available:
        used = [i for i in ideas if i.get("status") == "used"]
        if not used:
            raise RuntimeError("Idea bank empty. Run scripts/expand_idea_bank.py first.")
        pool = [i for i in used if i.get("curated") is True] or used
        available = sorted(pool, key=lambda x: float(x.get("virality_score") or 0), reverse=True)[:40]
        for i in available:
            i["status"] = "available"
            i["used_at"] = None

    available.sort(
        key=lambda x: (1 if x.get("curated") else 0, float(x.get("virality_score") or 0)),
        reverse=True,
    )
    top = available[: max(8, min(25, len(available)))]
    return random.choice(top)


def mark_used(idea_id: str) -> None:
    ideas = _load_ideas()
    now = datetime.now(timezone.utc).isoformat()
    for i in ideas:
        if i.get("id") == idea_id:
            i["status"] = "used"
            i["used_at"] = now
            break
    _save_ideas(ideas)


def build_youtube_package(idea: dict[str, Any]) -> dict[str, Any]:
    title = (idea.get("youtube_title") or idea.get("title") or "Amazing Fact").strip()
    if len(title) > 95:
        title = title[:92] + "..."

    description = (idea.get("youtube_description") or idea.get("summary") or "").strip()
    hook = (idea.get("hook") or "").strip()
    narration = (idea.get("narration") or "").strip()
    sources = idea.get("sources") or []
    hashtags = list(idea.get("hashtags") or [])
    for h in DEFAULT_HASHTAGS:
        if h not in hashtags:
            hashtags.append(h)
    hashtags = hashtags[:15]

    tags = list(idea.get("seo_keywords") or [])
    tags.extend(["shorts", "science facts", "BAMO", "12bamo", "educational shorts"])
    seen: set[str] = set()
    clean_tags: list[str] = []
    for t in tags:
        k = t.lower().strip()
        if k and k not in seen:
            seen.add(k)
            clean_tags.append(t.strip()[:30])
    clean_tags = clean_tags[:20]

    desc_parts = [
        description,
        "",
        hook,
        "",
        "Sources:",
    ]
    for s in sources[:5]:
        desc_parts.append(f"• {s}")
    desc_parts.extend([
        "",
        "Follow @12bamo for daily English science & curiosity Shorts.",
        " ".join(hashtags),
    ])
    full_description = "\n".join(desc_parts)[:4900]

    return {
        "idea_id": idea.get("id"),
        "title": title,
        "description": full_description,
        "tags": clean_tags,
        "hashtags": hashtags,
        "category_id": "27",
        "narration": narration,
        "hook": hook,
        "category": idea.get("category"),
        "duration_seconds": int(idea.get("duration_seconds") or 25),
    }


def append_history(record: dict[str, Any]) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    idea = select_idea()
    pkg = build_youtube_package(idea)
    print(json.dumps({"idea": {"id": idea.get("id"), "title": idea.get("title")}, "package": pkg}, ensure_ascii=False, indent=2))
