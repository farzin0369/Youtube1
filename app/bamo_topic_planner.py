"""Balanced, non-repeating daily topic planner for BAMO.

Pure-Python and offline-capable. It decides WHICH domain and topic each publish
slot gets; it never publishes and never calls a paid service. Candidate topics
come from an injectable source (e.g. an LLM) with a seed-bank fallback.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable

from app.youtube_history import normalize_text, topic_tokens

ROOT = Path(__file__).resolve().parents[1]
TopicSource = Callable[[str, dict[str, Any], list[str]], list[str]]


def load_json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def infer_domain(text: str, domains: dict[str, Any]) -> str | None:
    """Keyword fallback for history rows that carry no stored domain."""
    norm = normalize_text(text)
    best, best_hits = None, 0
    for key, cfg in sorted(domains.items(), key=lambda kv: kv[1]["priority"]):
        hits = sum(1 for word in cfg.get("keywords", []) if normalize_text(word) in norm)
        if hits > best_hits:
            best, best_hits = key, hits
    return best


def is_similar(a: str, b: str, sim: dict[str, float]) -> bool:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return False
    if na == nb or SequenceMatcher(None, na, nb).ratio() >= sim["sequence_ratio"]:
        return True
    ta, tb = topic_tokens(na), topic_tokens(nb)
    return bool(ta and tb) and len(ta & tb) / len(ta | tb) >= sim["token_overlap"]


def history_domains(history: list[dict[str, Any]], domains: dict[str, Any]) -> list[str | None]:
    result = []
    for row in history:
        dom = row.get("domain")
        if dom not in domains:
            dom = infer_domain(f"{row.get('topic') or ''} {row.get('title') or ''}", domains)
        result.append(dom)
    return result


def choose_domain(recent: list[str | None], today: list[str], cfg: dict[str, Any],
                  rng: random.Random) -> str:
    """Pick the domain with the largest deficit against its target share."""
    domains, bal = cfg["domains"], cfg["balance"]
    window = [d for d in (recent + today)[-bal["window"]:] if d]
    counts, total = Counter(window), max(1, len(window))
    last = [d for d in (recent + today)[-bal["no_repeat_last_n_domains"]:] if d]
    scores = {}
    for key, dom in domains.items():
        share = 100.0 * counts[key] / total
        if share >= bal["max_share_percent"] or key in last:
            continue
        scores[key] = dom["weight"] - share + rng.random() * 0.01
    if not scores:  # all blocked: relax only the recency rule
        scores = {k: d["weight"] - 100.0 * counts[k] / total for k, d in domains.items()}
    return max(scores, key=scores.get)


def bank_source(domain: str, domain_cfg: dict[str, Any], avoid: list[str]) -> list[str]:
    return list(load_json("bamo_topic_bank.json")["topics"].get(domain, []))


def pick_topic(domain: str, cfg: dict[str, Any], history_topics: list[str],
               taken_today: list[str], source: TopicSource, rng: random.Random) -> str | None:
    candidates = source(domain, cfg["domains"][domain], history_topics[-60:])
    rng.shuffle(candidates)
    seen = history_topics + taken_today
    for cand in candidates:
        if not any(is_similar(cand, old, cfg["similarity"]) for old in seen):
            return cand
    return None


def plan_day(day: date, history: list[dict[str, Any]], *, source: TopicSource = bank_source,
             domains_cfg: dict[str, Any] | None = None,
             schedule_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = domains_cfg or load_json("bamo_domains.json")
    sched = schedule_cfg or load_json("bamo_schedule.json")
    rng = random.Random(day.toordinal())
    recent = history_domains(history, cfg["domains"])
    history_topics = [str(r.get("topic") or r.get("title") or "") for r in history]
    today_domains: list[str] = []
    today_topics: list[str] = []
    slots = []
    for slot in sched["slots"]:
        tried: set[str] = set()
        while True:
            domain = choose_domain(recent, today_domains, cfg, rng)
            if domain in tried:  # avoid infinite loop when every domain is exhausted
                domain = next((d for d in cfg["domains"] if d not in tried), None)
                if domain is None:
                    topic, domain = None, None
                    break
            topic = pick_topic(domain, cfg, history_topics, today_topics, source, rng)
            if topic:
                break
            tried.add(domain)
            if len(tried) == len(cfg["domains"]):
                topic, domain = None, None
                break
        if topic is None:
            slots.append({**slot, "status": "NO_UNIQUE_TOPIC", "domain": None, "topic": None})
            continue
        today_domains.append(domain)
        today_topics.append(topic)
        dcfg = cfg["domains"][domain]
        slots.append({**slot, "status": "planned", "domain": domain, "topic": topic,
                      "narrative": dcfg["narrative"], "visual_grammar": dcfg["visual_grammar"],
                      "verification": dcfg["verification"]})
    distinct = len(set(today_domains))
    need = cfg["balance"]["min_distinct_domains_per_day"]
    return {"date": day.isoformat(), "timezone": sched["timezone"], "slots": slots,
            "distinct_domains": distinct, "diversity_ok": distinct >= need}
