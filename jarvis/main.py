"""Secret-safe Jarvis adapter for the OpenRouter chat-completions API."""

import os
import sys
import time
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Confirmed in OpenRouter's public catalog on 2026-10-22.
DEFAULT_MODEL = "minimax/minimax-m3.1-flash:free"
SYSTEM_PROMPT = (
    "تو Jarvis، دستیار هوشمند شخصی کاربر هستی. دقیق، مفید و طبیعی پاسخ بده. "
    "زبان اصلی فارسی است مگر کاربر زبان دیگری بخواهد. از Markdown برای خوانایی استفاده کن."
)


def _messages(prompt: str, history: Any) -> list[dict[str, str]]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("پیام خالی است؛ یک درخواست بنویسید.")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if isinstance(history, list):
        for item in history[-16:]:
            if not isinstance(item, dict):
                continue
            role, content = item.get("role"), item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content[:6000]})
    messages.append({"role": "user", "content": prompt[:12000]})
    return messages


def ask_jarvis(prompt: str, history: Any = None, *, client=None) -> str:
    """Request one completion; never falls back to local or paid models."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "کلید OpenRouter در دسترس نیست؛ secret با نام OPENROUTER_API_KEY را در GitHub Actions بررسی کنید."
        )
    messages = _messages(prompt, history)
    if client is None:
        client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key, timeout=45.0, max_retries=0)

    started = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL, messages=messages, max_tokens=900, temperature=0.4
        )
    except AuthenticationError as exc:
        raise RuntimeError("OpenRouter احراز هویت را رد کرد؛ اعتبار secret را بررسی کنید.") from exc
    except RateLimitError as exc:
        raise RuntimeError("سهمیه یا محدودیت نرخ OpenRouter اعمال شد؛ بعداً دوباره تلاش کنید.") from exc
    except APITimeoutError as exc:
        raise RuntimeError("درخواست OpenRouter پس از مهلت تعیین‌شده timeout شد.") from exc
    except APIConnectionError as exc:
        raise RuntimeError("ارتباط با OpenRouter برقرار نشد؛ اتصال سرویس را بررسی کنید.") from exc
    except APIStatusError as exc:
        status = getattr(exc, "status_code", None)
        if status == 404:
            message = "مدل رایگان انتخاب‌شده در OpenRouter در دسترس نیست."
        elif status == 402:
            message = "اعتبار یا سهمیهٔ رایگان OpenRouter کافی نیست."
        elif status == 429:
            message = "محدودیت نرخ یا سهمیهٔ مدل رایگان OpenRouter اعمال شد."
        else:
            message = f"OpenRouter خطای HTTP {status or 'نامشخص'} برگرداند."
        raise RuntimeError(message) from exc
    except Exception as exc:
        # Provider exception text can contain request data: do not print it.
        raise RuntimeError("پاسخ OpenRouter قابل پردازش نبود؛ JSON یا ساختار پاسخ نامعتبر است.") from exc

    try:
        answer = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        raise RuntimeError("ساختار پاسخ OpenRouter نامعتبر یا خالی بود.") from exc
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("مدل OpenRouter پاسخ متنی خالی برگرداند.")
    print(f"Jarvis model={DEFAULT_MODEL} elapsed={time.monotonic() - started:.1f}s", file=sys.stderr)
    return answer.strip()


if __name__ == "__main__":
    import json

    try:
        history = json.loads(os.getenv("HISTORY", "[]"))
    except (json.JSONDecodeError, TypeError):
        history = []
    try:
        print(ask_jarvis(os.getenv("PROMPT", "سلام جارویس"), history))
    except Exception as exc:
        print(f"خطای Jarvis: {exc}", file=sys.stderr)
        raise SystemExit(1)
