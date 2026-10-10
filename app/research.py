"""Collect, deduplicate, and rank current Iran-related news headlines from RSS feeds."""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.utils import env, load_channel_config, utc_now_iso

# Google News RSS searches aggregate reporting from multiple publishers. Keep only
# stories whose headline/summary explicitly connects them to Iran or Iran-related affairs.
NEWS_FEEDS: tuple[tuple[str, str], ...] = (
    ("iran_world", "https://news.google.com/rss/search?q=Iran+OR+Iranian+OR+Tehran+OR+IRGC+OR+%22Islamic+Republic%22+OR+%22Persian+Gulf%22+OR+Hormuz&hl=en-US&gl=US&ceid=US:en"),
    ("iran_fa", "https://news.google.com/rss/search?q=%D8%A7%DB%8C%D8%B1%D8%A7%D9%86+OR+%D8%A7%DB%8C%D8%B1%D8%A7%D9%86%DB%8C+OR+%D8%AA%D9%87%D8%B1%D8%A7%D9%86+OR+%D8%B3%D9%BE%D8%A7%D9%87+OR+%D8%AA%D9%86%DA%AF%D9%87+%D9%87%D8%B1%D9%85%D8%B2+OR+%D8%AE%D9%84%DB%8C%D8%AC+%D9%81%D8%A7%D8%B1%D8%B3&hl=fa&gl=IR&ceid=IR:fa"),
)
CATEGORY_FA = {
    "iran_world": "ایران و جهان",
    "iran_fa": "ایران",
}
IRAN_RELEVANCE = re.compile(
    r"\b(?:iran(?:ian)?|tehran|irgc|qods force|islamic republic|persian gulf|"
    r"strait of hormuz|hormuz|iranian nuclear|iran deal|iran sanctions)\b|"
    r"ایران|ایرانی|تهران|سپاه|قدس|جمهوری اسلامی|خلیج فارس|تنگه هرمز|برجام|هسته.?ای",
    re.IGNORECASE,
)


def is_iran_related(story: dict[str, Any]) -> bool:
    """Conservative relevance gate: title or description must name Iran-related terms."""
    text = f"{story.get('title', '')} {story.get('description', '')}"
    return bool(IRAN_RELEVANCE.search(text))


def _text(parent: ET.Element, path: str) -> str:
    node = parent.find(path)
    return " ".join("".join(node.itertext()).split()) if node is not None else ""


