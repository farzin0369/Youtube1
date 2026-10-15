#!/usr/bin/env python3
"""Slightly widen hook QA and ensure four recovery attempts for weak cloud models."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_shorts.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    original = text

    # Soften opening hook: 4-16 words (was 4-13) so small Persian models can pass.
    text = text.replace(
        'if not 4 <= first_words <= 13 or "؟" not in first:\n        raise ValueError("opening_hook_must_be_a_specific_short_question")',
        'if not 4 <= first_words <= 16 or "؟" not in first:\n        raise ValueError("opening_hook_must_be_a_specific_short_question")',
        1,
    )

    # Prefer four recovery attempts when still at three.
    if "for attempt in range(3):" in text and "for attempt in range(4):" not in text:
        text = text.replace("for attempt in range(3):", "for attempt in range(4):", 1)
        text = text.replace("if attempt < 2:", "if attempt < 3:", 1)
        text = text.replace(
            '"short draft failed a quality gate; corrective rewrite %s/2 will run (%s)"',
            '"short draft failed a quality gate; corrective rewrite %s/3 will run (%s)"',
            1,
        )

    # Stronger recovery when scenes array is missing.
    marker = 'if "opening_hook" in last_error or "hook_must" in last_error:'
    if marker in text and "exactly four authored scenes" not in text[text.find("word_focus"):text.find("word_focus")+1200]:
        insert_after = marker
        addition = '''
            if "four authored scenes" in last_error or "scene_" in last_error:
                word_focus += (
                    "\\nساختار اجباری: دقیقاً چهار شیء در آرایهٔ scenes با moodهای hook, calm, reassuring, motivational. "
                    "script باید اتصال عین spoken_text همان چهار صحنه با یک فاصله باشد."
                )
'''
        # Only add if not already present
        if "ساختار اجباری: دقیقاً چهار شیء" not in text:
            text = text.replace(
                '''            if "opening_hook" in last_error or "hook_must" in last_error:
                word_focus += (
                    "\\nقلاب: جملهٔ اول spoken_text صحنهٔ hook باید یک سؤال کوتاه فارسی با علامت ؟ باشد، "
                    "بین ۴ تا ۱۳ واژه، بدون سلام و مقدمهٔ کلی. مثال: «چرا یک مکث کوتاه قبل از پاسخ، آرامش می‌آورد؟»"
                )
''',
                '''            if "opening_hook" in last_error or "hook_must" in last_error:
                word_focus += (
                    "\\nقلاب: جملهٔ اول spoken_text صحنهٔ hook باید یک سؤال کوتاه فارسی با علامت ؟ باشد، "
                    "بین ۴ تا ۱۶ واژه، بدون سلام و مقدمهٔ کلی. مثال: «چرا یک مکث کوتاه قبل از پاسخ، آرامش می‌آورد؟»"
                )
            if "four authored scenes" in last_error or "scene_" in last_error:
                word_focus += (
                    "\\nساختار اجباری: دقیقاً چهار شیء در آرایهٔ scenes با moodهای hook, calm, reassuring, motivational. "
                    "script باید اتصال عین spoken_text همان چهار صحنه با یک فاصله باشد."
                )
''',
                1,
            )

    if text == original:
        print("PATCH_NOOP")
        return 0
    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED shorts QA tolerance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
