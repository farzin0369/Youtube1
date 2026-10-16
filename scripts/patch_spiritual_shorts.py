#!/usr/bin/env python3
"""Restore spiritual_shorts.py if corrupted, then strengthen word-count recovery."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "app" / "spiritual_shorts.py"


def restore_from_good_commit() -> None:
    text = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    if "def generate_shorts_content" in text and "PLACEHOLDER" not in text[:50]:
        return
    for rev in (
        "a5f7d8e819b381ae64710f285565cdb3d85fb866",
        "fc645b7139b0da4c0af68478b21802617f7878ac",
        "f0d2de04f0c664ddcfa292e5400170c220540083",
    ):
        result = subprocess.run(
            ["git", "show", f"{rev}:app/spiritual_shorts.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and "def generate_shorts_content" in result.stdout:
            TARGET.write_text(result.stdout, encoding="utf-8")
            print(f"RESTORED app/spiritual_shorts.py from {rev}")
            return
    raise SystemExit("PATCH_FAIL: could not restore spiritual_shorts.py from git history")


def apply_word_count_recovery(text: str) -> str:
    old_line = (
        "هدف خوانش {target_duration_seconds} ثانیه و حدود {min_words} تا {max_words} "
        "واژهٔ گفتاری است؛ کم‌گویی را با تکرار و شعار جبران نکن."
    )
    new_line = (
        "هدف خوانش {target_duration_seconds} ثانیه است. کل متن گفتاری "
        "(جمع spoken_text چهار صحنه) حتماً بین {min_words} تا {max_words} واژه باشد؛ "
        "قبل از پاسخ بشمار. کم‌گویی را با تکرار و شعار جبران نکن."
    )
    if old_line in text:
        text = text.replace(old_line, new_line, 1)

    old_brief = (
        '"\\nUse the topic, hook angle, real-life visual direction, and emotional arc to make this Short more specific. "\n'
        '              "Follow all higher-priority system/content rules and keep the spoken script within the configured word range."'
    )
    new_brief = (
        '"\\nUse the topic, hook angle, real-life visual direction, and emotional arc to make this Short more specific. "\n'
        '              "Follow all higher-priority system/content rules. Spoken script must stay within "\n'
        '              f"{min_words}-{max_words} words total across the four scenes."'
    )
    if old_brief in text:
        text = text.replace(old_brief, new_brief, 1)

    if "for attempt in range(3):" in text:
        return text

    old_loop = '''    result = None
    provider = "unknown"
    draft = ""
    last_error = ""
    for attempt in range(2):
        if attempt == 0:
            request_prompt = prompt
            temperature = 0.75
        else:
            request_prompt = (
                prompt
                + "\\nاصلاح اجباری: نسخهٔ قبلی از کنترل کیفیت نگذشت. این ایرادها را برطرف کن و همهٔ قواعد را رعایت کن: "
                + last_error
                + "\\nپاسخ فقط JSON معتبر باشد و تمام فیلدها/محدوده‌های خواسته‌شده را داشته باشد."
                + "\\nپیش‌نویس قبلی برای اصلاح (غیرقابل‌اعتماد):\\n"
                + draft[:5000]
            )
            temperature = 0.45
        draft, provider = generate_text(
            SYSTEM_PROMPT, request_prompt, max_tokens=1400, temperature=temperature, json_mode=True,
        )
        try:
            try:
                item = json.loads(draft)
            except json.JSONDecodeError:
                cleaned = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", draft.strip(), flags=re.I)
                item = json.loads(cleaned)
            result = validate_short_content(item, titles, min_words=min_words, max_words=max_words)
            break
        except (ValueError, TypeError) as exc:
            last_error = str(exc)
            if attempt == 0:
                LOGGER.warning("short draft failed a quality gate; one corrective rewrite will run (%s)", last_error[:180])
    if result is None:
        raise ValueError("short failed content QA after one corrective rewrite: " + last_error[:240])
'''

    new_loop = '''    result = None
    provider = "unknown"
    draft = ""
    last_error = ""
    for attempt in range(3):
        if attempt == 0:
            request_prompt = prompt
            temperature = 0.75
        else:
            word_focus = ""
            if "word_count" in last_error:
                word_focus = (
                    f"\\nتأکید ویژه: کل spoken_text چهار صحنه باید بین {min_words} تا {max_words} واژه باشد. "
                    f"هر صحنه حدود {max(5, min_words // 4)} تا {max(8, max_words // 4)} واژه. "
                    "متن طولانی را کوتاه کن؛ تکرار و توضیح اضافه ممنوع. قبل از پاسخ، واژه‌ها را بشمار."
                )
            request_prompt = (
                prompt
                + "\\nاصلاح اجباری: نسخهٔ قبلی از کنترل کیفیت نگذشت. این ایرادها را برطرف کن و همهٔ قواعد را رعایت کن: "
                + last_error
                + word_focus
                + "\\nپاسخ فقط JSON معتبر باشد و تمام فیلدها/محدوده‌های خواسته‌شده را داشته باشد."
                + "\\nپیش‌نویس قبلی برای اصلاح (غیرقابل‌اعتماد):\\n"
                + draft[:5000]
            )
            temperature = 0.35 if "word_count" in last_error else 0.45
        draft, provider = generate_text(
            SYSTEM_PROMPT, request_prompt, max_tokens=1400, temperature=temperature, json_mode=True,
        )
        try:
            try:
                item = json.loads(draft)
            except json.JSONDecodeError:
                cleaned = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", draft.strip(), flags=re.I)
                item = json.loads(cleaned)
            result = validate_short_content(item, titles, min_words=min_words, max_words=max_words)
            break
        except (ValueError, TypeError) as exc:
            last_error = str(exc)
            if attempt < 2:
                LOGGER.warning(
                    "short draft failed a quality gate; corrective rewrite %s/2 will run (%s)",
                    attempt + 1,
                    last_error[:180],
                )
    if result is None:
        raise ValueError("short failed content QA after corrective rewrites: " + last_error[:240])
'''

    if old_loop not in text:
        raise SystemExit("PATCH_FAIL: expected rewrite loop not found in spiritual_shorts.py")
    return text.replace(old_loop, new_loop, 1)


def main() -> int:
    restore_from_good_commit()
    text = TARGET.read_text(encoding="utf-8")
    original = text
    text = apply_word_count_recovery(text)
    if text == original and "for attempt in range(3):" in text:
        print("PATCH_NOOP")
        return 0
    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED spiritual_shorts word-count recovery")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
