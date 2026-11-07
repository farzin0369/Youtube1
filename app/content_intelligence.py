"""
BAMO Content Intelligence
------------------------
Central brain for daily English Shorts idea selection.

Responsibilities (planned):
1. Load available ideas from the idea bank
2. Optionally consider current trends (future)
3. Score candidates on novelty, visual potential, educational value, virality potential
4. Avoid recently used topics and near-duplicates
5. Return the single best idea for the day
6. Mark the chosen idea as used after successful production

This is a working skeleton. Scoring and trend integration will be expanded.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

IDEAS_PATH = Path(__file__).resolve().parents[1] / "data" / "ideas" / "ideas.jsonl"


@dataclass
class Idea:
    raw: dict[str, Any]

    @property
    def id(self) -> str:
        return self.raw["id"]

    @property
    def status(self) -> str:
        return self.raw.get("status", "available")

    @property
    def virality_score(self) -> float:
        return float(self.raw.get("virality_score", 5.0))

    @property
    def category(self) -> str:
        return self.raw.get("category", "")

    @property
    def title(self) -> str:
        return self.raw.get("title", "")


def load_ideas(path: Path = IDEAS_PATH) -> list[Idea]:
    if not path.exists():
        return []
    ideas: list[Idea] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ideas.append(Idea(json.loads(line)))
    return ideas


def available_ideas(ideas: list[Idea] | None = None) -> list[Idea]:
    if ideas is None:
        ideas = load_ideas()
    return [i for i in ideas if i.status == "available"]


def score_idea(idea: Idea) -> float:
    """
    Multi-criteria score (placeholder weights).
    Later: add trend boost, competition penalty, visual complexity, etc.
    """
    base = idea.virality_score
    # Prefer science / physics / math slightly for launch phase
    category_boost = 0.0
    cat = idea.category.lower()
    if any(k in cat for k in ("physics", "math", "science", "ai", "space")):
        category_boost = 0.4
    return base + category_boost + random.uniform(-0.1, 0.1)


def select_best_idea(ideas: list[Idea] | None = None) -> Optional[Idea]:
    candidates = available_ideas(ideas)
    if not candidates:
        return None
    ranked = sorted(candidates, key=score_idea, reverse=True)
    return ranked[0]


def mark_used(idea_id: str, path: Path = IDEAS_PATH) -> bool:
    """Mark an idea as used. Returns True if the idea was found and updated."""
    if not path.exists():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = False
    new_lines = []
    now = datetime.now(timezone.utc).isoformat()
    for line in lines:
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("id") == idea_id:
            obj["status"] = "used"
            obj["used_at"] = now
            updated = True
        new_lines.append(json.dumps(obj, ensure_ascii=False))
    if updated:
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return updated


def daily_brief() -> dict[str, Any]:
    """Return a simple daily production brief."""
    idea = select_best_idea()
    if idea is None:
        return {"error": "no_available_ideas", "message": "Idea bank is empty or all ideas are used."}
    return {
        "selected_idea_id": idea.id,
        "title": idea.title,
        "category": idea.category,
        "narration": idea.raw.get("narration"),
        "hook": idea.raw.get("hook"),
        "scenes": idea.raw.get("scenes"),
        "duration_seconds": idea.raw.get("duration_seconds"),
        "youtube_title": idea.raw.get("youtube_title"),
        "youtube_description": idea.raw.get("youtube_description"),
        "hashtags": idea.raw.get("hashtags"),
        "sources": idea.raw.get("sources"),
        "score": score_idea(idea),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    brief = daily_brief()
    print(json.dumps(brief, indent=2, ensure_ascii=False))
