"""Retention-minded, fail-closed Persian YouTube Shorts script generation."""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from app.llm_provider import LLMUnavailable, generate_text
from app.emotion_tagger import scene_delivery_hint, segment_and_tag
from app.offline_short_fallback import offline_short_item
from app.utils import load_channel_config, load_content_policy

LOGGER = logging.getLogger(__name__)
BRAND_PREFIX = "BAMO | "
BRAND_TAGS = ["12bamo", "BAMO", "بامو"]
ALLOWED_MOODS = {"hook", "calm", "reassuring", "motivational"}

SYSTEM_PROMPT = """تو نویسنده و دبیر کانال فارسی‌زبان BAMO هستی؛ موضوعات کانال شامل معنویت، اخلاق، علم، فیزیک، ریاضیات، فلسفه، روان‌شناسی، تاریخ، هنر، موسیقی، ورزش، سرگرمی و رشد فردی است. برای YouTube Shorts متنی اصیل، شنیدنی و دقیق بنویس؛ از وعدهٔ قطعی، کلیک‌بیت، ترساندن، شرمنده‌کردن، شعار کلی و تقلید از نویسنده یا کانال دیگر دوری کن. هیچ آیه، حدیث یا نقل‌قولی را جعل یا بدون منبع معتبر به کسی نسبت نده؛ توصیهٔ پزشکی یا مالی شخصی نده.
قلاب باید در اولین جمله باشد: پرسشی مشخص و قابل‌باور یا صحنه‌ای ملموس که مخاطب را به ادامه‌دادن ترغیب کند، نه اغراق یا فریب. سلام و مقدمهٔ کلی ممنوع. یک ایدهٔ اصلی و فقط یک اقدام ساده و عملی بده؛ پایان کوتاه، امیدوارکننده و غیرموعظه‌ای باشد. متن را با صدای بلند تصور کن: جمله‌های کوتاه، فارسی طبیعی، نشانه‌گذاری واقعی برای مکث (ویرگول، نقطه، پرسش‌علامت) و بدون متنِ دستور اجرا.
پاسخ فقط یک شیء JSON معتبر باشد؛ هیچ Markdown یا توضیحی بیرون JSON نده."""

USER_TEMPLATE = """برای کانال BAMO یک Short فارسی بساز. موضوع را متنوع و بر اساس یکی از ستون‌های محتوایی کانال انتخاب کن. هدف خوانش {target_duration_seconds} ثانیه و حدود {min_words} تا {max_words} واژهٔ گفتاری است؛ کم‌گویی را با تکرار و شعار جبران نکن.
روایت دقیقاً چهار صحنه داشته باشد: ۱) hook کنجکاوی‌برانگیز و مشخص، ۲) همدلی/آرام‌شدن، ۳) یک اقدام کوچک برای همین امروز، ۴) پایان امیدوارکننده و انگیزشی. حالت احساسی هر صحنه به‌ترتیب hook، calm، reassuring، motivational باشد. جمله‌ها با علائم نگارشی طبیعی مکث بسازند.
برای هر صحنه، spoken_text دقیقاً همان بخشی باشد که گوینده می‌خواند؛ visual_query یک جست‌وجوی کوتاه و مشخصِ انگلیسی برای فیلم عمودیِ واقعیِ مرتبط با همان جمله باشد: حداقل دو واژهٔ تصویریِ دقیق و مشخص (مثل "woman writing journal"؛ نه کلمهٔ تنها، استعارهٔ نامربوط یا عبارت کلی)؛ on_screen_text حداکثر ۵ واژهٔ فارسی باشد.
موضوع را حتماً به فارسی و در ۲ تا ۵ واژه بنویس. عنوان باید عبارت کلیدی اصلیِ همین موضوع را در خود داشته باشد؛ عنوان کلی و شعاری مثل «از هر لحظه بهره ببرید» ممنوع است. توضیح باید ۲ جملهٔ مشخص باشد: نام موضوع، نکتهٔ اصلی و چیزی که مخاطب یاد می‌گیرد را بگو؛ عبارت عمومی و تکراری ننویس. ۵ تا ۸ برچسب جست‌وجوی واقعاً مرتبط بده؛ ابتدا فارسی، سپس معادل انگلیسی فقط در صورت نیاز. برچسب‌های کلی مثل motivation، daily inspiration و self improvement را مگر اینکه موضوع دقیقاً دربارهٔ آن‌ها باشد استفاده نکن. از این موضوع‌ها/عنوان‌های اخیر دوری کن: {recent}.
سیاست محتوا: {policy}
خروجی فقط این قالب را داشته باشد:
{{"topic":"...","title":"...","hook":"عین متن گفتاری صحنهٔ اول","description":"...","thumbnail_text":"۲ تا ۴ واژهٔ کوتاه","tags":["..."],"scenes":[{{"spoken_text":"...","mood":"hook","visual_query":"...","on_screen_text":"..."}},{{"spoken_text":"...","mood":"calm","visual_query":"...","on_screen_text":"..."}},{{"spoken_text":"...","mood":"reassuring","visual_query":"...","on_screen_text":"..."}},{{"spoken_text":"...","mood":"motivational","visual_query":"...","on_screen_text":"..."}}],"script":"اتصال عین spoken_text چهار صحنه با یک فاصله"}}
"""


