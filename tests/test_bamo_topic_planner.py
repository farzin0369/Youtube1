from collections import Counter
from datetime import date, timedelta
from app.bamo_topic_planner import load_json, plan_day, is_similar, infer_domain


def test_weights_sum_to_100():
    cfg = load_json("bamo_domains.json")
    assert sum(d["weight"] for d in cfg["domains"].values()) == 100
    assert len(cfg["domains"]) == 8


def test_schedule_has_six_tehran_slots():
    s = load_json("bamo_schedule.json")
    assert [x["tehran"] for x in s["slots"]] == ["07:00", "10:00", "12:00", "15:00", "18:00", "21:00"]


def test_day_is_diverse_and_unique():
    plan = plan_day(date(2026, 11, 6), [])
    topics = [s["topic"] for s in plan["slots"]]
    assert all(s["status"] == "planned" for s in plan["slots"])
    assert len(set(topics)) == 6
    assert plan["diversity_ok"]


def test_no_adjacent_same_domain():
    plan = plan_day(date(2026, 11, 6), [])
    doms = [s["domain"] for s in plan["slots"]]
    assert all(a != b for a, b in zip(doms, doms[1:]))


def test_no_repeat_against_history():
    first = plan_day(date(2026, 11, 6), [])
    hist = [{"topic": s["topic"], "domain": s["domain"]} for s in first["slots"]]
    second = plan_day(date(2026, 11, 7), hist)
    old = {s["topic"] for s in first["slots"]}
    assert all(s["topic"] not in old for s in second["slots"] if s["topic"])


def test_long_run_is_balanced_and_priority_ordered():
    hist, counts = [], Counter()
    for i in range(7):
        plan = plan_day(date(2026, 11, 6) + timedelta(days=i), hist,
                        source=lambda d, c, a, n=[0]: [f"{d} موضوع منحصر {i} {j} {'x'*j}{chr(1600+j+i*7)}" for j in range(8)])
        for s in plan["slots"]:
            if s["topic"]:
                hist.append({"topic": s["topic"], "domain": s["domain"]})
                counts[s["domain"]] += 1
    assert set(counts) == set(load_json("bamo_domains.json")["domains"])
    assert max(counts.values()) / sum(counts.values()) <= 0.30
    assert counts["religious"] >= counts["chemistry"]


def test_similarity_and_inference():
    sim = load_json("bamo_domains.json")["similarity"]
    assert is_similar("چرا آسمان شب تاریک است", "چرا آسمان شب تاریک است؟", sim)
    assert not is_similar("چرا آهن زنگ می‌زند", "معمای پل‌های کونیگسبرگ", sim)
    assert infer_domain("آیه قرآن و تفسیر", load_json("bamo_domains.json")["domains"]) == "religious"
