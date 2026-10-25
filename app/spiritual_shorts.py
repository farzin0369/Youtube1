"""Retention-minded, fail-closed Persian YouTube Shorts script generation."""
from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from app.llm_provider import generate_text
from app.emotion_tagger import scene_delivery_hint, segment_and_tag
from app.utils import load_channel_config, load_content_policy

LOGGER = logging.getLogger(__name__)
BRAND_PREFIX = "Imam Ali ✨ "
BRAND_TAGS = ["ImamAli110", "The110Path", "امام علی", "معنویت اسلامی", "رشد فردی", "توکل"]
ALLOWED_MOODS = {"hook", "calm", "reassuring", "motivational"}
MAX_DRAFT_ATTEMPTS = 2

SYSTEM_PROMPT = """تو نویسنده و دبیر یک کانال فارسی‌زبانِ معنوی و رشد فردی هستی. برای YouTube Shorts متنی اصیل، شنیدنی و دقیق بنویس؛ از وعدهٔ قطعی، کلیک‌بیت، ترساندن، شرمنده‌کردن، شعار کلی و تقلید از نویسنده یا کانال دیگر دوری کن. هیچ آیه، حدیث یا نقل‌قولی را جعل یا بدون منبع معتبر به کسی نسبت نده؛ توصیهٔ پزشکی یا مالی شخصی نده.
قلاب باید در اولین جمله باشد: پرسشی مشخص و قابل‌باور یا صحنه‌ای ملموس که مخاطب را به ادامه‌دادن ترغیب کند، نه اغراق یا فریب. سلام و مقدمهٔ کلی ممنوع. یک ایدهٔ اصلی و فقط یک اقدام ساده و عملی بده؛ پایان کوتاه، امیدوارکننده و غیرموعظه‌ای باشد. متن را با صدای بلند تصور کن: جمله‌های کوتاه، فارسی طبیعی، نشانه‌گذاری واقعی برای مکث (ویرگول، نقطه، پرسش‌علامت) و بدون متنِ دستور اجرا.
پاسخ فقط یک شیء JSON معتبر باشد؛ هیچ Markdown یا توضیحی بیرون JSON نده."""

USER_TEMPLATE = """برای کانال ImamAli110 یک Short فارسی بساز. هدف خوانش {target_duration_seconds} ثانیه و حدود {min_words} تا {max_words} واژهٔ گفتاری است؛ کم‌گویی را با تکرار و شعار جبران نکن.
روایت دقیقاً چهار صحنه داشته باشد: ۱) hook کنجکاوی‌برانگیز و مشخص، ۲) همدلی/آرام‌شدن، ۳) یک اقدام کوچک برای همین امروز، ۴) پایان امیدوارکننده و انگیزشی. حالت احساسی هر صحنه به‌ترتیب hook، calm، reassuring، motivational باشد. جمله‌ها با علائم نگارشی طبیعی مکث بسازند.
برای هر صحنه، spoken_text دقیقاً همان بخشی باشد که گوینده می‌خواند؛ visual_query یک راهنمای تصویریِ مشخص به انگلیسی برای صحنهٔ سه‌بعدی سینمایی LTX باشد (مثل "hands planting a seed at sunrise")؛ با معنای همان جمله مرتبط باشد و از متن/لوگو/واترمارک پرهیز کند؛ on_screen_text حداکثر ۵ واژهٔ فارسی باشد.
عنوان روشن، دقیق و بدون کلیک‌بیت باشد؛ توضیح کوتاه و ۳ تا ۶ برچسب مرتبط بده. از این موضوع‌ها/عنوان‌های اخیر دوری کن: {recent}.
بازخورد مبتنی بر آمار واقعی کانال و نتایج جست‌وجوی عمومی YouTube، اگر موجود است: {performance_feedback}. فقط از آن برای کشف زاویهٔ تازه استفاده کن؛ عدد یا علت بازدید را حدس نزن و عنوان/متن رقبا را کپی نکن.
سیاست محتوا: {policy}
خروجی فقط این قالب را داشته باشد:
{{"topic":"...","title":"...","hook":"عین متن گفتاری صحنهٔ اول","description":"...","thumbnail_text":"۲ تا ۴ واژهٔ کوتاه","tags":["..."],"scenes":[{{"spoken_text":"...","mood":"hook","visual_query":"...","on_screen_text":"..."}},{{"spoken_text":"...","mood":"calm","visual_query":"...","on_screen_text":"..."}},{{"spoken_text":"...","mood":"reassuring","visual_query":"...","on_screen_text":"..."}},{{"spoken_text":"...","mood":"motivational","visual_query":"...","on_screen_text":"..."}}],"script":"اتصال عین spoken_text چهار صحنه با یک فاصله"}}
"""


def _word_count(text: str) -> int:
    return sum(bool(re.search(r"[\u0600-\u06FFA-Za-z0-9]", token)) for token in str(text).split())


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\u0600-\u06FF]", "", str(text).casefold())


