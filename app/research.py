"""Curated topics from trusted sources only — no invention of verses/hadith."""
from __future__ import annotations

import hashlib
import random
from typing import Any

from app.utils import load_channel_config, utc_now_iso

# هر موضوع: منبع قطعی + محدودیت نقل. مدل اجازه جعل ندارد.
TOPIC_SEEDS = [
    {
        "id": "nahj_letter_31",
        "pillar": "حکمت‌ها و نامه‌های امام علی با منبع معتبر",
        "title_hint": "وصیت امام علی به فرزند؛ از نامه ۳۱ نهج‌البلاغه",
        "focus": "اخلاق، تربیت، زهد — فقط از متن نامه ۳۱",
        "source_hint": "نهج‌البلاغه، نامه ۳۱",
        "source_type": "nahj_letter",
        "source_ref": "نامه ۳۱",
        "quote_policy": "اگر نقل مستقیم می‌کنی فقط با ذکر «نهج‌البلاغه نامه ۳۱»؛ وگرنه پارافریز اخلاقی بدون ادعای متن دقیق",
    },
    {
        "id": "nahj_hikmah_patience",
        "pillar": "حکمت‌ها و نامه‌های امام علی با منبع معتبر",
        "title_hint": "صبر در کلام امام علی؛ از بخش حکم نهج‌البلاغه",
        "focus": "صبر و شکیبایی",
        "source_hint": "نهج‌البلاغه، بخش حکم",
        "source_type": "nahj_hikmah",
        "source_ref": "حکم نهج‌البلاغه",
        "quote_policy": "بدون جعل حکمت؛ ترجیح با دعوت به تأمل و ارجاع به مطالعه اصل متن",
    },
    {
        "id": "quran_rahman_gratitude",
        "pillar": "تأملات قرآنی با ارجاع دقیق",
        "title_hint": "شکر نعمت؛ تأملی کوتاه با ارجاع به سوره الرحمن",
        "focus": "شکرگزاری؛ فقط ذکر نام سوره و در صورت نقل آیه، شماره آیه",
        "source_hint": "قرآن کریم، سوره الرحمن",
        "source_type": "quran",
        "source_ref": "سوره الرحمن",
        "quote_policy": "هر آیه باید با شماره باشد؛ بدون آیه جعلی؛ ترجمه فقط اگر مطمئن نیستی از نقل مستقیم پرهیز کن",
    },
    {
        "id": "nahj_kindness",
        "pillar": "صلح، اخلاق، مهربانی و وحدت ادیان",
        "title_hint": "مهربانی با مردم در آموزه‌های امام علی",
        "focus": "رفتار کریمانه؛ پرهیز از نفرت",
        "source_hint": "نهج‌البلاغه — ارجاع کلی به اخلاق عملی با ذکر منبع",
        "source_type": "nahj_ethics",
        "source_ref": "نهج‌البلاغه",
        "quote_policy": "تمرکز روی اخلاق عمومی با ارجاع به نهج‌البلاغه؛ بدون فرقه‌گرایی",
    },
    {
        "id": "nahj_honesty",
        "pillar": "صلح، اخلاق، مهربانی و وحدت ادیان",
        "title_hint": "راستی و امانت؛ الهام از نهج‌البلاغه",
        "focus": "صداقت در گفتار و عمل",
        "source_hint": "نهج‌البلاغه",
        "source_type": "nahj_ethics",
        "source_ref": "نهج‌البلاغه",
        "quote_policy": "پارافریز اخلاقی + دعوت به مطالعه منبع؛ بدون حدیث جعلی",
    },
    {
        "id": "short_gratitude",
        "pillar": "تأملات قرآنی با ارجاع دقیق",
        "title_hint": "یک دقیقه شکر؛ یادآوری کوتاه",
        "focus": "شکر روزانه",
        "source_hint": "قرآن کریم — آیات شکر با ذکر دقیق در صورت نقل",
        "source_type": "quran",
        "source_ref": "قرآن کریم",
        "quote_policy": "اگر آیه نمی‌دانی شماره دقیق را، فقط دعوت به شکر بدون نقل آیه",
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
            ] or TOPIC_SEEDS
            topic = dict(random.choice(candidates))
        else:
            topic = dict(random.choice(TOPIC_SEEDS))

    topic["kind"] = kind
    topic["picked_at"] = utc_now_iso()
    topic["channel_pillars"] = pillars
    topic["approved_books"] = (cfg.get("content") or {}).get("approved_source_books", [])
    return topic


def build_research_brief(topic: dict[str, Any]) -> str:
    return (
        f"موضوع: {topic['title_hint']}\n"
        f"ستون: {topic['pillar']}\n"
        f"تمرکز: {topic['focus']}\n"
        f"منبع مجاز: {topic['source_hint']} (نوع: {topic.get('source_type')})\n"
        f"ارجاع: {topic.get('source_ref')}\n"
        f"سیاست نقل: {topic.get('quote_policy')}\n"
        f"کتاب‌های تأییدشده کانال: {topic.get('approved_books')}\n"
        f"نوع ویدیو: {topic['kind']}\n"
        "ممنوع: جعل آیه/حدیث، نقل بدون منبع، نفرت‌پراکنی، سیاست، پزشکی.\n"
    )
