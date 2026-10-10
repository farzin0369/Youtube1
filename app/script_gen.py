"""Script generator — Qwen (Chinese model) first, then OpenAI, then fallback."""
from __future__ import annotations

import json
from typing import Any

from app.utils import (
    clean_persian,
    env,
    has_openai,
    has_qwen,
    load_content_policy,
    qwen_client_kwargs,
)

SYSTEM_PROMPT = """تو نویسنده و کارگردان محتوای فارسی کانال معنوی ImamAli110 هستی.
خروجی فقط JSON معتبر با کلیدهای title, description, script, sources, tags, duration_hint_seconds, scene_plan باشد.
scene_plan آرایه‌ای از صحنه‌هاست. هر صحنه باید کلیدهای spoken_text، visual_prompt، on_screen_text و duration_hint_seconds داشته باشد.
spoken_text متن دقیق گویندگی همان صحنه است. script باید دقیقاً از اتصال spoken_textها با یک فاصله ساخته شود.
visual_prompt باید یک دستور تصویری انگلیسی مشخص و مستقیم باشد که همان کنش یا احساس را نمایش دهد؛ از تصویر عمومی و نامرتبط پرهیز کن.
on_screen_text باید فارسی، کوتاه و حداکثر ۸ کلمه باشد. مدت هر صحنه مثبت باشد.
عنوان با «Imam Ali ✨ » شروع شود. فارسی روان و انسانی بنویس. آیه، حدیث، منبع یا نقل‌قول جعل نکن؛ نقل مستقیم باید منبع داشته باشد.
تصویر نباید متن، زیرنویس، لوگو یا واترمارک داشته باشد. چهرهٔ پیامبران یا چهرهٔ مقدسات را بازنمایی نکن.
"""

def _visual_prompt_for_text(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("مهربان", "لبخند", "دلجویی", "کمک", "محبت", "بخشش")):
        return "Cinematic realistic close shot of ordinary people helping or comforting one another, visible kind action, natural Persian everyday setting, warm daylight, no text, no logo, no watermark"
    if any(k in t for k in ("آرام", "آرامش", "نگران", "صبر", "تحمل")):
        return "Cinematic realistic scene of a person calmly breathing and listening beside a sunlit window, relaxed hands, gentle camera movement, no text, no logo, no watermark"
    if any(k in t for k in ("نور", "روشن", "امید")):
        return "A person opening curtains as morning light fills a modest room, a second person visibly encouraged, realistic cinematic lighting, no text, no logo, no watermark"
    if any(k in t for k in ("راست", "صداقت", "امانت")):
        return "A realistic cinematic moment of a person honestly returning a lost item to its owner, clear exchange and sincere expressions, no text, no logo, no watermark"
    return "A realistic cinematic live-action scene directly depicting the action and emotion described in the narration, clear subject and natural behavior, no text, no logo, no watermark"


def _short_on_screen_text(text: str, limit: int = 42) -> str:
    words = str(text).split()
    result = ""
    for word in words:
        candidate = (result + " " + word).strip()
        if len(candidate) > limit:
            break
        result = candidate
    return result or str(text)[:limit]


def _fallback_scenes(body: str) -> list[dict[str, Any]]:
    import re
    parts = [part.strip() for part in re.split(r"(?<=[.!?؟۔])\s+", str(body).strip()) if part.strip()]
    if not parts and body.strip():
        parts = [body.strip()]
    return [{
        "spoken_text": part,
        "visual_prompt": _visual_prompt_for_text(part),
        "on_screen_text": _short_on_screen_text(part),
        "duration_hint_seconds": max(2.5, min(8.0, len(part) / 13.0)),
    } for part in parts]



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
        "scene_plan": _fallback_scenes(body),
        "generated_by": "fallback",
    }


def _normalize(data: dict[str, Any], topic: dict[str, Any], kind: str) -> dict[str, Any]:
    data["script"] = clean_persian(str(data.get("script", ""))).strip()
    title = str(data.get("title") or topic["title_hint"])[:100]
    if not title.startswith("Imam Ali ✨"):
        title = "Imam Ali ✨ " + title
    data["title"] = title[:100]
    data["description"] = str(data.get("description", ""))
    data["sources"] = data.get("sources") or [topic["source_hint"]]
    data["tags"] = data.get("tags") or ["امام علی", "اخلاق"]
    data["duration_hint_seconds"] = int(data.get("duration_hint_seconds") or (45 if kind == "short" else 420))

    raw_scenes = data.get("scene_plan")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raw_scenes = _fallback_scenes(data["script"])
    normalized = []
    for raw in raw_scenes:
        if not isinstance(raw, dict):
            continue
        spoken = clean_persian(str(raw.get("spoken_text") or "")).strip()
        if not spoken:
            continue
        visual = str(raw.get("visual_prompt") or _visual_prompt_for_text(spoken)).strip()
        on_screen = _short_on_screen_text(clean_persian(str(raw.get("on_screen_text") or spoken)).strip())
        try:
            duration = max(1.5, float(raw.get("duration_hint_seconds") or 4.0))
        except (TypeError, ValueError):
            duration = 4.0
        normalized.append({
            "spoken_text": spoken,
            "visual_prompt": visual,
            "on_screen_text": on_screen,
            "duration_hint_seconds": duration,
        })
    if not normalized:
        normalized = _fallback_scenes(data["script"])
    # The narration is always derived from the same scene contract used by the visual engine.
    data["scene_plan"] = normalized
    data["script"] = " ".join(scene["spoken_text"] for scene in normalized)
    return data


def _chat_json(api_key: str, base_url: str, model: str, brief: str, kind: str, label: str) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
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
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "temperature": 0.55,
    }
    # Some Qwen deployments support json_object; if not, model still asked for JSON only.
    try:
        resp = client.chat.completions.create(**kwargs, response_format={"type": "json_object"})
    except Exception:
        resp = client.chat.completions.create(**kwargs)
    raw = resp.choices[0].message.content or "{}"
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
    data = json.loads(raw)
    data["generated_by"] = label
    return data


def _call_qwen(topic: dict[str, Any], kind: str, brief: str) -> dict[str, Any]:
    kw = qwen_client_kwargs()
    model = env("QWEN_MODEL") or env("DASHSCOPE_MODEL") or "qwen-plus"
    data = _chat_json(kw["api_key"], kw["base_url"], model, brief, kind, f"qwen:{model}")
    return _normalize(data, topic, kind)


def _call_openai(topic: dict[str, Any], kind: str, brief: str) -> dict[str, Any]:
    model = env("OPENAI_MODEL") or "gpt-4o-mini"
    data = _chat_json(
        env("OPENAI_API_KEY") or "",
        env("OPENAI_API_BASE") or "https://api.openai.com/v1",
        model,
        brief,
        kind,
        f"openai:{model}",
    )
    return _normalize(data, topic, kind)


def generate_script(topic: dict[str, Any], kind: str, research_brief: str) -> dict[str, Any]:
    # 1) Qwen first (user request)
    if has_qwen():
        try:
            return _call_qwen(topic, kind, research_brief)
        except Exception as e:
            print(f"[script] Qwen failed: {e}")
    # 2) OpenAI fallback
    if has_openai():
        try:
            return _call_openai(topic, kind, research_brief)
        except Exception as e:
            print(f"[script] OpenAI failed: {e}")
            out = _fallback_script(topic, kind)
            out["error"] = str(e)
            return out
    return _fallback_script(topic, kind)
