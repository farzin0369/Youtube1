#!/usr/bin/env python3
"""Add hook-specific recovery hints to spiritual_shorts rewrite loop."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_shorts.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    original = text

    old = '''            word_focus = ""
            if "word_count" in last_error:
                word_focus = (
                    f"\\nتأکید ویژه: کل spoken_text چهار صحنه باید بین {min_words} تا {max_words} واژه باشد. "
                    f"هر صحنه حدود {max(5, min_words // 4)} تا {max(8, max_words // 4)} واژه. "
                    "متن طولانی را کوتاه کن؛ تکرار و توضیح اضافه ممنوع. قبل از پاسخ، واژه‌ها را بشمار."
                )
'''

    new = '''            word_focus = ""
            if "word_count" in last_error:
                word_focus = (
                    f"\\nتأکید ویژه: کل spoken_text چهار صحنه باید بین {min_words} تا {max_words} واژه باشد. "
                    f"هر صحنه حدود {max(5, min_words // 4)} تا {max(8, max_words // 4)} واژه. "
                    "متن طولانی را کوتاه کن؛ تکرار و توضیح اضافه ممنوع. قبل از پاسخ، واژه‌ها را بشمار."
                )
            if "opening_hook" in last_error or "hook_must" in last_error:
                word_focus += (
                    "\\nقلاب: جملهٔ اول spoken_text صحنهٔ hook باید یک سؤال کوتاه فارسی با علامت ؟ باشد، "
                    "بین ۴ تا ۱۳ واژه، بدون سلام و مقدمهٔ کلی. مثال: «چرا یک مکث کوتاه قبل از پاسخ، آرامش می‌آورد؟»"
                )
'''

    if "opening_hook" in text and "بین ۴ تا ۱۳ واژه" in text:
        print("PATCH_NOOP")
        return 0

    if old not in text:
        # tolerate already-patched range(3) without the old exact block
        if "if \"word_count\" in last_error:" not in text:
            raise SystemExit("PATCH_FAIL: word_count recovery block missing")
        raise SystemExit("PATCH_FAIL: exact word_focus block not found")

    text = text.replace(old, new, 1)
    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED shorts hook recovery")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
