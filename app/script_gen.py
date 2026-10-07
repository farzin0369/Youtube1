"""Persian script from approved sources only."""
from __future__ import annotations

import json
from typing import Any

from app.utils import clean_persian, env, has_openai, load_content_policy

SYSTEM_PROMPT = """تو نویسنده‌ی اسکریپت برای کانال یوتیوب معنوی فارسی هستی.
قوانین مطلق:
1. هرگز آیه، حدیث یا سخن امام علی را جعل نکن.
2. فقط از منبعی که در brief آمده استفاده کن.
3. اگر متن دقیق حفظ نیستی، پارافریز اخلاقی کن و بگو بر اساس نهج‌البلاغه / قرآن — بدون ادعای نقل لفظی.
4. لحن: آرام، مردانه، یک گوینده ثابت، سینمایی و دلنشین.
5. بدون سیاست، نفرت، پزشکی.
6. خروجی فقط JSON.
"""


def _fallback_script(topic: dict[str, Any], kind: str) -> dict[str, Any]:
    src = topic.get("source_hint", "منابع معتبر")
    if kind == "short":
        body = (
            f"سلام. یک یادآوری کوتاه: {topic['title_hint']}. "
            f"{topic['focus']}. "
            f"بر اساس {src}، امروز کمی بیشتر اهل تأمل و مهربانی باشیم. "
            f"برای متن دقیق به {topic.get('source_ref', src)} مراجعه کنید. خداحافظ."
        )
        duration_hint = 45
    else:
        body = (
            f"بسم الله الرحمن الرحیم. سلام. "
            f"موضوع امروز از منابع معتبر است: {topic['title_hint']}. "
            f"تمرکز ما: {topic['focus']}. "
            f"منبع ما {src} است. بدون نقل جعلی، از این آموزه‌ها برای صبر و صداقت الهام می‌گیریم. "
            f"لطفاً اصل متن را در {topic.get('source_ref', src)} بخوانید. "
            f"سپاس از همراهی‌تان. خداحافظ."
        )
        duration_hint = 420
    return {
        "title": topic["title_hint"][:90],
        "description": f"{topic['title_hint']}\n\nمنبع: {src}\n\n#امام_علی #نهج_البلاغه #تأمل",
        "script": body,
        "sources": [src],
        "tags": ["امام علی", "نهج البلاغه", "اخلاق", "تأمل"],
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
        "۳۵–۵۰ ثانیه صحبت، لحن سینمایی کوتاه."
        if kind == "short"
        else "۶–۱۰ دقیقه، مقدمه، ۲–۳ نکته با ارجاع منبع، جمع‌بندی."
    )
    user = (
        f"{research_brief}\nمدت: {length_rule}\n"
        f"سیاست: {json.dumps(policy, ensure_ascii=False)}\n"
        "JSON: title, description, script, sources, tags, duration_hint_seconds"
    )
    resp = client.chat.completions.create(
        model=env("OPENAI_MODEL") or "gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.35,
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
            print(f"[script] failed: {e}")
            out = _fallback_script(topic, kind)
            out["error"] = str(e)
            return out
    return _fallback_script(topic, kind)
