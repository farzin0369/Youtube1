"""Script generator with a fully local path; OpenAI is optional."""
from __future__ import annotations
import json
from typing import Any
from app.local_ai import local_enabled, ollama_generate
from app.utils import clean_persian, env, has_openai, load_content_policy

SYSTEM_PROMPT="""تو نویسنده اسکریپت فارسی برای ImamAli110 هستی.
هرگز آیه یا حدیث جعل نکن. فقط از brief استفاده کن. اگر متن دقیق نیست، پارافریز کن.
لحن آرام، سینمایی، مردانه و محترمانه. خروجی فقط JSON با title, description, script, sources, tags, duration_hint_seconds."""

def _fallback_script(topic:dict[str,Any],kind:str)->dict[str,Any]:
    src=topic.get("source_hint","منابع معتبر")
    body=(f"یک یادآوری کوتاه: {topic['title_hint']}. {topic['focus']}. بر اساس {src}، امروز کمی بیشتر اهل تأمل و مهربانی باشیم. برای متن دقیق به {topic.get('source_ref',src)} مراجعه کنید.") if kind=="short" else (f"بسم الله الرحمن الرحیم. موضوع امروز: {topic['title_hint']}. تمرکز ما: {topic['focus']}. منبع: {src}. بدون نقل جعلی، از این آموزه برای صبر و صداقت الهام می‌گیریم.")
    return {"title":("Imam Ali ✨ " + topic["title_hint"])[:100],"description":f"{topic['title_hint']}\n\nمنبع: {src}","script":body,"sources":[src],"tags":["امام علی","نهج البلاغه","اخلاق"],"duration_hint_seconds":45 if kind=="short" else 420,"generated_by":"fallback-local"}

def _normalize(data:dict[str,Any],topic:dict[str,Any],kind:str)->dict[str,Any]:
    data["script"]=clean_persian(str(data.get("script","")))
    data["title"]=str(data.get("title") or ("Imam Ali ✨ " + topic["title_hint"]))[:100]\n    if not data["title"].startswith("Imam Ali ✨"):\n        data["title"]="Imam Ali ✨ " + data["title"]
    data["description"]=str(data.get("description",""))
    data["sources"]=data.get("sources") or [topic["source_hint"]]
    data["tags"]=data.get("tags") or ["امام علی","اخلاق"]
    data["duration_hint_seconds"]=int(data.get("duration_hint_seconds") or (45 if kind=="short" else 420))
    return data

def _call_local(topic:dict[str,Any],kind:str,brief:str)->dict[str,Any]:
    prompt=f"{brief}\nسیاست: {json.dumps(load_content_policy(),ensure_ascii=False)}\nمدت: {'۳۵ تا ۵۰ ثانیه' if kind=='short' else '۶ تا ۱۰ دقیقه'}\nJSON only."
    data=_normalize(json.loads(ollama_generate(prompt,SYSTEM_PROMPT,env("LOCAL_LLM_MODEL") or "qwen2.5:7b")),topic,kind)
    data["generated_by"]="local-ollama"
    return data

def _call_openai(topic:dict[str,Any],kind:str,brief:str)->dict[str,Any]:
    from openai import OpenAI
    client=OpenAI(api_key=env("OPENAI_API_KEY"),base_url=env("OPENAI_API_BASE") or "https://api.openai.com/v1")
    resp=client.chat.completions.create(model=env("OPENAI_MODEL") or "gpt-4o-mini",messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":f"{brief}\nJSON only."}],temperature=0.35,response_format={"type":"json_object"})
    data=_normalize(json.loads(resp.choices[0].message.content or "{}"),topic,kind); data["generated_by"]="openai"; return data

def generate_script(topic:dict[str,Any],kind:str,research_brief:str)->dict[str,Any]:
    if local_enabled():
        try: return _call_local(topic,kind,research_brief)
        except Exception as e:
            print(f"[local-script] failed: {e}")
            out=_fallback_script(topic,kind); out["error"]=str(e); return out
    if has_openai():
        try: return _call_openai(topic,kind,research_brief)
        except Exception as e:
            out=_fallback_script(topic,kind); out["error"]=str(e); return out
    return _fallback_script(topic,kind)