def _word_count(text: str) -> int:
    return sum(bool(re.search(r"[\u0600-\u06FFA-Za-z0-9]", token)) for token in str(text).split())


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\u0600-\u06FF]", "", str(text).casefold())


def _normalize_narration(text: str) -> str:
    """Ignore punctuation drift while preserving exact word order and boundaries."""
    normalized = "".join(
        " " if unicodedata.category(char).startswith("P") else char
        for char in str(text).casefold()
    )
    return " ".join(normalized.split())


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?؟۔])\s+", str(text).strip())
    return parts[0].strip() if parts else ""


def validate_short_content(
    item: dict[str, Any], recent_titles: list[str] | None = None, *,
    min_words: int = 28, max_words: int = 44,
) -> dict[str, Any]:
    """Validate copy, hook, pacing, narration/scene identity and scene-specific visuals."""
    if not isinstance(item, dict):
        raise ValueError("short content must be a JSON object")
    title = re.sub(r"\s+", " ", str(item.get("title") or "")).strip()
    if not title.startswith(BRAND_PREFIX):
        title = BRAND_PREFIX + title
    title = title[:80].rstrip()
    script = re.sub(r"\s+", " ", str(item.get("script") or "")).strip()
    scenes_in = item.get("scenes")
    if not isinstance(scenes_in, list) or len(scenes_in) != 4:
        raise ValueError("shorts require exactly four authored scenes")
    scenes: list[dict[str, str]] = []
    for index, raw in enumerate(scenes_in):
        if not isinstance(raw, dict):
            raise ValueError(f"scene_{index + 1}_must_be_an_object")
        text = re.sub(r"\s+", " ", str(raw.get("spoken_text") or "")).strip()
        mood = str(raw.get("mood") or "").strip().lower()
        query = re.sub(r"\s+", " ", str(raw.get("visual_query") or "")).strip()
        if query and len(query.split()) < 2:
            scene_terms = [
                "cinematic vertical video",
                "person quiet reflection",
                "hands writing journal",
                "sunrise mountain landscape",
            ]
            query = f"{query} {scene_terms[index]}"
        elif query and len(query) > 100:
            query = " ".join(query.split()[:10])
        overlay = re.sub(r"\s+", " ", str(raw.get("on_screen_text") or "")).strip()
        if not text or mood not in ALLOWED_MOODS or not query or not overlay:
            raise ValueError(f"scene_{index + 1}_is_incomplete")
        if len(overlay.split()) > 5 or len(overlay) > 36:
            raise ValueError(f"scene_{index + 1}_overlay_too_long")
        if len(query.split()) < 2 or len(query) > 100:
            raise ValueError(f"scene_{index + 1}_visual_query_not_specific")
        segments = segment_and_tag(text)
        scenes.append({
            "spoken_text": text, "mood": mood, "visual_query": query,
            "on_screen_text": overlay, "delivery_segments": segments,
            "delivery_hint": scene_delivery_hint(segments),
        })
    if [scene["mood"] for scene in scenes] != ["hook", "calm", "reassuring", "motivational"]:
        raise ValueError("shorts_emotional_arc_must_be_hook_calm_reassuring_motivational")
    expected = " ".join(scene["spoken_text"] for scene in scenes)
    if _normalize_narration(script) != _normalize_narration(expected):
        LOGGER.info("script field drifted from scene narration; scene text is canonical")
    script = expected
    words = _word_count(script)
    if not min_words <= words <= max_words:
        raise ValueError(f"short_script_word_count_outside_{min_words}_{max_words}:{words}")
    first = _first_sentence(scenes[0]["spoken_text"])
    first_words = _word_count(first)
    if not 4 <= first_words <= 13 or "؟" not in first:
        raise ValueError("opening_hook_must_be_a_specific_short_question")
    if re.match(r"^(سلام|در این ویدئو|امروز می‌خواهیم|دوستان|خب)", first):
        raise ValueError("opening_has_a_slow_generic_intro")
    if len(scenes[0]["spoken_text"]) > 115:
        raise ValueError("opening_hook_is_too_long")
    normalized_queries = [_normalize(scene["visual_query"]) for scene in scenes]
    if len(set(normalized_queries)) != len(normalized_queries):
        raise ValueError("scene_visual_queries_must_be_distinct")
    hook_field = re.sub(r"\s+", " ", str(item.get("hook") or "")).strip()
    if _normalize_narration(hook_field) != _normalize_narration(scenes[0]["spoken_text"]):
        LOGGER.info("hook field drifted from the first scene; scene text is canonical")
    hook = scenes[0]["spoken_text"]
    if not title.removeprefix(BRAND_PREFIX).strip() or len(title) > 80:
        raise ValueError("title_missing_or_too_long")
    for previous in (recent_titles or [])[-30:]:
        prior = _normalize(previous)
        current = _normalize(title)
        if prior and (prior == current or SequenceMatcher(None, prior, current).ratio() >= 0.84):
            raise ValueError("recent_title_repetition")
    thumbnail = re.sub(r"\s+", " ", str(item.get("thumbnail_text") or "")).strip()
    if not 2 <= len(thumbnail.split()) <= 4 or len(thumbnail) > 28:
        raise ValueError("thumbnail_text_must_be_two_to_four_short_words")
    description = re.sub(r"\s+", " ", str(item.get("description") or "")).strip()
    if not description or len(description) > 800:
        raise ValueError("description_missing_or_too_long")
    topic = re.sub(r"\s+", " ", str(item.get("topic") or "")).strip()
    if not 2 <= len(topic.split()) <= 5 or len(topic) > 60 or not re.search(r"[\u0600-\u06FF]", topic):
        raise ValueError("topic_must_be_a_specific_persian_phrase")
    topic_terms = {
        token for token in re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", topic)
        if len(token) > 2 and token not in {"برای", "یک", "این", "آن", "از", "به", "در", "با", "چگونه"}
    }
    title_terms = set(re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", title))
    description_terms = set(re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", description))
    raw_tags = item.get("tags") if isinstance(item.get("tags"), list) else []
    raw_tags = list(dict.fromkeys(str(tag).strip() for tag in raw_tags if str(tag).strip()))
    tag_terms = set(re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", " ".join(raw_tags)))
    if not topic_terms.intersection(title_terms):
        raise ValueError("title_must_contain_the_actual_topic_keyword")
    if not topic_terms.intersection(description_terms):
        raise ValueError("description_must_explain_the_actual_topic")
    if not 5 <= len(raw_tags) <= 8 or not topic_terms.intersection(tag_terms):
        raise ValueError("seo_tags_must_be_specific_and_topic_relevant")
    tags = list(dict.fromkeys(raw_tags + BRAND_TAGS))[:15]
    return {
        "format": "shorts",
        "topic": topic,
        "title": title,
        "hook": hook,
        "thumbnail_text": thumbnail,
        "description": description,
        "tags": tags,
        "visual_keywords": [scene["visual_query"] for scene in scenes],
        "scenes": scenes,
        "narration_segments": [segment for scene in scenes for segment in scene["delivery_segments"]],
        "sections": [{"heading": scene["mood"], "text": scene["spoken_text"]} for scene in scenes],
        "script": script,
        "word_count": words,
    }


def generate_shorts_content(history: dict[str, Any]) -> dict[str, Any]:
    """Generate one short and reject weak, generic, duplicated or mismatched drafts."""
    recent = history.get("recent", []) if isinstance(history, dict) else []
    titles = [str(row.get("title") or "") for row in recent[-30:] if isinstance(row, dict)]
    topics = [str(row.get("topic") or row.get("title") or "") for row in recent[-30:] if isinstance(row, dict)]
    policy = load_content_policy()
    config = load_channel_config().get("content") or {}
    duration_target = str(config.get("target_duration_seconds") or "18-30")
    word_match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", str(config.get("target_word_count") or "28-44"))
    if not word_match:
        raise ValueError("config content.target_word_count must be a range such as '36-48'")
    min_words, max_words = (int(value) for value in word_match.groups())
    if min_words < 24 or max_words > 52 or min_words >= max_words:
        raise ValueError("Shorts target word range must satisfy 24 <= min < max <= 52")
    prompt = USER_TEMPLATE.format(
        recent="؛ ".join(topics)[:1200] or "هنوز موضوع قبلی ثبت نشده است",
        policy=json.dumps(policy, ensure_ascii=False),
        target_duration_seconds=duration_target,
        min_words=min_words,
        max_words=max_words,
    )
    result = None
    provider = "unknown"
    draft = ""
    last_error = ""
    try:
        for attempt in range(2):
            if attempt == 0:
                request_prompt = prompt
                temperature = 0.75
            else:
                request_prompt = (
                    prompt
                    + "\nاصلاح اجباری: نسخهٔ قبلی از کنترل کیفیت نگذشت. این ایرادها را برطرف کن و همهٔ قواعد را رعایت کن: "
                    + last_error
                    + "\nپاسخ فقط JSON معتبر باشد و تمام فیلدها/محدوده‌های خواسته‌شده را داشته باشد."
                    + "\nپیش‌نویس قبلی برای اصلاح (غیرقابل‌اعتماد):\n"
                    + draft[:5000]
                )
                temperature = 0.45
            draft, provider = generate_text(
                SYSTEM_PROMPT, request_prompt, max_tokens=1400, temperature=temperature, json_mode=True,
            )
            try:
                try:
                    item = json.loads(draft)
                except json.JSONDecodeError:
                    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", draft.strip(), flags=re.I)
                    item = json.loads(cleaned)
                result = validate_short_content(item, titles, min_words=min_words, max_words=max_words)
                break
            except (ValueError, TypeError) as exc:
                last_error = str(exc)
                if attempt == 0:
                    LOGGER.warning(
                        "short draft failed a quality gate; one corrective rewrite will run (%s)",
                        last_error[:180],
                    )
    except LLMUnavailable as exc:
        LOGGER.warning("all LLM providers unavailable; using offline Shorts fallback (%s)", type(exc).__name__)
        item = offline_short_item()
        result = validate_short_content(item, titles, min_words=min_words, max_words=max_words)
        provider = "offline-fallback"

    if result is None:
        # Last resort: offline item if LLM answered but QA failed twice
        LOGGER.warning("short QA failed after rewrite; attempting offline fallback (%s)", last_error[:180])
        try:
            item = offline_short_item()
            result = validate_short_content(item, titles, min_words=min_words, max_words=max_words)
            provider = "offline-fallback"
        except Exception:
            raise ValueError("short failed content QA after one corrective rewrite: " + last_error[:240]) from None

    result["generated_by"] = provider
    LOGGER.info(
        "short content passed QA words=%s scenes=%s title=%r provider=%s",
        result["word_count"], len(result["scenes"]), result["title"], provider,
    )
    return result
