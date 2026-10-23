#!/usr/bin/env python3
"""Free, dependency-free preflight for YouTube hooks and title/thumbnail pairing.

This is an advisory heuristic, not a prediction of views. It does not call an
LLM, upload videos, or modify rendered media.
"""
from __future__ import annotations
import argparse
import re

CURIOSITY = ("چرا", "راز", "اگر", "هیچ‌کس", "چطور", "چه می‌شود", "قبل از", "اشتباه")
SPECIFIC = ("امروز", "یک", "سه", "۵", "5", "راه", "دقیقه", "بار")
FLUFF = ("باورنکردنی", "عالی", "فوق‌العاده", "بهترین", "شگفت‌انگیز", "وایرال")

def hook_score(text: str) -> tuple[int, list[str]]:
    t = text.strip()
    score, notes = 0, []
    if not t:
        return 0, ["هوک خالی است."]
    if len(t) <= 95:
        score += 2
        notes.append("کوتاه و مناسب شروع است.")
    else:
        notes.append("هوک را کوتاه‌تر کن؛ جملهٔ اول باید سریع فهمیده شود.")
    if any(x in t for x in CURIOSITY):
        score += 2
        notes.append("نشانه‌ای از کنجکاوی دارد.")
    else:
        notes.append("یک سؤال، تضاد یا شکاف کنجکاوی اضافه کن.")
    if any(x in t for x in SPECIFIC):
        score += 1
        notes.append("جزئیات نسبتاً مشخص دارد.")
    if any(x in t for x in FLUFF):
        notes.append("از صفت‌های کلیشه‌ای کم کن و وعدهٔ مشخص بده.")
    if re.search(r"[؟?]", t):
        score += 1
        notes.append("پرسش دارد؛ مطمئن شو پاسخ آن در ویدئو داده می‌شود.")
    return min(score, 6), notes

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hook", default="", help="جملهٔ آغازین ویدئو")
    p.add_argument("--title", default="", help="عنوان ویدئو")
    p.add_argument("--thumb", default="", help="متن روی تصویر بندانگشتی")
    args = p.parse_args()
    if not any((args.hook, args.title, args.thumb)):
        p.error("حداقل یکی از --hook، --title یا --thumb لازم است")
    if args.hook:
        score, notes = hook_score(args.hook)
        print(f"امتیاز آزمایشی هوک: {score}/6 (این امتیاز پیش‌بینی بازدید نیست)")
        for n in notes:
            print(f"- {n}")
    if args.title:
        title = args.title.strip()
        print(f"\nعنوان: {len(title)} نویسه")
        if len(title) > 60:
            print("- هشدار: عنوان از ۶۰ نویسه بیشتر است؛ نسخهٔ کوتاه‌تر هم بررسی کن.")
        if len(title) > 40:
            print("- روی موبایل ممکن است بخش پایانی عنوان دیده نشود.")
    if args.title and args.thumb:
        title_words = set(re.findall(r"\w+", args.title.casefold()))
        thumb_words = set(re.findall(r"\w+", args.thumb.casefold()))
        overlap = title_words & thumb_words
        print(f"\nمتن تصویر بندانگشتی: {len(args.thumb.split())} کلمه")
        if len(args.thumb.split()) > 3:
            print("- هشدار: متن تصویر را به حداکثر ۳ کلمه کاهش بده.")
        if overlap:
            print("- واژه‌های تکراری بین عنوان و تصویر: " + "، ".join(sorted(overlap)))
            print("- تصویر باید همان وعده را با واژه‌های متفاوت منتقل کند.")
        else:
            print("- هم‌پوشانی واژگانی مستقیمی پیدا نشد؛ وعدهٔ هر دو را دستی تطبیق بده.")
    print("\nیادآوری: این ابزار فقط بازبینی مقدماتی است؛ کیفیت محتوا و نتیجهٔ واقعی را تضمین نمی‌کند.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
