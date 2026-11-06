"""
BAMO Smart Director (Python)
Lightweight port of the JS Director for the production pipeline.
Analyzes scene text → mood, palette, motif, camera hints.
"""
from __future__ import annotations

import re
from typing import Any

MOODS: dict[str, dict[str, Any]] = {
    "calm": {
        "id": "calm",
        "palette": {
            "bg": "#0c0a09", "primary": "#f5d0a9", "secondary": "#a78bfa",
            "accent": "#67e8f9", "particle": "rgba(245,208,169,0.5)", "glow": "rgba(245,208,169,0.2)",
        },
        "camera": {"type": "slow-dolly", "intensity": 0.3},
        "particles": {"density": 0.4, "type": "dust"},
        "light": {"rays": 0.3, "bloom": 0.5},
        "transition": "fade",
    },
    "epic": {
        "id": "epic",
        "palette": {
            "bg": "#0a0a12", "primary": "#fbbf24", "secondary": "#f472b6",
            "accent": "#38bdf8", "particle": "rgba(251,191,36,0.6)", "glow": "rgba(251,191,36,0.28)",
        },
        "camera": {"type": "orbit", "intensity": 0.7},
        "particles": {"density": 0.8, "type": "golden"},
        "light": {"rays": 0.9, "bloom": 0.85},
        "transition": "light-leak",
    },
    "mysterious": {
        "id": "mysterious",
        "palette": {
            "bg": "#0b0c15", "primary": "#818cf8", "secondary": "#c084fc",
            "accent": "#22d3ee", "particle": "rgba(129,140,248,0.45)", "glow": "rgba(129,140,248,0.22)",
        },
        "camera": {"type": "parallax", "intensity": 0.5},
        "particles": {"density": 0.55, "type": "stars"},
        "light": {"rays": 0.4, "bloom": 0.6},
        "transition": "particle-dissolve",
    },
    "energetic": {
        "id": "energetic",
        "palette": {
            "bg": "#0f172a", "primary": "#22d3ee", "secondary": "#f472b6",
            "accent": "#a3e635", "particle": "rgba(34,211,238,0.55)", "glow": "rgba(34,211,238,0.25)",
        },
        "camera": {"type": "shake-zoom", "intensity": 0.85},
        "particles": {"density": 0.9, "type": "sparks"},
        "light": {"rays": 0.7, "bloom": 0.75},
        "transition": "whip",
    },
    "sad": {
        "id": "sad",
        "palette": {
            "bg": "#0c1220", "primary": "#94a3b8", "secondary": "#64748b",
            "accent": "#7dd3fc", "particle": "rgba(148,163,184,0.35)", "glow": "rgba(125,211,252,0.15)",
        },
        "camera": {"type": "slow-zoom", "intensity": 0.25},
        "particles": {"density": 0.3, "type": "rain"},
        "light": {"rays": 0.15, "bloom": 0.35},
        "transition": "fade",
    },
    "futuristic": {
        "id": "futuristic",
        "palette": {
            "bg": "#020617", "primary": "#22d3ee", "secondary": "#a78bfa",
            "accent": "#e879f9", "particle": "rgba(34,211,238,0.5)", "glow": "rgba(167,139,250,0.25)",
        },
        "camera": {"type": "dolly", "intensity": 0.6},
        "particles": {"density": 0.7, "type": "grid"},
        "light": {"rays": 0.6, "bloom": 0.8},
        "transition": "morph",
    },
    "hopeful": {
        "id": "hopeful",
        "palette": {
            "bg": "#052e16", "primary": "#4ade80", "secondary": "#2dd4bf",
            "accent": "#facc15", "particle": "rgba(74,222,128,0.5)", "glow": "rgba(74,222,128,0.22)",
        },
        "camera": {"type": "slow-dolly", "intensity": 0.4},
        "particles": {"density": 0.6, "type": "golden"},
        "light": {"rays": 0.65, "bloom": 0.7},
        "transition": "fade",
    },
    "spiritual": {
        "id": "spiritual",
        "palette": {
            "bg": "#0c0a09", "primary": "#fbbf24", "secondary": "#f472b6",
            "accent": "#38bdf8", "particle": "rgba(251,191,36,0.5)", "glow": "rgba(251,191,36,0.22)",
        },
        "camera": {"type": "orbit", "intensity": 0.35},
        "particles": {"density": 0.5, "type": "dust"},
        "light": {"rays": 0.55, "bloom": 0.65},
        "transition": "light-leak",
    },
}

