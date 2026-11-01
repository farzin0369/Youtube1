"""Eleven BAMO specialist review gates executed before any upload.

These are deterministic role hand-offs, not claims of eleven separately hosted LLMs.
Each role emits an auditable pass/fail result and the pipeline fails closed on any failure.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.youtube_history import find_duplicate, normalize_text

ROLE_NAMES = (
    "discovery", "strategy", "script_hook", "packaging", "seo",
    "production", "editing", "shorts", "chapters", "community", "analytics",
)


def _result(role: str, issues: list[str]) -> dict[str, Any]:
    return {"role": role, "ok": not issues, "issues": issues}


def review_package(
    content: dict[str, Any], *, channel_videos: list[dict[str, Any]],
    captions_path: Path, policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scenes = content.get("scenes") or []
    script = str(content.get("script") or "")
    title = str(content.get("title") or "")
    description = str(content.get("description") or "")
    topic = str(content.get("topic") or "")
    tags = [str(tag).strip() for tag in content.get("tags", []) if str(tag).strip()]
    roles: list[dict[str, Any]] = []

    duplicate = find_duplicate(content, channel_videos)
    roles.append(_result("discovery", ["candidate already exists on the YouTube channel"] if duplicate else []))

    strategy_issues = []
    if not topic or len(script.split()) < 24:
        strategy_issues.append("topic or core idea is too thin")
    roles.append(_result("strategy", strategy_issues))

    hook = str(scenes[0].get("spoken_text") or "") if scenes else ""
    first_sentence = re.split(r"(?<=[.!?؟])\s+", hook.strip())[0] if hook else ""
    hook_issues = []
    if "؟" not in first_sentence or not 4 <= len(first_sentence.split()) <= 16:
        hook_issues.append("opening hook must be a concise, specific question")
    roles.append(_result("script_hook", hook_issues))

    packaging_issues = []
    if not title.startswith("BAMO | ") or len(title) > 100:
        packaging_issues.append("title must be precise, branded and within YouTube's limit")
    description_sentences = [part for part in re.split(r"(?<=[.!?؟])\s+", description) if part.strip()]
    if not 35 <= len(description) <= 900 or len(description_sentences) < 2:
        packaging_issues.append("description must contain two useful, topic-specific sentences")
    if not 2 <= len(str(content.get("thumbnail_text") or "").split()) <= 4:
        packaging_issues.append("thumbnail text must contain 2-4 concise words")
    roles.append(_result("packaging", packaging_issues))

    seo_issues = []
    topical_tags = [tag for tag in tags if tag.casefold() not in {"bamo", "12bamo", "بامو"}]
    if not 5 <= len(topical_tags) <= 8:
        seo_issues.append("five to eight relevant search tags are required")
    topic_words = set(normalize_text(topic).split())
    tag_words = set(normalize_text(" ".join(tags)).split())
    if topic_words and not (topic_words & tag_words):
        seo_issues.append("tags do not contain the actual topic")
    if not {"BAMO", "12bamo", "بامو"}.issubset(set(tags)):
        seo_issues.append("BAMO brand tags are missing")
    roles.append(_result("seo", seo_issues))

    production_issues = []
    if len(scenes) != 4:
        production_issues.append("Shorts must contain exactly four authored scenes")
    queries = [normalize_text(str(scene.get("visual_query") or "")) for scene in scenes]
    if len(set(queries)) != len(queries) or any(len(query.split()) < 2 for query in queries):
        production_issues.append("scene visuals must be specific and distinct")
    roles.append(_result("production", production_issues))

    expected_script = " ".join(str(scene.get("spoken_text") or "").strip() for scene in scenes)
    editing_issues = []
    if normalize_text(script) != normalize_text(expected_script):
        editing_issues.append("narration does not exactly follow authored scene dialogue")
    roles.append(_result("editing", editing_issues))

    shorts_issues = []
    if not 24 <= len(script.split()) <= 52:
        shorts_issues.append("spoken word count is outside Shorts target range")
    roles.append(_result("shorts", shorts_issues))

    chapter_issues = []
    try:
        srt = captions_path.read_text(encoding="utf-8")
        cue_count = len(re.findall(r"(?m)^\d{2}:\d{2}:\d{2},\d{3} -->", srt))
        if cue_count < 4:
            chapter_issues.append("Persian captions contain fewer than four timed cues")
    except OSError:
        chapter_issues.append("caption file is missing")
    roles.append(_result("chapters", chapter_issues))

    forbidden = (policy or {}).get("forbidden") or []
    community_issues = []
    lowered = (title + " " + description + " " + script).casefold()
    for term in forbidden:
        if str(term).casefold() in lowered:
            community_issues.append("content matches a forbidden-policy term")
            break
    roles.append(_result("community", community_issues))

    analytics_issues = []
    normalized_title = normalize_text(title)
    for video in channel_videos:
        previous = normalize_text(str(video.get("title") or ""))
        if normalized_title and previous and SequenceMatcher(None, normalized_title, previous).ratio() >= 0.84:
            analytics_issues.append("recent channel title is too similar")
            break
    roles.append(_result("analytics", analytics_issues))

    report = {"ok": all(item["ok"] for item in roles), "roles": roles}
    failed = [item["role"] for item in roles if not item["ok"]]
    if failed:
        raise ValueError("BAMO 11-role editorial review failed: " + ", ".join(failed))
    return report