def _published(raw: str) -> str:
    if not raw:
        return ""
    try:
        parsed = parsedate_to_datetime(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return raw[:80]


def parse_rss(xml_bytes: bytes, category: str, feed_url: str) -> list[dict[str, Any]]:
    """Parse RSS safely; malformed entries are skipped rather than invented."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    stories: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        title = _text(item, "title")
        link = _text(item, "link")
        if not title or not link:
            continue
        parsed = urlparse(link)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        source = _text(item, "source")
        description = html.unescape(re.sub(r"<[^>]+>", " ", _text(item, "description")))
        description = " ".join(description.split())[:1200]
        stories.append({
            "id": hashlib.sha256((title.lower() + "|" + link).encode()).hexdigest()[:16],
            "title": title,
            "description": description,
            "url": link,
            "publisher": source or parsed.netloc,
            "category": category,
            "category_fa": CATEGORY_FA.get(category, category),
            "published_at": _published(_text(item, "pubDate")),
            "feed_url": feed_url,
        })
    return stories


def fetch_news(timeout: int = 12, per_feed: int = 12) -> list[dict[str, Any]]:
    """Fetch public RSS feeds; errors are recorded and do not fabricate stories."""
    collected: list[dict[str, Any]] = []
    errors: list[str] = []
    for category, feed_url in NEWS_FEEDS:
        request = urllib.request.Request(
            feed_url,
            headers={"User-Agent": "TTKhabarNewsBot/1.0 (RSS news research; contact: repository owner)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read(2_000_000)
            collected.extend(parse_rss(payload, category, feed_url)[:per_feed])
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            errors.append(f"{category}: {type(exc).__name__}")
        time.sleep(0.05)
    unique: dict[str, dict[str, Any]] = {}
    for story in collected:
        normalized = re.sub(r"[^a-z0-9]+", " ", story["title"].lower()).strip()
        key = normalized or story["id"]
        if key not in unique:
            unique[key] = story
    stories = [story for story in unique.values() if is_iran_related(story)]
    # Prefer recent stories, but keep unknown timestamps eligible and preserve category diversity.
    now = datetime.now(timezone.utc)
    def freshness(story: dict[str, Any]) -> float:
        raw = story.get("published_at", "")
        try:
            published = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            age_hours = max(0.0, (now - published).total_seconds() / 3600)
            return max(0.0, 72.0 - age_hours) / 72.0
        except (ValueError, TypeError):
            return 0.2
    stories.sort(key=lambda story: freshness(story), reverse=True)
    # Keep up to two stories per category before filling remaining slots.
    selected: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    for story in stories:
        category = str(story.get("category") or "world")
        if category_counts.get(category, 0) >= 2:
            continue
        selected.append(story)
        category_counts[category] = category_counts.get(category, 0) + 1
        if len(selected) >= 24:
            break
    if not selected and errors:
        raise RuntimeError("Could not retrieve any current news RSS feeds: " + ", ".join(errors))
    return selected


def rank_stories(stories: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    """Choose a compact, category-diverse set with valid source links."""
    result: list[dict[str, Any]] = []
    seen_categories: set[str] = set()
    for story in stories:
        if not story.get("title") or not story.get("url"):
            continue
        category = str(story.get("category") or "world")
        if category not in seen_categories:
            result.append(story)
            seen_categories.add(category)
        if len(result) >= max(1, min(int(limit), 5)):
            break
    if len(result) < min(3, limit):
        for story in stories:
            if story not in result and story.get("title") and story.get("url"):
                result.append(story)
            if len(result) >= max(1, min(int(limit), 5)):
                break
    return result


def pick_topic(kind: str, seed: str | None = None) -> dict[str, Any]:
    """Build a current news assignment. If feeds fail, stop instead of inventing news."""
    cfg = load_channel_config()
    channel = cfg.get("channel", {})
    limit = 5 if kind == "long" else 1
    prefetched_path = (env("TT_KHABAR_NEWS_FILE") or "").strip()
    if prefetched_path:
        try:
            payload = json.loads(Path(prefetched_path).read_text(encoding="utf-8"))
            prefetched = payload.get("stories") if isinstance(payload, dict) else None
            if not isinstance(prefetched, list):
                raise ValueError("news JSON must contain a stories array")
            stories = rank_stories([story for story in prefetched if isinstance(story, dict) and is_iran_related(story)], limit=limit)
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Prefetched news input is invalid; refusing to fetch untracked replacement stories: {type(exc).__name__}") from exc
    else:
        stories = rank_stories(fetch_news(), limit=limit)
    if not stories:
        raise RuntimeError("No source-linked news stories available; refusing to invent a bulletin.")
    if kind == "long" and len(stories) < 3:
        raise RuntimeError("Fewer than three source-linked news stories are available; refusing to publish a bulletin.")
    digest = hashlib.sha256("|".join(item["id"] for item in stories).encode()).hexdigest()[:12]
    return {
        "id": "news_" + digest,
        "pillar": ", ".join(item["category_fa"] for item in stories),
        "title_hint": stories[0]["title"],
        "focus": "جمع‌بندی فارسی ۳ تا ۵ خبر روز درباره ایران و رویدادهای جهانی مرتبط با ایران؛ با تفکیک واقعیت، ادعا و تحلیل",
        "source_hint": "منابع خبری پیوندخورده در فهرست خبرها",
        "source_type": "current_news_rss",
        "source_ref": ", ".join(item["publisher"] for item in stories),
        "quote_policy": "فقط اطلاعات موجود در تیتر/خلاصه و منابع پیوندخورده؛ ادعاها را به منبع نسبت بده؛ جزئیات تأییدنشده را قطعی بیان نکن",
        "stories": stories,
        "kind": kind,
        "picked_at": utc_now_iso(),
        "channel_pillars": channel.get("objective", "اخبار جهانی فارسی"),
        "approved_books": [],
    }


def build_research_brief(topic: dict[str, Any]) -> str:
    stories = topic.get("stories") or []
    if not stories:
        raise RuntimeError("Research brief has no source-linked stories; refusing unsupported content.")
    lines = [
        "ماموریت: یک بولتن خبری فارسی دقیق، متوازن و قابل‌فهم فقط درباره ایران و رویدادهای جهانی مرتبط با ایران بساز.",
        "محدودیت حیاتی: فقط از تیتر، خلاصه و لینک‌های زیر استفاده کن. هیچ عدد، نقل‌قول، علت، نتیجه یا جزئیاتی را که در داده نیست اختراع نکن.",
        "خبر، ادعا و تحلیل را از هم جدا کن. در صورت کمبود اطلاعات بگو جزئیات مستقل هنوز روشن نیست.",
        "۳ تا ۵ خبر با تنوع موضوعی انتخاب شده‌اند؛ برای هر مورد نام ناشر، تاریخ انتشار و URL را در توضیحات بیاور.",
        "برای هر خبر: چه رخ داده، چرا مهم است، چه چیزی هنوز نامعلوم است. از تکرار تیتر به‌عنوان تحلیل پرهیز کن.",
        "خبرهای حساس درباره سلامت، درگیری و انتخابات را با نسبت دادن روشن به منبع بیان کن؛ از تصاویر ساختگی به‌عنوان تصاویر واقعی استفاده نکن.",
        f"نوع ویدئو: {topic.get('kind')}; زمان گردآوری: {topic.get('picked_at')}",
        "منابع و داده‌های گردآوری‌شده:",
    ]
    for i, story in enumerate(stories, 1):
        lines.extend([
            f"{i}. دسته: {story.get('category_fa')} ({story.get('category')})",
            f"تیتر اصلی: {story.get('title')}",
            f"ناشر: {story.get('publisher')}",
            f"زمان انتشار: {story.get('published_at') or 'در RSS اعلام نشده'}",
            f"خلاصه منبع: {story.get('description') or 'خلاصه‌ای در RSS موجود نیست؛ فقط تیتر در دسترس است.'}",
            f"لینک منبع: {story.get('url')}",
        ])
    return "\n".join(lines) + "\n"