KEYWORD_MOOD = [
    (re.compile(r"صبر|آرامش|سکوت|آرام|صلح|peaceful|calm|gentle|soft", re.I), "calm"),
    (re.compile(r"حماسی|قهرمان|پیروزی|قدرت|عظیم|epic|hero|victory|power|glory", re.I), "epic"),
    (re.compile(r"رمز|مرموز|تاریک|پنهان|راز|mystery|dark|secret|shadow", re.I), "mysterious"),
    (re.compile(r"انرژی|سریع|هیجان|پرش|حرکت|energy|fast|excited|dynamic", re.I), "energetic"),
    (re.compile(r"غم|اندوه|فقدان|تنهایی|اشک|sad|grief|lonely|tear", re.I), "sad"),
    (re.compile(r"آینده|فناوری|فضا|سایبر|neon|future|cyber|space|tech", re.I), "futuristic"),
    (re.compile(r"امید|رشد|پیشرفت|نور|طلوع|hope|growth|light|dawn|rise", re.I), "hopeful"),
    (re.compile(r"توکل|دعا|قلب|معنویت|ایمان|روح|spiritual|faith|soul|prayer", re.I), "spiritual"),
]


def detect_mood(text: str) -> dict[str, Any]:
    t = text or ""
    for pattern, mood_id in KEYWORD_MOOD:
        if pattern.search(t):
            return MOODS[mood_id]
    return MOODS["spiritual"]


def guess_motif(text: str) -> str:
    t = (text or "").lower()
    if re.search(r"بیضی|کانون|ellipse|focus|foci", t):
        return "ellipse"
    if re.search(r"موج|تداخل|wave|interference|phase", t):
        return "wave"
    if re.search(r"مسیر|قدم|راه|path|step|journey|road", t):
        return "path"
    if re.search(r"نور|طلوع|light|sun|dawn|glow|hope", t):
        return "light"
    if re.search(r"انتخاب|دو راه|choice|decision|fork", t):
        return "choice"
    if re.search(r"ستاره|فضا|کیهان|star|cosmic|space|galaxy", t):
        return "cosmic"
    if re.search(r"رشد|درخت|growth|tree|plant", t):
        return "growth"
    return "abstract"


def enrich_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """Add mood, palette, motif, camera to a pipeline scene dict."""
    narration = str(scene.get("spoken_text") or scene.get("narration") or "")
    visual = str(scene.get("visual_query") or scene.get("visual_prompt") or "")
    overlay = str(scene.get("on_screen_text") or scene.get("text") or "")
    blob = f"{narration} {visual} {overlay}"

    mood = detect_mood(blob)
    motif = guess_motif(blob)

    out = dict(scene)
    out["narration"] = narration
    out["text"] = overlay or narration[:48]
    out["visual_prompt"] = visual or motif
    out["motif"] = motif
    out["mood"] = mood["id"]
    out["palette"] = mood["palette"]
    out["camera"] = mood["camera"]
    out["particles"] = mood["particles"]
    out["light"] = mood["light"]
    out["transition"] = mood["transition"]
    return out


def enrich_project(project: dict[str, Any]) -> dict[str, Any]:
    """Enrich all scenes in a render project."""
    scenes = project.get("scenes") or []
    enriched = [enrich_scene(s) for s in scenes]
    out = dict(project)
    out["scenes"] = enriched
    if enriched:
        out["globalMood"] = enriched[0].get("mood", "spiritual")
    return out
