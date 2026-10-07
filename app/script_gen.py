"""Generate Persian script + title + description."""
from __future__ import annotations

import json
from typing import Any

from app.utils import clean_persian, env, has_openai, load_content_policy

SYSTEM_PROMPT = """تو نویسنده‌ی اسکریپت برای کانال یوتیوب فارسی معنوی هستی.
قوانین مطلق:
1. هرگز آیه قرآن، حدیث، یا سخن امام علی را جعل نکن.
2. اگر نقل قول می‌آوری، منبع را صریح بنویس.
3. اگر منبع دقیق نداری، از زبان اخلاقی عمومی استفاده کن.
4. لحن: آرام، محترمانه، مردانه.
5. مخاطب همه سنین.
6. بازنمایی چهره مقدس ممنوع.
7. خروجی فقط JSON معتبر.
"""


def _fallback_script(topic: dict[str, Any], kind: str) -> dict[str, Any]:
    if kind == "short":
        body = (
            f"سلام. امروز یک یادآوری کوتاه درباره «{topic['title_hint']}». "
            f"{topic['focus']}. "
            "بر اساس آموزه‌های اخلاقی و منابع معتبر، بیایید امروز کمی بیشتر اهل صبر و مهربانی باشیم. "
            "منبع پیشنهادی: " + topic["source_hint"] + ". خداحافظ."
        )
        duration_hint = 45
    else:
        body = (
            f"بسم الله الرحمن الرحیم. سلام و احترام. "
            f"موضوع امروز: {topic['title_hint']}. "
            f"تمرکز ما روی {topic['focus']} است. "
            f"بر اساس منابع معتبر مانند {topic['source_hint']}، "
            "می‌توانیم از این آموزه‌ها برای زندگی الهام بگیریم: صبر، صداقت، و مهربانی. "
            "لطفاً متن‌های اصلی را از منابع معتبر مطالعه کنید. خداحافظ."
        )
        duration_hint = 420

    return {
        "title": topic["title_hint"][:90],
        "description": (
            f"{topic['title_hint']}\n\n"
            f"منبع: {topic['source_hint']}\n\n"
            "#امام_علی #نهج_البلاغه #تأمل #اخلاق"
        ),
        "script": body,
        "sources": [topic["source_hint"]],
        "tags": ["امام علی", "نهج البلاغه", "اخلاق", "تأمل", "فارسی"],
        "duration_hint_seconds": duration_hint,
        "generated_by": "fallback",
    }


def _call_openai(topic: dict[str, Any], kind: str, research_brief: str) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(
        api_key=env("OPENAI_API_KEY"),
        base_url=env("OPENAI_API_BASE") or "https://api.openai.com/v1",
    )
    policy = load_content_policy()
    length_rule = (
        "اسکریپت حدود ۳۵ تا ۵۰ ثانیه (۸۰ تا ۱۲۰ کلمه)."
        if kind == "short"
        else "اسکریپت حدود ۶ تا ۱۰ دقیقه (۹۰۰ تا ۱۴۰۰ کلمه)."
    )
    user = (
        f"{research_brief}\nمدت هدف: {length_rule}\n"
        f"سیاست: {json.dumps(policy, ensure_ascii=False)}\n"
        "خروجی JSON: title, description, script, sources, tags, duration_hint_seconds"
    )
    resp = client.chat.completions.create(
        model=env("OPENAI_MODEL") or "gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content or "{}")
    data["script"] = clean_persian(str(data.get("script", "")))
    data["title"] = str(data.get("title", topic["title_hint"]))[:100]
    data["description"] = str(data.get("description", ""))
    data["sources"] = data.get("sources") or [topic["source_hint"]]
    data["tags"] = data.get("tags") or ["امام علی", "اخلاق"]
    data["duration_hint_seconds"] = int(
        data.get("duration_hint_seconds") or (45 if kind == "short" else 420)
    )
    data["generated_by"] = "openai"
    return data


def generate_script(topic: dict[str, Any], kind: str, research_brief: str) -> dict[str, Any]:
    if has_openai():
        try:
            return _call_openai(topic, kind, research_brief)
        except Exception as e:
            print(f"[script] OpenAI failed: {e}")
            out = _fallback_script(topic, kind)
            out["error"] = str(e)
            return out
    print("[script] No OPENAI_API_KEY — fallback")
    return _fallback_script(topic, kind)
