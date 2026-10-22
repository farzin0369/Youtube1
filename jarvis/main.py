import json
import os
import sys
import time
from openai import OpenAI

SYSTEM_PROMPT = (
    "تو Jarvis، دستیار هوشمند شخصی کاربر هستی. دقیق، مفید و طبیعی پاسخ بده. "
    "زبان اصلی فارسی است مگر کاربر زبان دیگری بخواهد. از Markdown برای خوانایی استفاده کن."
)

MODELS = [
    "minimax/minimax-m3.1-flash:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

def ask_jarvis(prompt: str, history=None) -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY تنظیم نشده است؛ آن را در GitHub Secrets تعریف کنید.")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, timeout=45.0, max_retries=0)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in (history or [])[-16:]:
        if not isinstance(item, dict):
            continue
        role, content = item.get("role"), item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content[:6000]})
    messages.append({"role": "user", "content": prompt[:12000]})
    errors = []
    for model in MODELS:
        try:
            started = time.monotonic()
            response = client.chat.completions.create(
                model=model, messages=messages, max_tokens=900, temperature=0.4
            )
            answer = response.choices[0].message.content
            if not answer or not answer.strip():
                raise RuntimeError("مدل پاسخ خالی برگرداند.")
            print(f"Jarvis model={model} elapsed={time.monotonic()-started:.1f}s", file=sys.stderr)
            return answer.strip()
        except Exception as exc:
            errors.append(f"{model}: {type(exc).__name__}")
            print(f"مدل {model} ناموفق بود؛ تلاش با مدل رایگان بعدی.", file=sys.stderr)
    raise RuntimeError("همه مدل‌های رایگان OpenRouter ناموفق بودند: " + "; ".join(errors))

if __name__ == "__main__":
    prompt = os.getenv("PROMPT", "سلام جارویس").strip()
    try:
        history = json.loads(os.getenv("HISTORY", "[]"))
        if not isinstance(history, list):
            history = []
    except (json.JSONDecodeError, TypeError):
        history = []
    try:
        print(ask_jarvis(prompt, history))
    except Exception as exc:
        print(f"خطای Jarvis: {exc}", file=sys.stderr)
        raise SystemExit(1)
