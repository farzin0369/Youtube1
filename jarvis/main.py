import json
import os
from openai import OpenAI
import time
import sys
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    timeout=12.0,
    max_retries=0,
)

SYSTEM_PROMPT = (
    "تو Jarvis، دستیار هوشمند شخصی کاربر هستی. پاسخ‌ها را دقیق، مفید و طبیعی بده. "
    "زبان اصلی فارسی است، مگر اینکه کاربر زبان دیگری بخواهد. از Markdown برای خوانایی استفاده کن."
)


def ask_jarvis(prompt: str, history: list[dict] | None = None) -> str:
    models = [
        "minimax/minimax-m3.1-flash:free",
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
    ]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in (history or [])[-24:]:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content[:12000]})
    messages.append({"role": "user", "content": prompt})

    last_error = None
    for model in models:
        try:
            started = time.monotonic()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=700,
                temperature=0.4,
            )
            answer = response.choices[0].message.content or "پاسخی دریافت نشد."
            print(f"مدل {model} پاسخ را در {time.monotonic() - started:.1f} ثانیه داد.", file=sys.stderr)
            return answer
        except Exception as exc:
            last_error = exc
            print(f"مدل {model} سریع پاسخ نداد یا در دسترس نبود؛ تلاش با مدل بعدی...")
    raise last_error


if __name__ == "__main__":
    prompt = os.getenv("PROMPT", "سلام جارویس")
    try:
        history = json.loads(os.getenv("HISTORY", "[]"))
        if not isinstance(history, list):
            history = []
    except json.JSONDecodeError:
        history = []
    print(ask_jarvis(prompt, history))
