import random
from datetime import datetime, timedelta, timezone

from app import bamo_growth_loop as g
from app.bamo_topic_planner import load_json, plan_day

NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)


def _sim(policy, n, quality, seed=1, state=None, start=0):
    """Simulate n videos. quality(recipe, domain) -> multiplier on baseline metrics."""
    rng = random.Random(seed)
    state = state or g.new_state(policy)
    doms = list(load_json("bamo_domains.json")["domains"])
    for i in range(start, start + n):
        pick = g.choose_recipe(state, "short", policy, rng)
        dom = doms[i % len(doms)]
        q = quality(pick["recipe"], dom)
        pub = NOW - timedelta(hours=200 - i)
        g.record_publication(state, video_id=f"v{i}", fmt="short", domain=dom, topic=f"t{i}",
                             recipe=pick["recipe"], experiment=pick["experiment"], published_at=pub.isoformat())
        g.ingest_metrics(state, f"v{i}", {"views": 1000 * q, "likes": 50 * q, "comments": 5 * q,
                                          "ctr": 5 * q, "avg_view_pct": 50 * q, "avg_view_seconds": 18 * q,
                                          "age_hours": 100})
        g.run_cycle(state, policy, NOW)
    return state


def test_cold_start_scores_without_baseline_then_scores_relative():
    policy = g.load_policy()
    state = _sim(policy, 8, lambda r, d: 1.0)
    assert all(v["scored_at"] for v in state["videos"])
    assert all(0.9 <= v["reward"] <= 1.1 for v in state["videos"][policy["min_scored_for_baseline"]:])


def test_loop_learns_better_hook_and_title():
    policy = g.load_policy()
    q = lambda r, d: (1.6 if r["hook_style"] == "counterintuitive" else 0.8) * (1.3 if r["title_style"] == "number" else 1.0)
    for seed in (1, 3):
        state = _sim(policy, 150, q, seed=seed)
        champ = state["recipes"]["short"]["champion"]
        assert champ["hook_style"] == "counterintuitive"
        assert champ["title_style"] == "number"
        assert state["recipes"]["short"]["version"] > 1


def test_diagnosis_flags_real_problems():
    policy = g.load_policy()
    base = {"ctr": 5.0, "retention": 50.0, "engagement": 0.06, "velocity": 10.0}
    weak = {"metrics": {"views": 100, "likes": 0, "comments": 0, "ctr": 1.0, "avg_view_pct": 15.0,
                        "avg_view_seconds": 1.5, "age_hours": 50}}
    codes = {i["code"] for i in g.diagnose(weak, base, policy)}
    assert {"ctr_low", "hook_failure", "retention_low", "engagement_low"} <= codes
    reach = {"metrics": {"views": 50, "likes": 5, "comments": 1, "ctr": 5.0, "avg_view_pct": 50.0,
                         "avg_view_seconds": 18, "age_hours": 50}}
    assert {i["code"] for i in g.diagnose(reach, base, policy)} == {"discovery_low"}


def test_rollback_after_regression():
    policy = g.load_policy()
    state = _sim(policy, 40, lambda r, d: 1.0, seed=5)
    rec = state["recipes"]["short"]
    rec["history"].append({"version": 1, "champion": dict(rec["champion"]), "scored_at_promotion": 30})
    rec["champion"]["hook_style"] = "stat"
    rec["version"] += 1
    for v in state["videos"][30:]:  # everything after the promotion got much worse
        v["reward"] = 0.4
    previous = dict(rec["history"][-1]["champion"])
    rolled = g._maybe_rollback(state, "short", policy)
    assert rolled is True
    assert rec["champion"] == previous and rec["champion"]["hook_style"] != "stat"
    assert any(e["kind"] == "rollback" for e in state["events"])


def test_domain_multipliers_bounded_and_planner_still_balanced():
    policy = g.load_policy()
    domains = load_json("bamo_domains.json")
    names = list(domains["domains"])
    state = g.new_state(policy)
    for i in range(60):
        d = names[i % 8]
        state["videos"].append({"video_id": f"x{i}", "format": "short", "domain": d,
                                "reward": 2.5 if d == "chemistry" else (0.2 if d == "religious" else 1.0),
                                "scored_at": "x"})
    mult = g.domain_multipliers(state, policy, names)
    lo, hi = policy["weight_multiplier_bounds"]
    assert all(lo <= m <= hi for m in mult.values())
    assert mult["chemistry"] > 1.0 > mult["religious"]
    cfg = g.apply_weight_multipliers(domains, mult)
    assert abs(sum(d["weight"] for d in cfg["domains"].values()) - 100) < 0.01
    # no pillar is ever starved: weight stays above 40% of its base
    assert all(cfg["domains"][k]["weight"] > 0.4 * domains["domains"][k]["weight"] for k in names)
    from datetime import date
    plan = plan_day(date(2026, 11, 21), [], domains_cfg=cfg)
    assert plan["diversity_ok"]


class _Resp:
    def __init__(self, payload, status=200):
        self._p, self.status_code = payload, status
    def json(self): return self._p
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(self.status_code)


class _Http:
    def __init__(self): self.calls = []
    def post(self, url, **kw): self.calls.append(("post", url)); return _Resp({"access_token": "tok"})
    def get(self, url, **kw):
        self.calls.append(("get", url, kw.get("params", {}).get("metrics")))
        if "youtubeanalytics" in url:
            m = kw["params"]["metrics"]
            if "Impressions" in m:  # simulate API rejecting thumbnail metrics
                return _Resp({}, 400)
            return _Resp({"columnHeaders": [{"name": "views"}, {"name": "averageViewDuration"}, {"name": "averageViewPercentage"}],
                          "rows": [[900, 17.5, 48.0]]})
        return _Resp({"items": [{"id": "a1", "statistics": {"viewCount": "900", "likeCount": "40", "commentCount": "6"}}]})


def test_stats_client_falls_back_without_thumbnail_metrics():
    http = _Http()
    client = g.YouTubeStats("id", "secret", "refresh", http=http)
    state = g.new_state(g.load_policy())
    g.record_publication(state, video_id="a1", fmt="short", domain="math", topic="t",
                         recipe={}, experiment=None, published_at=(NOW - timedelta(hours=60)).isoformat())
    assert g.collect(state, client, NOW) == 1
    m = state["videos"][0]["metrics"]
    assert m["views"] == 900 and m["avg_view_pct"] == 48.0 and "ctr" not in m
    assert sum(1 for c in http.calls if c[0] == "get" and "youtubeanalytics" in c[1]) == 2