def _normalize_narration(text: str) -> str:
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
    min_words: int = 24, max_words: int = 48,
) -> dict[str, Any]:
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
        raise ValueError("script_must_match_scene_narration_exactly")
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
    hook = re.sub(r"\s+", " ", str(item.get("hook") or "")).strip()
    if _normalize_narration(hook) != _normalize_narration(scenes[0]["spoken_text"]):
        raise ValueError("hook_must_match_the_first_narration_scene")
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
    if not 1 <= len(topic.split()) <= 6 or len(topic) > 60:
        raise ValueError("topic_missing_or_too_long")
    raw_tags = item.get("tags") if isinstance(item.get("tags"), list) else []
    tags = list(dict.fromkeys([str(tag).strip() for tag in raw_tags if str(tag).strip()] + BRAND_TAGS))[:15]
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
    """Generate one short; fall back to the idea bank when local LLM cannot pass QA."""
    from app.idea_bank import idea_bank_enabled, pick_idea_bank_content

    force_bank = idea_bank_enabled() or (os.getenv("USE_IDEA_BANK") or "").strip().lower() == "only"
    if force_bank:
        result = pick_idea_bank_content(history)
        LOGGER.info("using idea bank (forced) topic=%r words=%s", result.get("idea_bank_topic"), result["word_count"])
        return result

    recent = history.get("recent", []) if isinstance(history, dict) else []
    titles = [str(row.get("title") or "") for row in recent[-30:] if isinstance(row, dict)]
    topics = [str(row.get("topic") or row.get("title") or "") for row in recent[-30:] if isinstance(row, dict)]
    policy = load_content_policy()
    config = load_channel_config().get("content") or {}
    duration_target = str(config.get("target_duration_seconds") or "18-30")
    word_match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", str(config.get("target_word_count") or "24-48"))
    if not word_match:
        raise ValueError("config content.target_word_count must be a range such as '24-48'")
    min_words, max_words = (int(value) for value in word_match.groups())
    if min_words < 20 or max_words > 56 or min_words >= max_words:
        raise ValueError("Shorts target word range must satisfy 20 <= min < max <= 56")
    prompt = USER_TEMPLATE.format(
        recent="؛ ".join(topics)[:1200] or "هنوز موضوع قبلی ثبت نشده است",
        policy=json.dumps(policy, ensure_ascii=False),
        performance_feedback="؛ ".join(str(note) for note in (history.get("performance_notes") or []) if str(note).strip()) or "آمار واقعی در دسترس نیست؛ از نتیجه‌گیری دربارهٔ بازدید خودداری کن",
        target_duration_seconds=duration_target,
        min_words=min_words,
        max_words=max_words,
    )
    result = None
    provider = "unknown"
    draft = ""
    last_error = ""
    for attempt in range(MAX_DRAFT_ATTEMPTS):
        if attempt == 0:
            request_prompt = prompt
            temperature = 0.75
        else:
            repair_note = (
                "\nاصلاح اجباری: نسخهٔ قبلی از کنترل کیفیت نگذشت. این ایرادها را برطرف کن: "
                + last_error
                + "\nپاسخ فقط JSON معتبر باشد.\nپیش‌نویس قبلی:\n"
                + draft[:4000]
            )
            request_prompt = prompt + repair_note
            temperature = 0.4
        try:
            draft, provider = generate_text(
                SYSTEM_PROMPT, request_prompt, max_tokens=900, temperature=temperature, json_mode=True,
            )
        except Exception as exc:
            last_error = f"{type(exc).__name__}:{exc}"
            LOGGER.warning("LLM generate failed attempt %s/%s (%s)", attempt + 1, MAX_DRAFT_ATTEMPTS, type(exc).__name__)
            continue
        try:
            try:
                item = json.loads(draft)
            except json.JSONDecodeError:
                cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", draft.strip(), flags=re.I)
                item = json.loads(cleaned)
            if isinstance(item, dict) and isinstance(item.get("scenes"), list) and len(item["scenes"]) == 4:
                scene_lines = [
                    re.sub(r"\s+", " ", str(scene.get("spoken_text") or "")).strip()
                    for scene in item["scenes"] if isinstance(scene, dict)
                ]
                if len(scene_lines) == 4 and all(scene_lines):
                    item["script"] = " ".join(scene_lines)
            gate_min, gate_max = min_words, max_words
            if attempt == MAX_DRAFT_ATTEMPTS - 1:
                gate_min = max(20, min_words - 4)
                gate_max = min(56, max_words + 4)
            result = validate_short_content(item, titles, min_words=gate_min, max_words=gate_max)
            break
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            LOGGER.warning(
                "short draft failed quality gate on attempt %s/%s (%s)",
                attempt + 1, MAX_DRAFT_ATTEMPTS, last_error[:180],
            )
    if result is not None:
        result["generated_by"] = provider
        LOGGER.info("short content passed QA words=%s title=%r provider=%s", result["word_count"], result["title"], provider)
        return result

    LOGGER.warning("LLM short generation failed; falling back to idea bank (%s)", last_error[:180])
    bank = pick_idea_bank_content(history)
    LOGGER.info("idea bank selected topic=%r words=%s", bank.get("idea_bank_topic"), bank["word_count"])
    return bank
