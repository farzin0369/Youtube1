"""Deterministic Persian narration segmentation and emotion/intensity tagging.

This is a lightweight, explainable heuristic. It does not claim to infer nuanced
human emotion; callers should treat labels as delivery hints and allow a neutral
fallback when confidence is low.
"""
from __future__ import annotations

import re
from typing import Any

EMOTIONS = {"angry", "motivational", "calm", "reassuring", "sad", "joyful", "neutral"}

# Cues are intentionally modest and phrase-level. Add project-specific vocabulary
# here rather than introducing an unbounded model dependency into the render path.
_CUES: dict[str, tuple[str, ...]] = {
    "angry": ("عصبانی", "خشم", "خشمگین", "کلافه", "بس کن", "تحمل", "نفرت", "ظلم", "بی‌عدالتی", "دیگه بسه"),
    "motivational": ("ادامه بده", "می‌توانی", "می‌تونی", "شروع کن", "قدم", "بلند شو", "تسلیم نشو", "از نو", "پیش برو", "امید", "هدف", "بساز", "اقدام"),
    "calm": ("آرام", "نفس", "مکث", "آهسته", "سکوت", "آسوده", "استراحت", "ذهن", "امشب", "نفس عمیق"),
    "reassuring": ("نگران نباش", "تنها نیستی", "اشکالی ندارد", "لازم نیست", "کافیست", "کافیه", "طبیعی است", "درکت می‌کنم", "به خودت سخت نگیر", "همین قدر"),
    "sad": ("غم", "غمگین", "دلتنگ", "تنهایی", "اشک", "خسته", "شکست", "از دست", "درد", "ناامید"),
    "joyful": ("خوشحال", "شادی", "لبخند", "شاد", "جشن", "سپاسگزار", "خوشبخت", "عالیه"),
}

# A few common Persian/Arabic character variants are normalized for matching only;
# returned segment text remains byte-for-byte equivalent to the original substring.
def _norm(value: str) -> str:
    value = value.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه")
    value = value.replace("أ", "ا").replace("إ", "ا").replace("ؤ", "و")
    return re.sub(r"\s+", " ", value).strip().casefold()


def _split_spans(text: str) -> list[tuple[int, int]]:
    """Split at sentence/clause punctuation, retaining punctuation in each span."""
    spans: list[tuple[int, int]] = []
    start = 0
    # Strong breaks always split. Commas and colons split only when followed by
    # a sufficiently substantial clause, avoiding fragments such as "اما، ...".
    for match in re.finditer(r"[.!?؟؛،,:]+(?=\s+|$)", text):
        end = match.end()
        candidate = text[start:end].strip()
        following = text[end:].lstrip()
        strong = any(char in match.group() for char in ".!?؟؛")
        if not candidate:
            start = end
            continue
        if strong or (len(candidate.split()) >= 4 and len(following.split()) >= 3):
            left = start
            while left < end and text[left].isspace():
                left += 1
            if left < end:
                spans.append((left, end))
            start = end
    tail = text[start:]
    left = start
    while left < len(text) and text[left].isspace():
        left += 1
    if text[left:].strip():
        spans.append((left, len(text.rstrip())))
    # Merge tiny punctuation-created fragments with the next segment.
    merged: list[tuple[int, int]] = []
    for span in spans:
        previous = text[merged[-1][0]:merged[-1][1]].rstrip() if merged else ""
        previous_is_sentence_end = bool(re.search(r"[.!?؟؛]$", previous))
        if merged and len(previous.split()) < 3 and not previous_is_sentence_end:
            merged[-1] = (merged[-1][0], span[1])
        else:
            merged.append(span)
    return merged


def classify_emotion(text: str) -> dict[str, Any]:
    """Return a conservative emotion label, confidence and normalized intensity."""
    normalized = _norm(text)
    scores = {emotion: 0.0 for emotion in _CUES}
    matched: dict[str, list[str]] = {emotion: [] for emotion in _CUES}
    for emotion, cues in _CUES.items():
        for cue in cues:
            if _norm(cue) in normalized:
                scores[emotion] += 1.0
                matched[emotion].append(cue)

    # Punctuation/lexical emphasis adjust intensity slightly, never determine emotion alone.
    emphatic = min(0.20, normalized.count("!") * 0.06 + normalized.count("؟") * 0.025)
    intensifiers = ("خیلی", "واقعاً", "هرگز", "همین حالا", "فوراً", "اصلاً")
    intensity_boost = min(0.16, sum(normalized.count(word) for word in intensifiers) * 0.04)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    emotion, top = ranked[0]
    second = ranked[1][1]
    if top <= 0:
        emotion = "neutral"
        confidence = 0.35
        intensity = 0.30
    else:
        confidence = min(0.95, 0.55 + 0.12 * top + 0.08 * max(0.0, top - second))
        base = {"angry": 0.58, "motivational": 0.62, "calm": 0.42,
                "reassuring": 0.43, "sad": 0.50, "joyful": 0.58}[emotion]
        intensity = min(0.90, max(0.20, base + emphatic + intensity_boost))

    # Neutralize a potentially harmful overreaction: one anger cue in reassuring copy
    # should not make a whole sentence sound angry if reassurance cues are stronger.
    if emotion == "angry" and scores.get("reassuring", 0) > top:
        emotion = "reassuring"

    pace = "brisk" if emotion in {"angry", "motivational", "joyful"} else "slow" if emotion in {"calm", "sad", "reassuring"} else "steady"
    pause_after_ms = 520 if re.search(r"[.!?؟؛]$", text.strip()) else 300 if re.search(r"[,،:]$", text.strip()) else 180
    return {
        "emotion": emotion,
        "intensity": round(intensity, 2),
        "confidence": round(confidence, 2),
        "pace": pace,
        "pause_after_ms": pause_after_ms,
        "matched_cues": matched.get(emotion, []),
        "method": "persian_lexical_rules_v1",
    }


def segment_and_tag(text: str) -> list[dict[str, Any]]:
    """Split Persian narration and attach explainable emotion/intensity hints.

    Each item includes exact source character offsets and original text, so this
    metadata can be aligned to word-boundary captions or audio segments.
    """
    source = str(text or "")
    segments: list[dict[str, Any]] = []
    for start, end in _split_spans(source):
        value = source[start:end].strip()
        if not value:
            continue
        # Account for leading whitespace trimmed above while preserving offsets.
        actual_start = start + len(source[start:end]) - len(source[start:end].lstrip())
        label = classify_emotion(value)
        segments.append({
            "text": value,
            "start_char": actual_start,
            "end_char": actual_start + len(value),
            **label,
        })
    return segments


def scene_delivery_hint(segments: list[dict[str, Any]]) -> dict[str, Any]:
    """Choose a conservative scene-level TTS hint from its strongest segment."""
    if not segments:
        return classify_emotion("")
    chosen = max(segments, key=lambda row: (float(row.get("intensity", 0)) * float(row.get("confidence", 0)), float(row.get("confidence", 0))))
    return {key: chosen[key] for key in ("emotion", "intensity", "confidence", "pace", "pause_after_ms", "method") if key in chosen}
