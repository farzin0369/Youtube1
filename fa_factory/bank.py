#!/usr/bin/env python3
"""Persian idea bank: validation, near-duplicate detection, non-repeating selection.

The bank file is append-only JSONL (data/fa/ideas_fa.jsonl). Usage is tracked
separately in data/fa/history.jsonl so the big file is never rewritten.
"""
from __future__ import annotations

import json
import random
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data" / "fa" / "ideas_fa.jsonl"
HISTORY = ROOT / "data" / "fa" / "history.jsonl"

_ZWNJ = "\u200c"
_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_DIGITS = re.compile(r"[0-9\u06F0-\u06F9\u0660-\u0669]")
_LATIN = re.compile(r"[A-Za-z]")
STOP = set("و در به از که این آن را با برای است یا هم تا یک می همه بر خود را؟ نیز اما اگر چه چرا".split())


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = t.replace("ي", "ی").replace("ك", "ک").replace(_ZWNJ, " ")
    t = _DIACRITICS.sub("", t)
    t = _PUNCT.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def tokens(text: str) -> set[str]:
    return {w for w in normalize(text).split() if w not in STOP and len(w) > 1}


def idea_fingerprint(idea: dict[str, Any]) -> set[str]:
    return tokens(idea.get("title", "")) | tokens(" ".join(idea.get("sentences", [])[:3]))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def validate(idea: dict[str, Any]) -> list[str]:
    """Return a list of problems; empty list = publishable."""
    errs: list[str] = []
    for k in ("id", "category", "visual", "title", "sentences"):
        if not idea.get(k):
            errs.append(f"missing:{k}")
    sents = idea.get("sentences") or []
    if not (4 <= len(sents) <= 9):
        errs.append("sentence_count_4_to_9")
    for i, s in enumerate(sents):
        if _DIGITS.search(s):
            errs.append(f"digit_in_spoken_text:{i} (write numbers as words for TTS)")
        if _LATIN.search(s):
            errs.append(f"latin_in_spoken_text:{i}")
        if len(s.split()) > 16:
            errs.append(f"sentence_too_long:{i}")
    if len(idea.get("title", "")) > 90:
        errs.append("title_over_90")
    return errs


def load(path: Path = BANK) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


class DedupIndex:
    """Token inverted index so 10k+ ideas can be checked quickly."""

    def __init__(self, ideas: Iterable[dict[str, Any]] = ()):
        self.fps: dict[str, set[str]] = {}
        self.inv: dict[str, set[str]] = defaultdict(set)
        for i in ideas:
            self.add(i)

    def add(self, idea: dict[str, Any]) -> None:
        fp = idea_fingerprint(idea)
        self.fps[idea["id"]] = fp
        for t in fp:
            self.inv[t].add(idea["id"])

    def nearest(self, idea: dict[str, Any]) -> tuple[float, str | None]:
        fp = idea_fingerprint(idea)
        cands: dict[str, int] = defaultdict(int)
        for t in fp:
            for cid in self.inv.get(t, ()):
                cands[cid] += 1
        best, best_id = 0.0, None
        for cid in cands:
            j = jaccard(fp, self.fps[cid])
            if j > best:
                best, best_id = j, cid
        return best, best_id

    def is_duplicate(self, idea: dict[str, Any], threshold: float = 0.55) -> bool:
        score, _ = self.nearest(idea)
        return score >= threshold


def used_ids() -> set[str]:
    return {r.get("idea_id") for r in load(HISTORY) if r.get("idea_id") and r.get("ok", True)}


def recent_categories(n: int = 6) -> list[str]:
    return [r.get("category", "") for r in load(HISTORY)][-n:]


def select_idea(*, prefer_category: str | None = None, seed: int | None = None) -> dict[str, Any]:
    """Pick one never-used, valid idea; rotate categories; prefer high virality."""
    rnd = random.Random(seed)
    ideas = load()
    used = used_ids()
    pool = [i for i in ideas if i["id"] not in used and i.get("status", "available") == "available" and not validate(i)]
    if not pool:
        raise RuntimeError("No unused valid Persian idea left. Run fa_factory/expand_bank.py")
    if prefer_category:
        sub = [i for i in pool if prefer_category in i.get("category", "")]
        pool = sub or pool
    recent = set(recent_categories())
    fresh = [i for i in pool if i.get("category") not in recent]
    pool = fresh or pool
    pool.sort(key=lambda x: float(x.get("virality_score", 0)), reverse=True)
    return rnd.choice(pool[: max(8, min(40, len(pool)))])


def record_use(idea: dict[str, Any], **extra: Any) -> None:
    from datetime import datetime, timezone

    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "idea_id": idea["id"], "category": idea.get("category"), **extra}
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def stats() -> dict[str, Any]:
    ideas = load()
    ok = [i for i in ideas if not validate(i)]
    cats: dict[str, int] = defaultdict(int)
    for i in ok:
        cats[i["category"]] += 1
    return {"total": len(ideas), "valid": len(ok), "used": len(used_ids()), "by_category": dict(cats)}


if __name__ == "__main__":
    print(json.dumps(stats(), ensure_ascii=False, indent=2))
