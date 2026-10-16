"""Map Persian spiritual narration to English cinematic visual prompts.

Used by Mixkit keyword selection and by GPU AI engines (Wan / CogVideoX / Hunyuan).
No API keys — pure deterministic mapping + light templates.
"""
from __future__ import annotations

import hashlib
import re
from typing import Iterable

# Theme → list of cinematic English shot ideas (vertical short-friendly)
_THEME_SHOTS: dict[str, list[str]] = {
    "توکل": [
        "cloaked figure walking slowly through a vast candle-lit stone hall, golden light cracks forming under each footstep, cinematic volumetric light",
        "wide shot of a lonely traveler on a mountain ridge at dawn, soft golden clouds, calm determined posture",
        "close-up of open hands releasing glowing particles into dark air, spiritual atmosphere, shallow depth of field",
    ],
    "نفس": [
        "slow motion close-up of a person taking a deep breath in a misty forest, soft morning light through trees",
        "calm lake surface reflecting sky, gentle ripples, peaceful solitude, cinematic",
        "silhouette of a figure standing still as fog moves around them, serene, natural light",
    ],
    "صبر": [
        "single candle flame burning steadily in a dark quiet room, subtle camera push-in",
        "rain on a window with soft indoor warm light, contemplative mood",
        "hourglass sand falling slowly in soft side light, shallow depth of field",
    ],
    "شکر": [
        "golden sunrise over quiet fields, warm rays, hopeful atmosphere",
        "hands cupped under soft sunlight, floating dust motes, gratitude mood",
        "birds rising from a tree at dawn, wide cinematic sky",
    ],
    "قدم": [
        "boots taking one careful step on a wet stone path, glowing trail behind, cathedral atmosphere",
        "narrow forest trail ahead, soft god-rays through canopy, walking forward",
        "stone bridge over a quiet river at dusk, lone figure mid-crossing",
    ],
    "نور": [
        "tree of luminous golden roots growing from a person's chest in a dark hall, cinematic fantasy realism",
        "beam of light breaking through heavy clouds onto a single path",
        "lantern held in darkness, warm glow on stone walls, slow camera orbit",
    ],
    "آرام": [
        "still desert dunes at blue hour, soft wind, vast silence",
        "empty courtyard with a single olive tree and soft afternoon light",
        "ocean horizon at sunset, gentle waves, calm palette",
    ],
    "دعا": [
        "silhouette of raised hands against moonlit window, spiritual calm",
        "rows of soft candle flames in a dark sacred hall, shallow depth of field",
        "night sky full of stars above a quiet hillside, long exposure feel",
    ],
    "امید": [
        "small green sprout breaking through dry soil toward sunlight",
        "light appearing at the end of a long dark tunnel, hopeful",
        "first sunlight after a storm over wet rooftops",
    ],
    "تلاش": [
        "climber reaching a ridge at sunrise, determined silhouette",
        "hands working soil in early morning light, honest labor",
        "long road toward mountains, traveler walking steadily",
    ],
    "زمان": [
        "clock hands moving slowly over a blurred city at dusk",
        "sun moving across the sky in subtle time-lapse, contemplative",
        "empty chair by a window as daylight fades, quiet urgency",
    ],
}

_DEFAULT_SHOTS = [
    "cinematic portrait of a calm spiritual journey, soft volumetric light, natural motion",
    "atmospheric documentary shot of peaceful nature path at golden hour",
    "slow camera move through candle-lit ancient stone interior, reverent mood",
    "wide landscape at dawn with a single distant figure, hopeful silence",
]

_STYLE = (
    "cinematic realistic footage, natural motion, atmospheric practical lighting, "
    "smooth subtle camera movement, detailed environment, filmic color grading, "
    "vertical 9:16 composition, no text, no captions, no logo, no watermark"
)

_NEGATIVE = (
    "subtitles, letters, watermark, logo, static image, flicker, jitter, "
    "distorted anatomy, cartoon, overexposed, low quality"
)


def _themes_in(text: str) -> list[str]:
    found: list[str] = []
    for theme in _THEME_SHOTS:
        if theme in text:
            found.append(theme)
    return found


def cinematic_prompt_for_scene(
    spoken_text: str,
    *,
    scene_index: int = 0,
    topic: str = "",
) -> str:
    """One English cinematic prompt aligned to Persian spoken meaning."""
    blob = f"{topic} {spoken_text}".strip()
    themes = _themes_in(blob)
    pool: list[str] = []
    for th in themes:
        pool.extend(_THEME_SHOTS[th])
    if not pool:
        pool = list(_DEFAULT_SHOTS)
    # Stable pick per scene text
    h = int(hashlib.sha1(f"{scene_index}:{blob}".encode("utf-8")).hexdigest()[:8], 16)
    shot = pool[h % len(pool)]
    return f"{shot}, {_STYLE}"


def cinematic_prompts_for_scenes(
    scenes: Iterable[str],
    *,
    topic: str = "",
) -> list[str]:
    return [
        cinematic_prompt_for_scene(str(s), scene_index=i, topic=topic)
        for i, s in enumerate(scenes)
    ]


def mixkit_keywords_from_scenes(
    scenes: Iterable[str],
    *,
    topic: str = "",
    count: int = 4,
) -> list[str]:
    """Short English search keywords for free Mixkit, diversified by scene meaning."""
    prompts = cinematic_prompts_for_scenes(scenes, topic=topic)
    keys: list[str] = []
    # Pull 3-4 concrete nouns/phrases from each prompt for search
    for p in prompts:
        tokens = re.findall(
            r"\b(candle|forest|sunrise|mountain|ocean|path|hands|light|desert|bridge|rain|clouds|moon|stars|field|tunnel|sprout)\b",
            p.lower(),
        )
        if tokens:
            keys.append(" ".join(tokens[:3]))
        else:
            keys.append("calm nature sunrise")
    # dedupe preserve order
    out: list[str] = []
    for k in keys:
        if k not in out:
            out.append(k)
    while len(out) < count:
        out.append(_DEFAULT_SHOTS[len(out) % len(_DEFAULT_SHOTS)].split(",")[0][:40])
    return out[: max(count, 4)]


def negative_prompt() -> str:
    return _NEGATIVE
