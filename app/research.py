"""Topic selection for the channel."""
from __future__ import annotations

import hashlib
import random
from typing import Any

from app.utils import load_channel_config, utc_now_iso

TOPIC_SEEDS = [
    {
        "id": "nahj_letter_31",
        "pillar": "حکمت‌ها و نامه‌های امام علی با منبع معتبر",
        "title_hint": "نامه ۳۱ نهج‌البلاغه؛ وصیت به امام حسن",
        "focus": "اخلاق، تربیت فرزند، زهد و پرهیز از دنیاگرایی",
        "source_hint": "نهج‌البلاغه، نامه ۳۱ (ترجمه‌های معتبر مانند فیض‌الاسلام یا دشتی)",
    },
    {
        "id": "nahj_hikmah_1",
        "pillar": "حکمت‌ها و نامه‌های امام علی با منبع معتبر",
        "title_hint": "حکمت‌هایی از نهج‌البلاغه درباره صبر",
        "focus": "صبر در سختی و شکر در نعمت",
        "source_hint": "نهج‌البلاغه، بخش حکم",
    },
    {
        "id": "quran_reflection_rahman",
        "pillar": "تأملات قرآنی با ارجاع دقیق",
        "title_hint": "تأملی کوتاه در سوره الرحمن",
        "focus": "نعمت‌های الهی و شکرگزاری بدون ادعای تفسیر شخصی بدون منبع",
        "source_hint": "قرآن کریم، سوره الرحمن — فقط ذکر آیه با شماره و ترجمه معتبر",
    },
    {
        "id": "peace_unity",
        "pillar": "صلح، اخلاق، مهربانی و وحدت ادیان",
        "title_hint": "مهربانی و احترام به انسان‌ها در سخن امام علی",
        "focus": "رفتار کریمانه با مردم، پرهیز از نفرت‌پراکنی",
        "source_hint": "نهج‌البلاغه و روایات معتبر با ذکر منبع",
    },
    {
        "id": "ethics_honesty",
        "pillar": "صلح، اخلاق، مهربانی و وحدت ادیان",
        "title_hint": "راستی و امانت‌داری",
        "focus": "صداقت در گفتار و عمل",
        "source_hint": "نهج‌البلاغه / احادیث معتبر با ارجاع",
    },
    {
        "id": "short_gratitude",
        "pillar": "تأملات قرآنی با ارجاع دقیق",
        "title_hint": "شکر نعمت؛ یادآوری کوتاه",
        "focus": "شکرگزاری روزانه بدون ادعاهای پزشکی یا سیاسی",
        "source_hint": "آیات مرتبط با شکر با ذکر دقیق سوره و آیه",
    },
]


def pick_topic(kind: str, seed: str | None = None) -> dict[str, Any]:
    cfg = load_channel_config()
    pillars = cfg.get("content", {}).get("pillars", [])

    if seed:
        idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(TOPIC_SEEDS)
        topic = dict(TOPIC_SEEDS[idx])
    else:
        if kind == "short":
            candidates = [
                t for t in TOPIC_SEEDS
                if t["id"].startswith("short") or "حکمت" in t["title_hint"] or "شکر" in t["title_hint"]
            ]
            if not candidates:
                candidates = TOPIC_SEEDS
            topic = dict(random.choice(candidates))
        else:
            topic = dict(random.choice(TOPIC_SEEDS))

    topic["kind"] = kind
    topic["picked_at"] = utc_now_iso()
    topic["channel_pillars"] = pillars
    return topic


def build_research_brief(topic: dict[str, Any]) -> str:
    return (
        f"موضوع: {topic['title_hint']}\n"
        f"ستون محتوا: {topic['pillar']}\n"
        f"تمرکز: {topic['focus']}\n"
        f"راهنمای منبع: {topic['source_hint']}\n"
        f"نوع ویدیو: {topic['kind']}\n"
        "قوانین سخت:\n"
        "- هر نقل‌قول باید منبع داشته باشد.\n"
        "- هرگز آیه، حدیث یا سخن جعلی نساز.\n"
        "- بین نقل قول، ترجمه، تفسیر و روایت خلاقانه تمایز بگذار.\n"
        "- چهره مقدس را بازنمایی نکن.\n"
        "- نفرت‌پراکنی مذهبی ممنوع.\n"
    )
