"""Free, deterministic YouTube growth review integrated before any upload."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


CURIOSITY = ("چرا", "راز", "اگر", "چطور", "چه می‌شود", "قبل از", "اشتباه", "تا حالا")
FLUFF = ("باورنکردنی", "عالی", "فوق‌العاده", "بهترین", "شگفت‌انگیز", "وایرال")


def _first_sentence(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    match = re.search(r"^.*?[.!?؟۔](?:\s|$)", value)
    return match.group(0).strip() if match else value[:160]


def _hook_score(text: str) -> tuple[int, list[str]]:
    value = str(text or "").strip()
    notes: list[str] = []
    score = 0
    if not value:
        return 0, ["قلاب آغازین خالی است."]
    if len(value) <= 100:
        score += 2
    else:
        notes.append("قلاب آغازین طولانی است؛ کوتاه‌ترش کن.")
    if any(token in value for token in CURIOSITY):
        score += 2
    else:
        notes.append("برای ایجاد کنجکاوی، سؤال مشخص یا تضاد ملموس بررسی شود.")
    if "؟" in value or "?" in value:
        score += 1
    else:
        notes.append("قلاب پرسشی نیست؛ بررسی کن که آیا شروع ملموس و جذاب است.")
    if any(token in value for token in FLUFF):
        notes.append("از صفت‌های کلیشه‌ای و وعده‌های اغراق‌آمیز پرهیز شود.")
    return min(score, 5), notes


def review_package(
    content: dict[str, Any],
    render: dict[str, Any],
    media_qa: dict[str, Any],
    history: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Review hook, packaging, SEO, repetition, scene mapping and media QA without a paid API."""
    warnings: list[str] = []
    blockers: list[str] = []
    title = str(content.get("title") or "").strip()
    description = str(content.get("description") or "").strip()
    tags = [str(tag).strip() for tag in (content.get("tags") or []) if str(tag).strip()]
    thumb = str(content.get("thumbnail_text") or "").strip()
    fmt = str(content.get("format") or render.get("video_format") or "long").lower()
    scenes = content.get("scenes") or []
    first_spoken = str((scenes[0] if scenes else {}).get("spoken_text") or content.get("script") or "")
    hook = str(content.get("hook") or _first_sentence(first_spoken)).strip()
    hook_score, hook_notes = _hook_score(hook)

    if not title:
        blockers.append("missing_title")
    if not description:
        blockers.append("missing_description")
    if not tags:
        blockers.append("missing_tags")
    if not thumb:
        blockers.append("missing_thumbnail_text")
    if not media_qa.get("ok"):
        blockers.append("media_qa_failed")
    if render.get("scene_mapping") != "exact-narration-scene-plan":
        blockers.append("scene_narration_mapping_unverified")

    if len(title) > 90:
        warnings.append("عنوان طولانی است و باید برای نمایش موبایل بازبینی شود.")
    thumb_words = thumb.split()
    if not 2 <= len(thumb_words) <= 4:
        warnings.append("متن تصویر بندانگشتی بهتر است ۲ تا ۴ واژه داشته باشد.")
    overlap = set(re.findall(r"\w+", title.casefold())) & set(re.findall(r"\w+", thumb.casefold()))
    if overlap:
        warnings.append("عنوان و تصویر بندانگشتی واژه‌های تکراری دارند: " + "، ".join(sorted(overlap)[:6]))
    if hook_score < 3:
        warnings.append("قلاب آغازین امتیاز کنجکاوی پایینی دارد؛ پیش از انتشار بازبینی شود.")
    warnings.extend(hook_notes)
    if fmt in {"shorts", "short"} and len(scenes) != 4:
        blockers.append("shorts_scene_count_must_be_four")
    if fmt in {"shorts", "short"} and render.get("visual_source") != "ltx-video":
        blockers.append("shorts_not_rendered_by_ltx")
    if render.get("visual_scene_count") != len(render.get("scene_plan_path") and scenes or scenes):
        # Render plans for long videos are sentence-level, while content sections are grouped.
        if fmt not in {"long"}:
            warnings.append("visual_scene_count_differs_from_script_scene_count")

    recent = (history or {}).get("recent") or []
    for row in recent[-30:]:
        old_title = str(row.get("title") or "") if isinstance(row, dict) else str(row)
        if old_title and SequenceMatcher(None, old_title.casefold(), title.casefold()).ratio() >= 0.84:
            warnings.append("عنوان به یکی از ۳۰ ویدئوی اخیر بیش از حد شبیه است.")
            break

    seo_score = 0
    seo_score += 1 if title else 0
    seo_score += 1 if description else 0
    seo_score += 1 if tags else 0
    seo_score += 1 if thumb else 0
    seo_score += 1 if any(tag.lower() in {"imamali110", "the110path"} for tag in tags) else 0
    return {
        "schema_version": 1,
        "ok": not blockers,
        "publish_allowed": not blockers,
        "hook_score": hook_score,
        "seo_pack_score": seo_score,
        "title_length": len(title),
        "thumbnail_word_count": len(thumb_words),
        "tag_count": len(tags),
        "format": fmt,
        "scene_mapping": render.get("scene_mapping"),
        "visual_source": render.get("visual_source"),
        "media_qa_ok": bool(media_qa.get("ok")),
        "blockers": blockers,
        "warnings": list(dict.fromkeys(warnings)),
        "checked_capabilities": [
            "yt-audit", "yt-chapters", "yt-comment", "yt-edit", "yt-package",
            "yt-plan", "yt-retention", "yt-script", "yt-seo", "yt-shorts", "yt-viral",
        ],
        "note": "Heuristic advisory only; scores do not predict views or guarantee virality.",
    }
