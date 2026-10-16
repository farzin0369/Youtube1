#!/usr/bin/env python3
"""Build data/shorts_idea_bank.json from compact validated templates."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "shorts_idea_bank.json"
BRAND = "Imam Ali ✨ "

# Each row: topic, title, thumb, description, tags, four (spoken, visual, overlay)
TEMPLATES: list[tuple] = [
    ("مکث کوتاه", "یک مکث قبل از پاسخ", "مکث کوتاه", "گاهی یک نفس کوتاه قبل از جواب، هم به خودت احترام می‌گذارد هم به طرف مقابل.", ["آرامش", "ارتباط"],
     [("چرا یک مکث کوتاه قبل از پاسخ، آرامش می‌آورد؟", "person pausing before speaking", "مکث کوتاه؟"),
      ("خیلی وقت‌ها عجله در جواب، تنش را بیشتر می‌کند.", "stressed hands on table", "عجله و تنش"),
      ("امروز قبل از پاسخ، یک نفس آرام بگیر و بعد حرف بزن.", "person taking deep breath", "یک نفس"),
      ("همین مکث کوچک، می‌تواند احترام و آرامش بسازد.", "calm sunrise window light", "احترام و آرامش")]),
    ("شکر ساده", "یک شکر کوچک امروز", "شکر امروز", "شکرگزاری لازم نیست بزرگ باشد؛ یک چیز کوچک کافی است.", ["شکر", "امید"],
     [("اگر امروز فقط یک چیز را شکر کنی، چه می‌شود؟", "hand writing gratitude journal", "یک شکر؟"),
      ("گاهی ذهن فقط کمبودها را می‌بیند و خسته می‌شود.", "tired person looking window", "ذهن خسته"),
      ("امشب یک نعمت کوچک را روی کاغذ بنویس و مرور کن.", "pencil writing notebook", "بنویس"),
      ("همین یادآوری ساده، می‌تواند دل را سبک‌تر کند.", "warm evening tea cup", "دل سبک")]),
    ("قدم کوچک", "یک قدم کوچک کافی است", "قدم کوچک", "تغییر بزرگ از یک اقدام کوچک شروع می‌شود، نه از شعار.", ["عادت", "رشد فردی"],
     [("چرا منتظر انگیزهِ کامل می‌مانی تا شروع کنی؟", "person staring blank notebook", "شروع؟"),
      ("بسیاری از کارها زیر وزن انتظار بزرگ گیر می‌کنند.", "heavy backpack on floor", "وزن انتظار"),
      ("امروز فقط پنج دقیقه برای همان کار کنار بگذار.", "phone timer five minutes", "پنج دقیقه"),
      ("قدم کوچک و مداوم، مسیر را واقعی و ممکن می‌کند.", "footsteps on quiet path", "مسیر واقعی")]),
    ("توکل آرام", "توکل بدون عجله", "توکل آرام", "توکل یعنی تلاش مسئولانه و دل‌سپاری بدون شتاب و وعدهِ قطعی.", ["توکل", "امید"],
     [("اگر نتیجه دیر آمد، آیا تلاشت بی‌معنا بوده؟", "person waiting by window rain", "نتیجه دیر؟"),
      ("گاهی عجله، آرامش را از کار خوب می‌گیرد.", "clock hands close up", "عجله"),
      ("امروز کارت را درست انجام بده و نتیجه را بسپار.", "hands finishing simple task", "کار درست"),
      ("توکل آرام، قلب را سبک و مسیر را پایدار می‌کند.", "peaceful mountain path morning", "مسیر پایدار")]),
    ("صبح آرام", "ده دقیقهِ اول صبح", "صبح آرام", "شروع روز با عجله ذهن را شلوغ می‌کند.", ["صبح", "عادت"],
     [("اولین ده دقیقهِ صبحت مال کیست؟", "phone alarm morning bed", "ده دقیقه؟"),
      ("اگر با عجله و صفحهِ گوشی شروع کنی، ذهنت پر می‌شود.", "scrolling phone in bed", "ذهن پر"),
      ("فردا صبح سه نفس عمیق و یک نیت ساده بگذار.", "sunrise through curtains", "سه نفس"),
      ("همین شروع آرام، می‌تواند روز را روشن‌تر کند.", "coffee cup morning light", "روز روشن")]),
    ("تمرکز کوتاه", "بیست دقیقه تمرکز", "تمرکز کوتاه", "تمرکز کامل لازم نیست؛ یک بازهِ کوتاه کافی است.", ["تمرکز", "نظم"],
     [("آخرین بار چند دقیقه بدون گوشی کار کردی؟", "phone face down on desk", "بدون گوشی؟"),
      ("اعلان‌های پی‌درپی ذهن را تکه تکه می‌کنند.", "notification lights phone screen", "اعلان‌ها"),
      ("امروز بیست دقیقه گوشی را کنار بگذار و یک کار را تمام کن.", "timer twenty minutes desk", "بیست دقیقه"),
      ("تمرکز کوتاه و مداوم، نتیجهِ واقعی می‌سازد.", "finished notebook page pen", "نتیجه")]),
    ("امید واقعی", "امید بدون شعار", "امید واقعی", "امید شعار نیست؛ قدم بعدی کوچک و صادقانه است.", ["امید", "توکل"],
     [("وقتی خسته‌ای، امید برایت چه شکلی دارد؟", "person sitting alone dusk", "امید؟"),
      ("شعارهای بزرگ گاهی فاصله با واقعیت می‌سازند.", "foggy empty road", "شعار بزرگ"),
      ("یک کار کوچک و ممکن برای فردا انتخاب کن.", "checklist one item marked", "کار کوچک"),
      ("امید واقعی در حرکت آرام و پیوسته زنده می‌ماند.", "sunrise over quiet hills", "حرکت آرام")]),
    ("پول آگاهانه", "یک خرید آگاهانه", "خرید آگاهانه", "سواد مالی با یک سؤال ساده شروع می‌شود.", ["سواد مالی", "عادت"],
     [("قبل از خرید بعدی، چه سؤالی از خودت می‌پرسی؟", "person holding wallet store", "قبل خرید؟"),
      ("خرید عجول گاهی فقط یک احساس لحظه‌ای را پر می‌کند.", "shopping bag on chair", "خرید عجول"),
      ("بیست‌وچهار ساعت صبر کن، بعد تصمیم بگیر.", "calendar mark one day", "۲۴ ساعت"),
      ("آگاهی کوچک در خرج، آرامش بزرگ‌تری می‌آورد.", "coins saved glass jar", "آگاهی")]),
    ("نفس عمیق", "سه نفس در تنش", "سه نفس", "در لحظهِ تنش، بدن به یک توقف کوتاه نیاز دارد.", ["آرامش", "تنش"],
     [("وقتی عصبانی می‌شوی، اولین حرکتت چیست؟", "clenched fists close up", "عصبانی؟"),
      ("واکنش فوری گاهی حرفی می‌سازد که بعد پشیمان می‌شوی.", "argument shadows hallway", "واکنش فوری"),
      ("قبل از پاسخ، سه نفس عمیق بکش و بعد حرف بزن.", "person breathing slowly outdoors", "سه نفس"),
      ("این مکث ساده می‌تواند آسیب را کم کند.", "calm face soft daylight", "کمتر آسیب")]),
    ("مرز سالم", "نه گفتن محترمانه", "نه محترمانه", "مرز سالم بی‌احترامی نیست؛ مراقبت از توان و وقت است.", ["مرز", "احترام"],
     [("آخرین بار کی نه گفتی و دلت آرام ماند؟", "person politely declining handshake", "نه گفتن؟"),
      ("قبول همه چیز، گاهی خودت را خالی می‌کند.", "overloaded bag spilling items", "خالی شدن"),
      ("امروز یک درخواست غیرضروری را محترمانه رد کن.", "calm conversation soft room", "محترمانه"),
      ("مرز روشن، رابطه را سالم‌تر نگه می‌دارد.", "garden fence flowers sunlight", "مرز روشن")]),
]

MOODS = ["hook", "calm", "reassuring", "motivational"]


def word_count(text: str) -> int:
    return sum(bool(re.search(r"[\u0600-\u06FFA-Za-z0-9]", t)) for t in str(text).split())


def main() -> int:
    ideas = []
    for i, (topic, title, thumb, desc, tags, scenes_raw) in enumerate(TEMPLATES):
        scenes = []
        for (spoken, visual, overlay), mood in zip(scenes_raw, MOODS):
            scenes.append({
                "spoken_text": spoken,
                "mood": mood,
                "visual_query": visual,
                "on_screen_text": overlay,
            })
        script = " ".join(s["spoken_text"] for s in scenes)
        wc = word_count(script)
        if not 28 <= wc <= 52:
            raise SystemExit(f"word count out of range for {topic}: {wc}")
        ideas.append({
            "id": f"bank-{i+1:04d}",
            "topic": topic,
            "title": BRAND + title,
            "hook": scenes[0]["spoken_text"],
            "thumbnail_text": thumb,
            "description": desc,
            "tags": tags,
            "scenes": scenes,
            "script": script,
            "word_count": wc,
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "source": "curated-templates", "count": len(ideas), "ideas": ideas}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"BUILT {OUT} count={len(ideas)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
