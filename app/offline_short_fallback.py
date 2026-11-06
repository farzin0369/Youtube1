"""Deterministic offline Shorts draft when cloud LLM is unavailable.

Used so dry-run / factory can still exercise TTS + motion render path.
Passes validate_short_content gates in app.spiritual_shorts.
"""
from __future__ import annotations

from typing import Any


def offline_short_item() -> dict[str, Any]:
    """Return one valid 4-scene Persian Shorts JSON object."""
    scenes = [
        {
            "spoken_text": "چرا بعضی روزها فقط باید صبر کنی؟",
            "mood": "hook",
            "visual_query": "person waiting quiet morning window",
            "on_screen_text": "گاهی فقط صبر",
        },
        {
            "spoken_text": "وقتی نتیجه را نمی‌بینی، باز هم هر قدم کوچک بخشی از راه است.",
            "mood": "calm",
            "visual_query": "footsteps path forest sunrise",
            "on_screen_text": "هر قدم بخشی از راه",
        },
        {
            "spoken_text": "امروز یک کار کوچک انجام بده و همان را تمام کن.",
            "mood": "reassuring",
            "visual_query": "hands writing journal desk light",
            "on_screen_text": "یک کار کوچک امروز",
        },
        {
            "spoken_text": "نور امید برمی‌گردد؛ تو قوی‌تری از آنچه فکر می‌کنی.",
            "mood": "motivational",
            "visual_query": "sunrise mountain landscape golden light",
            "on_screen_text": "تو قوی‌تری",
        },
    ]
    script = " ".join(s["spoken_text"] for s in scenes)
    return {
        "topic": "صبر و اقدام کوچک",
        "title": "BAMO | چرا بعضی روزها فقط باید صبر کنی؟",
        "hook": scenes[0]["spoken_text"],
        "description": "درباره صبر و اقدام کوچک: وقتی نتیجه دیر می‌آید، قدم‌های کوچک راه را می‌سازند و امید برمی‌گردد.",
        "thumbnail_text": "صبر و قدم",
        "tags": ["صبر", "اقدام کوچک", "امید", "رشد فردی", "shorts", "patience", "hope"],
        "scenes": scenes,
        "script": script,
    }
