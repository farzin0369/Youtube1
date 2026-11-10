#!/usr/bin/env python3
"""Grow the Persian bank toward 10,000 DISTINCT ideas using a free LLM (OpenRouter).

Pipeline per batch:  generate -> structural validation -> near-duplicate check
-> independent fact-check pass by a second model -> append only if it passes.
Nothing unverified is ever marked available. Safe to run daily; each run appends.

  OPENROUTER_API_KEY=... python fa_factory/expand_bank.py --target 10000 --batches 6
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fa_factory import bank  # noqa: E402

API = "https://openrouter.ai/api/v1/chat/completions"
GEN_MODELS = ["meta-llama/llama-3.3-70b-instruct:free", "qwen/qwen-2.5-72b-instruct:free", "deepseek/deepseek-chat-v3-0324:free"]
CHK_MODELS = ["deepseek/deepseek-chat-v3-0324:free", "meta-llama/llama-3.3-70b-instruct:free", "qwen/qwen-2.5-72b-instruct:free"]

TOPICS = {  # category -> (visual, subtopics to rotate so batches differ)
    "فضا و نجوم": ("cosmos", ["سیاره‌ها", "ستاره‌ها", "سیاه‌چاله", "کهکشان‌ها", "ماه‌ها", "اخترفیزیک", "سفرهای فضایی", "تلسکوپ‌ها"]),
    "فیزیک": ("waves", ["نور", "صدا", "گرانش", "الکتریسیته", "ترمودینامیک", "کوانتوم", "نسبیت", "مکانیک"]),
    "شیمی و زیست": ("molecule", ["عناصر", "مولکول‌ها", "سلول", "ژنتیک", "واکنش‌های شیمیایی", "بدن انسان", "میکروب‌ها"]),
    "طبیعت و جانوران": ("nature", ["پستانداران", "پرندگان", "اقیانوس", "حشرات", "گیاهان", "اکوسیستم", "ناپدیدشدن گونه‌ها"]),
    "ریاضیات": ("geometry", ["عددها", "هندسه", "احتمال", "پارادوکس‌ها", "بی‌نهایت", "ریاضیدانان ایرانی", "الگوها"]),
    "تاریخ و تمدن": ("gears", ["ایران باستان", "اختراع‌ها", "دانشمندان ایرانی و اسلامی", "مصر و بین‌النهرین", "فناوری باستان", "جاده ابریشم"]),
    "روان‌شناسی و مغز": ("neural", ["حافظه", "توجه", "خواب", "تصمیم‌گیری", "توهم‌های ادراکی", "عادت‌ها"]),
    "فناوری و هوش مصنوعی": ("neural", ["هوش مصنوعی", "اینترنت", "رایانه‌ها", "رباتیک", "انرژی پاک", "ریزتراشه‌ها"]),
    "زمین‌شناسی و آب‌وهوا": ("nature", ["زلزله و آتشفشان", "اقلیم", "اقیانوس‌ها", "کوه‌ها", "غارها", "جو زمین"]),
    "پزشکی و سلامت علمی": ("molecule", ["تاریخ پزشکی", "ایمنی‌شناسی", "قلب و گردش خون", "مغز و اعصاب", "کشف دارو"]),
}

GEN_PROMPT = """تو نویسندهٔ حرفه‌ای شورت‌های علمی فارسی هستی. {n} ایدهٔ کاملاً متفاوت و واقعی دربارهٔ «{sub}» در حوزهٔ «{cat}» بنویس.
قوانین سخت:
- فقط حقیقت‌های مستند و شناخته‌شده؛ اگر مطمئن نیستی ننویس.
- هر ایده: عنوان جذاب (حداکثر ۹۰ نویسه) و ۵ تا ۶ جملهٔ کوتاه (هر جمله حداکثر ۱۲ کلمه)، جملهٔ اول قلاب شگفتی، جملهٔ آخر نتیجه.
- هیچ رقم یا حرف لاتین ننویس؛ همهٔ عددها را با حروف فارسی بنویس (مثلاً «دویست و چهل و سه»). نام‌های لاتین را فارسی بنویس.
- از موضوع‌ها و عنوان‌های این فهرست دوری کن: {avoid}
- فارسی روان و گفتاری، بدون اعراب.
خروجی فقط JSON معتبر: [{{"title":"...","sentences":["..."],"keywords":["..."],"claim":"یک جمله: ادعای علمی اصلی","source":"نام منبع معتبر (کتاب/نهاد/مقاله)"}}]"""

CHK_PROMPT = """به‌عنوان بررسی‌کنندهٔ دقیق واقعیت‌ها، متن زیر را بخوان. فقط اگر ادعای اصلی و همهٔ جمله‌ها از نظر علمی/تاریخی درست و بدون اغراق هستند، «PASS» بنویس؛ در غیر این صورت «FAIL: دلیل کوتاه».
عنوان: {title}
جمله‌ها: {sents}
ادعای اصلی: {claim}"""


def chat(prompt: str, models: list[str], key: str, temperature: float = 0.8) -> str:
    last = None
    for m in models:
        body = json.dumps({"model": m, "temperature": temperature, "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(API, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except Exception as exc:
            last = exc
    raise RuntimeError(f"all models failed: {last}")


def parse_json_list(text: str) -> list[dict]:
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
        return [d for d in data if isinstance(d, dict)]
    except json.JSONDecodeError:
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=10000)
    ap.add_argument("--batches", type=int, default=6, help="LLM batches this run")
    ap.add_argument("--per-batch", type=int, default=10)
    args = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        print("OPENROUTER_API_KEY not set; nothing added")
        return 0

    ideas = bank.load()
    idx = bank.DedupIndex(ideas)
    n = len(ideas)
    cats = list(TOPICS)
    added = rejected = 0
    for b in range(args.batches):
        if n >= args.target:
            break
        cat = cats[(n + b) % len(cats)]
        visual, subs = TOPICS[cat]
        sub = subs[(n // len(cats) + b) % len(subs)]
        avoid = "؛ ".join(i["title"] for i in ideas[-60:] if i["category"] == cat)[:900]
        try:
            raw = chat(GEN_PROMPT.format(n=args.per_batch, sub=sub, cat=cat, avoid=avoid or "—"), GEN_MODELS, key)
        except Exception as exc:
            print("generate failed:", exc)
            continue
        for d in parse_json_list(raw):
            n_try = n + added + 1
            idea = {"id": f"fa-{n_try:05d}", "category": cat, "visual": visual, "title": str(d.get("title", "")).strip(),
                    "sentences": [str(s).strip() for s in d.get("sentences", [])], "keywords": [str(k) for k in d.get("keywords", [])][:6],
                    "virality_score": 7.5, "source": str(d.get("source", ""))[:120], "claim": str(d.get("claim", ""))[:300]}
            if bank.validate(idea) or idx.is_duplicate(idea):
                rejected += 1
                continue
            try:
                verdict = chat(CHK_PROMPT.format(title=idea["title"], sents=" ".join(idea["sentences"]), claim=idea["claim"]), CHK_MODELS, key, 0.0)
            except Exception:
                rejected += 1
                continue
            if not verdict.strip().upper().startswith("PASS"):
                rejected += 1
                continue
            idea.update({"verified": True, "status": "available"})
            idx.add(idea)
            ideas.append(idea)
            with bank.BANK.open("a", encoding="utf-8") as f:
                f.write(json.dumps(idea, ensure_ascii=False) + "\n")
            added += 1
        print(f"batch {b + 1}: cat={cat} sub={sub} added={added} rejected={rejected}", flush=True)
    print(json.dumps({"added": added, "rejected": rejected, **bank.stats()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
