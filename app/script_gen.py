"""High-quality Persian script: OpenAI first, modern fluent tone."""
from __future__ import annotations

import json
from typing import Any

from app.utils import clean_persian, env, has_openai, load_content_policy

SYSTEM_PROMPT = """تو نویسندهٔ حرفه‌ای اسکریپت یوتیوب فارسی هستی برای کانال معنوی ImamAli110.

سبک الزامی:
- فارسی امروزی، روان، گرم و انسانی — نه کتابی، نه رباتی، نه شعارزده
- مثل یک گویندهٔ با‌تجربه که آرام و صمیمی حرف می‌زند
- جمله‌های کوتاه و قابل شنیدن
- لحن مردانه، محترم، بدون اغراق

قوانین سخت:
1) هرگز آیه یا حدیث جعل نکن
2) اگر نقل مستقیم نداری، با زبان خودت معنا را بگو و منبع کلی را ذکر کن
3) بدون سیاست، نفرت، پزشکی
4) خروجی فقط JSON معتبر با کلیدها: title, description, script, sources, tags, duration_hint_seconds

title باید با «Imam Ali ✨ » شروع شود.
script فقط متن گفتاری باشد (بدون مرحله‌بندی مثل [مقدمه]).
"""


def _fallback_script(topic: dict[str, Any], kind: str) -> dict[str, Any]:
    src = topic.get("source_hint", "منابع معتبر")
    if kind == "short":
        body = (
            f"گاهی فقط یک یادآوری کوچک کافی‌ست. "
            f"موضوع امروز: {topic['title_hint']}. "
            f"{topic['focus']}. "
            f"اگر فرصت داشتی، نگاهی به {src} بینداز؛ اصل کلام آنجاست. "
            f"برای خودت و اطرافیانت، یک قدم آرام‌تر و مهربان‌تر باش."
        )
        dur = 45
    else:
        body = (
            f"سلام. امروز می‌خواهیم کمی با آرامش دربارهٔ {topic['title_hint']} حرف بزنیم. "
            f"تمرکز ما روی {topic['focus']} است. "
            f"منبع اصلی ما {src} است؛ من اینجا به‌جای نقل جعلی، از روح این آموزه می‌گویم. "
            f"در زندگی روزمره، این حرف‌ها وقتی معنا پیدا می‌کنند که به رفتارمان برسند: "
            f"صبر در سختی، صداقت در گفتار، و مهربانی با آدم‌ها. "
            f"اگر خواستی عمیق‌تر بخوانی، برو سراغ اصل متن در {topic.get('source_ref', src)}. "
            f"ممنون که همراهی. خداحافظ."
        )
        dur = 420
    return {
        "title": ("Imam Ali ✨ " + topic["title_hint"])[:100],
        "description": f"{topic['title_hint']}\n\nمنبع: {src}\n\n#امام_علی #نهج_البلاغه",
        "script": body,
        "sources": [src],
        "tags": ["امام علی", "نهج البلاغه", "اخلاق", "تأمل"],
        "duration_hint_seconds": dur,
        "generated_by": "fallback-quality",
    }


def _normalize(data: dict[str, Any], topic: dict[str, Any], kind: str) -> dict[str, Any]:
    data["script"] = clean_persian(str(data.get("script", "")))
    title = str(data.get("title") or topic["title_hint"])[:100]
    if not title.startswith("Imam Ali ✨"):
        title = "Imam Ali ✨ " + title
    data["title"] = title[:100]
    data["description"] = str(data.get("description", ""))
    data["sources"] = data.get("sources") or [topic["source_hint"]]
    data["tags"] = data.get("tags") or ["امام علی", "اخلاق"]
    data["duration_hint_seconds"] = int(
        data.get("duration_hint_seconds") or (45 if kind == "short" else 420)
    )
    return data


def _call_openai(topic: dict[str, Any], kind: str, brief: str) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(
        api_key=env("OPENAI_API_KEY"),
        base_url=env("OPENAI_API_BASE") or "https://api.openai.com/v1",
    )
    length = (
        "حدود ۴۰ ثانیه گفتار؛ ۸۰ تا ۱۲۰ کلمه؛ طبیعی و شنیدنی."
        if kind == "short"
        else "۶ تا ۹ دقیقه؛ مقدمه کوتاه، ۲–۳ نکته، جمع‌بندی انسانی."
    )
    user = (
        f"{brief}\nمدت هدف: {length}\n"
        f"سیاست: {json.dumps(load_content_policy(), ensure_ascii=False)}\n"
        "فقط JSON."
    )
    resp = client.chat.completions.create(
        model=env("OPENAI_MODEL") or "gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.55,
        response_format={"type": "json_object"},
    )
    data = _normalize(json.loads(resp.choices[0].message.content or "{}"), topic, kind)
    data["generated_by"] = "openai-quality"
    return data


def generate_script(topic: dict[str, Any], kind: str, research_brief: str) -> dict[str, Any]:
    # Quality path: OpenAI first when key exists
    if has_openai():
        try:
            return _call_openai(topic, kind, research_brief)
        except Exception as e:
            print(f"[script] OpenAI failed: {e}")
            out = _fallback_script(topic, kind)
            out["error"] = str(e)
            return out
    return _fallback_script(topic, kind)
