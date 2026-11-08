"""Scene generation for Text-to-Video engine.

Turns TextAnalysis into a timed ScenePlan:
  - one or more sentences per scene
  - visual query assignment
  - caption text
  - motion / transition hints
  - speech timing estimates
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .text_analyzer import TextAnalysis, TextAnalyzer

Motion = Literal["kenburns_in", "kenburns_out", "pan_left", "pan_right", "static", "zoom_pulse"]
Transition = Literal["fade", "cut", "slide_left", "slide_right", "none"]
Aspect = Literal["portrait", "landscape", "square"]


@dataclass
class Scene:
    id: str
    index: int
    narration: str
    caption: str
    start_sec: float
    end_sec: float
    duration_sec: float
    visual_query: str
    motion: Motion
    transition_in: Transition
    tone_hint: str
    keywords: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.duration_sec


@dataclass
class ScenePlan:
    title: str
    language: str
    tone: str
    aspect: Aspect
    target_fps: int
    scenes: list[Scene]
    music_mood: str
    visual_queries: list[str]
    total_duration_sec: float
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SceneGenerator:
    """Build timed scenes from text analysis."""

    def __init__(
        self,
        *,
        max_scene_sec: float = 6.5,
        min_scene_sec: float = 1.6,
        pad_end_sec: float = 0.4,
        sentences_per_scene: int = 1,
        aspect: Aspect = "portrait",
        fps: int = 30,
    ) -> None:
        self.max_scene_sec = max_scene_sec
        self.min_scene_sec = min_scene_sec
        self.pad_end_sec = pad_end_sec
        self.sentences_per_scene = max(1, sentences_per_scene)
        self.aspect = aspect
        self.fps = fps
        self._motions: list[Motion] = [
            "kenburns_in",
            "kenburns_out",
            "pan_left",
            "pan_right",
            "zoom_pulse",
        ]
        self._transitions: list[Transition] = ["fade", "fade", "cut", "slide_left"]

    def from_analysis(self, analysis: TextAnalysis) -> ScenePlan:
        groups = self._group_sentences(analysis)
        scenes: list[Scene] = []
        t = 0.0
        queries = analysis.visual_queries or ["cinematic abstract background"]

        for i, group in enumerate(groups):
            narration = " ".join(s.text for s in group).strip()
            caption = self._caption_for(group, analysis.language)
            # duration: sum of sentence estimates, clamped
            raw_dur = sum(s.estimated_speech_sec for s in group)
            dur = max(self.min_scene_sec, min(self.max_scene_sec, raw_dur))
            vq = queries[i % len(queries)]
            motion = self._motions[i % len(self._motions)]
            tr = "none" if i == 0 else self._transitions[i % len(self._transitions)]

            scene = Scene(
                id=f"scene_{i:03d}",
                index=i,
                narration=narration,
                caption=caption,
                start_sec=round(t, 3),
                end_sec=round(t + dur, 3),
                duration_sec=round(dur, 3),
                visual_query=vq,
                motion=motion,
                transition_in=tr,  # type: ignore[arg-type]
                tone_hint=analysis.tone,
                keywords=analysis.keywords[:6],
                meta={
                    "sentence_indexes": [s.index for s in group],
                    "sentence_count": len(group),
                },
            )
            scenes.append(scene)
            t += dur

        total = t + self.pad_end_sec
        return ScenePlan(
            title=analysis.title,
            language=analysis.language,
            tone=analysis.tone,
            aspect=self.aspect,
            target_fps=self.fps,
            scenes=scenes,
            music_mood=analysis.music_mood,
            visual_queries=list(queries),
            total_duration_sec=round(total, 3),
            meta={
                "scene_count": len(scenes),
                "topics": analysis.topics,
                "source_char_count": analysis.meta.get("char_count"),
            },
        )

    def from_text(
        self,
        text: str,
        *,
        title: str | None = None,
        analyzer: TextAnalyzer | None = None,
    ) -> ScenePlan:
        analyzer = analyzer or TextAnalyzer()
        analysis = analyzer.analyze(text, title=title)
        return self.from_analysis(analysis)

    # ------------------------------------------------------------------
    def _group_sentences(self, analysis: TextAnalysis) -> list[list]:
        sents = analysis.sentences
        if not sents:
            return []
        n = self.sentences_per_scene
        groups: list[list] = []
        buf: list = []
        acc = 0.0
        for s in sents:
            # start new group if buffer full by count or duration
            if buf and (len(buf) >= n or acc + s.estimated_speech_sec > self.max_scene_sec):
                groups.append(buf)
                buf = []
                acc = 0.0
            buf.append(s)
            acc += s.estimated_speech_sec
        if buf:
            groups.append(buf)
        return groups

    @staticmethod
    def _caption_for(group: list, language: str) -> str:
        # Prefer first sentence as on-screen caption (readable length)
        text = group[0].text.strip()
        if len(group) > 1 and language == "en":
            # allow short merge
            merged = " ".join(s.text.strip() for s in group)
            if len(merged) <= 90:
                return merged
        # hard trim for vertical safe area
        if len(text) > 110:
            return text[:107].rstrip() + "…"
        return text


def plan_scenes(text: str, **kwargs: Any) -> ScenePlan:
    """Convenience: text → ScenePlan."""
    return SceneGenerator(**{k: v for k, v in kwargs.items() if k in {
        "max_scene_sec", "min_scene_sec", "pad_end_sec", "sentences_per_scene", "aspect", "fps"
    }}).from_text(text, title=kwargs.get("title"))
