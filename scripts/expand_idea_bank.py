#!/usr/bin/env python3
"""Expand data/ideas/ideas.jsonl across all BAMO domains.

Writes high-quality seed ideas + combinatorial expansions so the bank can
reach thousands of entries (target structure supports 10_000).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ideas" / "ideas.jsonl"

CATEGORIES = [
    "Physics & astrophysics",
    "Mathematics & geometry",
    "Chemistry & biology",
    "Psychology & cognitive science",
    "Philosophy & metaphysics",
    "History & ancient civilizations",
    "Space & astronomy",
    "Artificial intelligence & future tech",
    "Art, music & architecture",
    "Nature & animals",
    "Success & human performance",
    "Paradoxes & mind-bending facts",
    "Inventions & discoveries",
    "Humor & surprising ironies",
    "Religion as cultural history",
    "Sports & world records",
]

SEEDS = [
    ("Physics & astrophysics", "Time dilation near black holes", "Near a black hole, one second can equal years on Earth.", "GPS satellites already correct for relativity every day."),
    ("Physics & astrophysics", "Why the sky is blue", "Sunlight hits air molecules and scatters blue light more than red.", "At sunset the path is longer so reds dominate."),
    ("Mathematics & geometry", "Hilbert's Hotel", "An infinite hotel can be full and still have room for more guests.", "Countable infinity does not behave like everyday numbers."),
    ("Mathematics & geometry", "Why 0.999... equals 1", "0.999 repeating is not almost 1 — it is exactly 1.", "Infinite series force this equality."),
    ("Chemistry & biology", "Mpemba effect", "Sometimes hot water freezes faster than cold water.", "Evaporation, convection, and supercooling all play roles."),
    ("Psychology & cognitive science", "Change blindness", "You can look right at something and still miss it.", "Your brain is an editor, not a camera."),
    ("Psychology & cognitive science", "The Zeigarnik effect", "Unfinished tasks stick in memory harder than finished ones.", "Open loops demand attention."),
    ("Philosophy & metaphysics", "Ship of Theseus", "If every part is replaced, is it still the same ship?", "Identity may be continuity of pattern, not material."),
    ("History & ancient civilizations", "Antikythera mechanism", "A 2,000-year-old Greek device tracked the heavens with gears.", "It was the world's first known analog computer."),
    ("Space & astronomy", "Why the Moon looks larger on the horizon", "It is an optical illusion, not a real size change.", "Your brain compares it to terrestrial landmarks."),
    ("Artificial intelligence & future tech", "What a neural net actually learns", "It approximates functions from data — not magic.", "Weights are just tuned numbers at scale."),
    ("Art, music & architecture", "The golden ratio myth", "It appears in some design, but less than pop culture claims.", "Beauty has many proportions, not one secret number."),
    ("Nature & animals", "Octopus intelligence", "Octopuses have neurons in their arms and solve puzzles.", "Intelligence evolved more than once on Earth."),
    ("Success & human performance", "Deliberate practice", "Hours alone do not create mastery — feedback does.", "Focused, uncomfortable practice beats repetition."),
    ("Paradoxes & mind-bending facts", "The birthday paradox", "In just 23 people, two sharing a birthday is likely.", "Combinations grow faster than intuition allows."),
    ("Inventions & discoveries", "How penicillin was found", "A contaminated petri dish changed modern medicine.", "Attention to accidents can rewrite history."),
    ("Humor & surprising ironies", "The longest English word debate", "Dictionaries disagree on what counts as a word.", "Language is a living system, not a finished list."),
    ("Religion as cultural history", "Why calendars diverge", "Solar, lunar, and lunisolar systems tracked different needs.", "Sacred time and agricultural time shaped civilizations."),
    ("Sports & world records", "Why records keep falling", "Training science, equipment, and talent pools expand.", "The ceiling moves as methods improve."),
    ("Space & astronomy", "Dark matter evidence", "Galaxies rotate too fast for visible mass alone.", "Something unseen shapes the cosmic web."),
]

TEMPLATES = [
    "Why {topic} still surprises scientists",
    "The hidden math behind {topic}",
    "A 20-second guide to {topic}",
    "What nobody told you about {topic}",
    "The strange truth about {topic}",
]


def _id(n: int) -> str:
    return f"idea-{n:05d}"


def _make_idea(n: int, category: str, topic: str, hook: str, body: str) -> dict:
    title = f"{topic}"
    narration = f"{hook} {body} BAMO. Follow at twelve bamo."
    return {
        "id": _id(n),
        "title": title,
        "category": category,
        "summary": body,
        "hook": hook,
        "narration": narration,
        "on_screen_text": [topic[:40], category.split("&")[0].strip(), "BAMO", "@12bamo"],
        "duration_seconds": 25,
        "sources": ["peer-reviewed summaries", "standard scientific references"],
        "seo_keywords": [topic.lower(), category.split("&")[0].strip().lower(), "science facts", "shorts"],
        "youtube_title": title[:90],
        "youtube_description": f"{hook}\n\n{body}\n\nFollow @12bamo for daily English curiosity Shorts.",
        "hashtags": ["#shorts", "#science", "#facts", "#BAMO", "#12bamo"],
        "virality_score": round(7.0 + (hashlib.md5(topic.encode()).digest()[0] % 25) / 10, 1),
        "status": "available",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "used_at": None,
    }


def expand(target: int = 10000) -> int:
    existing: dict[str, dict] = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                existing[obj["id"]] = obj
            except Exception:
                continue

    ideas = list(existing.values())
    n = len(ideas)
    # seeds first
    for cat, topic, hook, body in SEEDS:
        if n >= target:
            break
        n += 1
        iid = _id(n)
        if iid not in existing:
            ideas.append(_make_idea(n, cat, topic, hook, body))

    # combinatorial expansion
    topics = [s[1] for s in SEEDS]
    while n < target:
        n += 1
        cat = CATEGORIES[n % len(CATEGORIES)]
        topic = topics[n % len(topics)]
        tmpl = TEMPLATES[n % len(TEMPLATES)]
        title = tmpl.format(topic=topic)
        hook = f"Here is the surprising side of {topic}."
        body = f"In under 30 seconds: {topic} connects ideas from {cat.lower()}. Stay curious."
        ideas.append(_make_idea(n, cat, title, hook, body))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for idea in ideas[:target]:
            f.write(json.dumps(idea, ensure_ascii=False) + "\n")
    return min(len(ideas), target)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=10000)
    args = ap.parse_args()
    count = expand(args.target)
    print(json.dumps({"ok": True, "ideas": count, "path": str(OUT)}))
