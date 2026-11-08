"""Text analysis for Text-to-Video engine.

Detects language, segments sentences/paragraphs, extracts keywords,
infer tone, and suggests visual search queries + music mood.

Designed to work offline with heuristics. Optional LLM hook later.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Tone = Literal["neutral", "educational", "upbeat", "dramatic", "calm", "urgent"]
Lang = Literal["fa", "en", "mixed", "unknown"]

# Minimal stopword lists (FA + EN) — enough for keyword ranking without NLTK
_STOP_EN = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "is", "are",
    "was", "were", "be", "been", "being", "it", "this", "that", "with", "as", "by", "from",
    "you", "your", "we", "they", "he", "she", "his", "her", "their", "our", "not", "no",
    "can", "will", "just", "about", "into", "than", "then", "so", "if", "when", "what",
    "which", "who", "how", "why", "all", "each", "every", "more", "most", "some", "such",
    "only", "own", "same", "than", "too", "very", "also", "do", "does", "did", "have",
    "has", "had", "here", "there", "these", "those", "them", "its", "my", "me", "us",
}

_STOP_FA = {
    "و", "در", "به", "از", "که", "این", "را", "با", "برای", "تا", "یک", "است", "هست",
    "بود", "شد", "می", "هم", "یا", "اگر", "اما", "نه", "آن", "او", "ما", "شما", "آنها",
    "هر", "چی", "چه", "چرا", "چگونه", "کجا", "کی", "ولی", "پس", "بعد", "قبل", "روی",
    "زیر", "بین", "بدون", "نیز", "دیگر", "همین", "چند", "بیشتر", "کمتر", "همه",
    "هیچ", "باشد", "شوند", "شود", "کرد", "کردن", "کرده", "می‌شود", "می‌کند",
}

_TONE_RULES: list[tuple[Tone, tuple[str, ...]]] = [
    ("upbeat", ("موفق", "شادی", "عالی", "پیروزی", "خوش", "amazing", "success", "win", "happy", "great")),
    ("dramatic", ("خطر", "مرگ", "جنگ", "فاجعه", "وحشت", "danger", "death", "war", "crisis", "fear")),
    ("urgent", ("فوری", "الان", "سریع", "هشدار", "اهم", "now", "urgent", "alert", "immediately", "must")),
    ("calm", ("آرام", "صلح", "نرم", "مدیتیشن", "آرامش", "calm", "peace", "soft", "gentle", "quiet")),
    ("educational", ("یاد", "آموزش", "چرا", "چگونه", "علم", "learn", "why", "how", "science", "explain", "چیست")),
]


@dataclass
class SentenceInfo:
    index: int
    text: str
    char_count: int
    word_count: int
    estimated_speech_sec: float  # rough TTS duration


@dataclass
class TextAnalysis:
    raw_text: str
    language: Lang
    title: str
    tone: Tone
    sentences: list[SentenceInfo]
    paragraphs: list[str]
    keywords: list[str]
    topics: list[str]
    visual_queries: list[str]
    music_mood: str
    estimated_total_speech_sec: float
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class TextAnalyzer:
    """Heuristic NLP pipeline (FA/EN). No paid API required."""

    def __init__(
        self,
        *,
        chars_per_sec_fa: float = 11.0,
        chars_per_sec_en: float = 14.0,
        min_sentence_chars: int = 6,
    ) -> None:
        self.cps_fa = chars_per_sec_fa
        self.cps_en = chars_per_sec_en
        self.min_sentence_chars = min_sentence_chars

    def analyze(self, text: str, *, title: str | None = None) -> TextAnalysis:
        raw = (text or "").strip()
        if not raw:
            raise ValueError("empty text")

        lang = self.detect_language(raw)
        paragraphs = self._split_paragraphs(raw)
        sentences = self._split_sentences(raw, lang)
        keywords = self.extract_keywords(raw, lang, top_k=12)
        topics = self.infer_topics(keywords, raw)
        tone = self.infer_tone(raw)
        visual = self.suggest_visual_queries(keywords, topics, tone, lang)
        music = self.suggest_music_mood(tone)
        total = sum(s.estimated_speech_sec for s in sentences)

        derived_title = title or self._derive_title(sentences, raw)

        return TextAnalysis(
            raw_text=raw,
            language=lang,
            title=derived_title,
            tone=tone,
            sentences=sentences,
            paragraphs=paragraphs,
            keywords=keywords,
            topics=topics,
            visual_queries=visual,
            music_mood=music,
            estimated_total_speech_sec=round(total, 2),
            meta={
                "sentence_count": len(sentences),
                "paragraph_count": len(paragraphs),
                "char_count": len(raw),
            },
        )

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------
    @staticmethod
    def detect_language(text: str) -> Lang:
        fa = len(re.findall(r"[\u0600-\u06FF]", text))
        en = len(re.findall(r"[A-Za-z]", text))
        if fa == 0 and en == 0:
            return "unknown"
        if fa > 0 and en > 0 and min(fa, en) / max(fa, en) > 0.25:
            return "mixed"
        return "fa" if fa >= en else "en"

    # ------------------------------------------------------------------
    # Segmentation
    # ------------------------------------------------------------------
    def _split_paragraphs(self, text: str) -> list[str]:
        parts = re.split(r"\n\s*\n+", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _split_sentences(self, text: str, lang: Lang) -> list[SentenceInfo]:
        # Persian/Arabic question + EN punctuation
        chunks = re.split(r"(?<=[.!?؟۔])\s+|\n+", text.strip())
        cps = self.cps_fa if lang in ("fa", "mixed") else self.cps_en
        out: list[SentenceInfo] = []
        idx = 0
        for chunk in chunks:
            s = chunk.strip()
            if len(s) < self.min_sentence_chars:
                continue
            words = re.findall(r"[\w\u0600-\u06FF]+", s, flags=re.UNICODE)
            est = max(1.2, min(12.0, len(s) / cps))
            out.append(
                SentenceInfo(
                    index=idx,
                    text=s,
                    char_count=len(s),
                    word_count=len(words),
                    estimated_speech_sec=round(est, 2),
                )
            )
            idx += 1
        if not out:
            # fallback: whole text as one sentence
            est = max(1.5, min(20.0, len(text) / cps))
            out.append(
                SentenceInfo(
                    index=0,
                    text=text.strip(),
                    char_count=len(text),
                    word_count=len(text.split()),
                    estimated_speech_sec=round(est, 2),
                )
            )
        return out

    # ------------------------------------------------------------------
    # Keywords / topics
    # ------------------------------------------------------------------
    def extract_keywords(self, text: str, lang: Lang, top_k: int = 12) -> list[str]:
        tokens = re.findall(r"[A-Za-z\u0600-\u06FF]{3,}", text.lower())
        stop = _STOP_EN | _STOP_FA
        filtered = [t for t in tokens if t not in stop and not t.isdigit()]
        counts = Counter(filtered)
        # prefer slightly longer tokens
        ranked = sorted(counts.items(), key=lambda kv: (kv[1], len(kv[0])), reverse=True)
        return [w for w, _ in ranked[:top_k]]

    def infer_topics(self, keywords: list[str], text: str) -> list[str]:
        blob = (" ".join(keywords) + " " + text).lower()
        catalog: dict[str, tuple[str, ...]] = {
            "space": ("فضا", "کهکشان", "ستاره", "سیاه", "شفق", "nebula", "galaxy", "planet", "orbit", "nasa"),
            "physics": ("فیزیک", "نسبیت", "گرانش", "کوانتوم", "physics", "gravity", "quantum", "energy"),
            "ai": ("هوش", "مدل", "یادگیری", "neural", "ai", "model", "machine", "gpt"),
            "nature": ("طبیعت", "جنگل", "اقیانوس", "کوه", "nature", "forest", "ocean", "mountain"),
            "history": ("تاریخ", "باستان", "تمدن", "history", "ancient", "empire"),
            "math": ("ریاضی", "عدد", "احتمال", "هندسه", "math", "probability", "geometry"),
            "psychology": ("روان", "ذهن", "احساس", "mind", "brain", "emotion", "behavior"),
            "business": ("کسب", "پول", "بازار", "business", "market", "money", "startup"),
        }
        hits: list[tuple[str, int]] = []
        for topic, keys in catalog.items():
            score = sum(1 for k in keys if k in blob)
            if score:
                hits.append((topic, score))
        hits.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in hits[:4]] or ["general"]

    def infer_tone(self, text: str) -> Tone:
        low = text.lower()
        scores: Counter[str] = Counter()
        for tone, keys in _TONE_RULES:
            for k in keys:
                if k in low:
                    scores[tone] += 1
        if not scores:
            return "educational" if ("؟" in text or "?" in text or "چرا" in text or "why" in low) else "neutral"
        return scores.most_common(1)[0][0]  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Creative suggestions
    # ------------------------------------------------------------------
    def suggest_visual_queries(
        self,
        keywords: list[str],
        topics: list[str],
        tone: Tone,
        lang: Lang,
    ) -> list[str]:
        queries: list[str] = []
        # topic-first (better for stock APIs which are EN-heavy)
        topic_map = {
            "space": ["aurora borealis", "milky way stars", "earth from space", "nebula cosmos"],
            "physics": ["particle trails abstract", "black hole visualization", "laboratory science"],
            "ai": ["data center lights", "neural network abstract", "circuit board macro"],
            "nature": ["forest sunlight", "ocean waves aerial", "mountain sunrise"],
            "history": ["ancient ruins", "old library books", "historic architecture"],
            "math": ["geometry patterns", "fractal abstract", "blackboard equations"],
            "psychology": ["human silhouette thinking", "brain scan abstract", "calm lake reflection"],
            "business": ["city skyline night", "startup office", "handshake business"],
            "general": ["cinematic bokeh lights", "abstract gradient motion", "timelapse clouds"],
        }
        for t in topics:
            queries.extend(topic_map.get(t, [])[:2])
        # keyword boost (prefer latin keywords for stock search)
        for kw in keywords:
            if re.search(r"[A-Za-z]", kw):
                queries.append(kw)
        # tone flavor
        tone_extra = {
            "dramatic": "dark cinematic atmosphere",
            "upbeat": "bright colorful motion",
            "calm": "soft natural light",
            "urgent": "fast motion city",
            "educational": "clean modern explanation visual",
            "neutral": "minimal abstract background",
        }
        queries.append(tone_extra.get(tone, "cinematic background"))
        # dedupe preserve order
        seen, out = set(), []
        for q in queries:
            k = q.lower().strip()
            if k and k not in seen:
                seen.add(k)
                out.append(q.strip())
        return out[:8]

    @staticmethod
    def suggest_music_mood(tone: Tone) -> str:
        return {
            "upbeat": "uplifting corporate",
            "dramatic": "dark cinematic tension",
            "urgent": "fast electronic pulse",
            "calm": "ambient soft piano",
            "educational": "curious light documentary",
            "neutral": "minimal ambient",
        }.get(tone, "minimal ambient")

    @staticmethod
    def _derive_title(sentences: list[SentenceInfo], raw: str) -> str:
        if sentences:
            t = sentences[0].text.strip()
            return t[:80]
        return raw.strip().split("\n", 1)[0][:80]


def analyze_text(text: str, **kwargs: Any) -> TextAnalysis:
    """Convenience entrypoint."""
    return TextAnalyzer().analyze(text, **kwargs)
