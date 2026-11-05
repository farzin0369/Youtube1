"""BAMO growth loop: learn from real YouTube stats and tune the next videos.

Self-improvement here is deliberately BOUNDED and REVERSIBLE:
  * it tunes a small "recipe" (hook style, title style, voice rate, length,
    thumbnail style) and per-domain weight multipliers;
  * every change is versioned; a sustained reward drop triggers rollback;
  * it never edits code and never publishes by itself.

Pure logic lives here (testable offline). Network access is isolated in
YouTubeStats and is injected, so tests never touch the network.
"""
from __future__ import annotations

import copy
import json
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_policy() -> dict[str, Any]:
    return json.loads((ROOT / "config" / "bamo_growth_policy.json").read_text(encoding="utf-8"))


def new_state(policy: dict[str, Any]) -> dict[str, Any]:
    return {"version": 1, "videos": [], "recipes": {
        fmt: {"champion": dict(rec), "version": 1, "history": []}
        for fmt, rec in policy["defaults"].items()}, "arms": {}, "events": []}


# ---------------------------------------------------------------- metrics

def _ratio(value, base):
    if value is None or not base:
        return None
    return max(0.0, min(3.0, float(value) / float(base)))


def metric_view(video: dict[str, Any]) -> dict[str, float | None]:
    """Normalise the latest metric snapshot into comparable numbers."""
    m = (video.get("metrics") or {})
    views = m.get("views")
    age = max(1.0, float(m.get("age_hours") or 1.0))
    return {
        "ctr": m.get("ctr"),
        "retention": m.get("avg_view_pct"),
        "avg_seconds": m.get("avg_view_seconds"),
        "engagement": ((m.get("likes") or 0) + 2 * (m.get("comments") or 0)) / views if views else None,
        "velocity": (views / age) if views is not None else None,
    }


def baseline(videos: list[dict[str, Any]], fmt: str, exclude_id: str | None = None) -> dict[str, float | None]:
    rows = [metric_view(v) for v in videos if v.get("format") == fmt and v.get("scored_at")
            and v.get("video_id") != exclude_id]
    out = {}
    for key in ("ctr", "retention", "engagement", "velocity"):
        vals = [r[key] for r in rows if r[key] is not None]
        out[key] = statistics.median(vals) if vals else None
    return out


def reward(video: dict[str, Any], base: dict[str, float | None], policy: dict[str, Any]) -> float | None:
    """1.0 == channel baseline for this format. None when it cannot be judged."""
    mv = metric_view(video)
    weights = policy["reward_weights"]
    total, used = 0.0, 0.0
    for key, w in weights.items():
        r = _ratio(mv.get(key), base.get(key))
        if r is not None:
            total += w * r
            used += w
    return round(total / used, 4) if used else None


def diagnose(video: dict[str, Any], base: dict[str, float | None], policy: dict[str, Any]) -> list[dict[str, str]]:
    th = policy["diagnosis"]
    mv = metric_view(video)
    issues = []

    def add(code, directive):
        issues.append({"code": code, "directive": directive})

    ctr_r = _ratio(mv["ctr"], base.get("ctr"))
    ret_r = _ratio(mv["retention"], base.get("retention"))
    eng_r = _ratio(mv["engagement"], base.get("engagement"))
    vel_r = _ratio(mv["velocity"], base.get("velocity"))
    if ctr_r is not None and ctr_r < th["ctr_ratio"]:
        add("ctr_low", "Title/thumbnail did not earn clicks: try another title_style or thumbnail_style.")
    if mv["avg_seconds"] is not None and mv["avg_seconds"] < th["hook_fail_seconds"]:
        add("hook_failure", "Viewers left in the first seconds: try another hook_style.")
    if ret_r is not None and ret_r < th["retention_ratio"]:
        add("retention_low", "Retention below channel norm: try shorter target_seconds or a faster voice_rate.")
    if eng_r is not None and eng_r < th["engagement_ratio"]:
        add("engagement_low", "Few likes/comments: strengthen the closing question or hook.")
    packaging_ok = (ctr_r is None or ctr_r >= th["ctr_ratio"]) and (ret_r is None or ret_r >= th["retention_ratio"])
    if vel_r is not None and vel_r < th["velocity_ratio"] and packaging_ok:
        add("discovery_low", "Packaging and retention are fine but reach is low: topic/domain is under-performing.")
    return issues


# ---------------------------------------------------------------- recipes

def _event(state, kind, **data):
    state["events"].append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kind": kind, **data})
    del state["events"][:-200]


def scored_count(state: dict[str, Any], fmt: str) -> int:
    return sum(1 for v in state["videos"] if v.get("format") == fmt and v.get("reward") is not None)


def choose_recipe(state: dict[str, Any], fmt: str, policy: dict[str, Any],
                  rng: random.Random | None = None) -> dict[str, Any]:
    """Recipe for the next video: the champion, plus one explored dimension."""
    rng = rng or random.Random()
    champ = dict(state["recipes"][fmt]["champion"])
    cold = scored_count(state, fmt) < policy["min_scored_for_baseline"]
    explore = cold or rng.random() < policy["explore_rate"]
    recipe = dict(champ)
    experiment = None
    if explore:
        dims = policy["dimensions"]
        open_codes = [c for c in recent_issue_codes(state, fmt)]
        focus = []
        for code in open_codes:
            focus += policy["issue_dimension"].get(code, [])
        dim = rng.choice(focus) if focus and not cold else rng.choice(sorted(dims))
        table = state["arms"].get(fmt, {}).get(dim, {})
        options = [o for o in dims[dim] if o != champ.get(dim)]
        fewest = min((table.get(str(o), {}).get("n", 0) for o in options), default=0)
        options = [o for o in options if table.get(str(o), {}).get("n", 0) == fewest]  # least-tried first
        if cold:  # bootstrap a baseline with varied recipes
            for d in dims:
                recipe[d] = rng.choice(dims[d])
        else:
            recipe[dim] = rng.choice(options)
        experiment = {"dimension": "*" if cold else dim, "value": None if cold else recipe[dim]}
    return {"format": fmt, "recipe": recipe, "experiment": experiment,
            "recipe_version": state["recipes"][fmt]["version"]}


def recent_issue_codes(state: dict[str, Any], fmt: str, last: int = 8) -> list[str]:
    rows = [v for v in state["videos"] if v.get("format") == fmt and v.get("diagnosis")][-last:]
    counts: dict[str, int] = {}
    for v in rows:
        for issue in v["diagnosis"]:
            counts[issue["code"]] = counts.get(issue["code"], 0) + 1
    return [c for c, n in sorted(counts.items(), key=lambda kv: -kv[1]) if n >= 2]


def _update_arms(state, video, rew):
    arms = state["arms"].setdefault(video["format"], {})
    for dim, value in (video.get("recipe") or {}).items():
        slot = arms.setdefault(dim, {}).setdefault(str(value), {"n": 0, "sum": 0.0})
        slot["n"] += 1
        slot["sum"] += rew


def _maybe_promote(state, fmt, policy):
    rec = state["recipes"][fmt]
    arms = state["arms"].get(fmt, {})
    changed = {}
    for dim, table in arms.items():
        cur = str(rec["champion"].get(dim))
        cur_mean = (table[cur]["sum"] / table[cur]["n"]) if cur in table and table[cur]["n"] else None
        best_val, best_mean = None, None
        for val, s in table.items():
            if s["n"] >= policy["promote_min_samples"]:
                mean = s["sum"] / s["n"]
                if best_mean is None or mean > best_mean:
                    best_val, best_mean = val, mean
        if best_val is None or best_val == cur:
            continue
        if cur_mean is None or best_mean >= cur_mean * policy["promote_margin"]:
            options = policy["dimensions"][dim]
            typed = next((o for o in options if str(o) == best_val), best_val)
            changed[dim] = (rec["champion"].get(dim), typed)
    if changed:
        rec["history"].append({"version": rec["version"], "champion": dict(rec["champion"]),
                               "scored_at_promotion": scored_count(state, fmt)})
        del rec["history"][:-20]
        for dim, (_, new) in changed.items():
            rec["champion"][dim] = new
        rec["version"] += 1
        _event(state, "promote", format=fmt, changes={d: list(v) for d, v in changed.items()}, version=rec["version"])
    return changed


def _maybe_rollback(state, fmt, policy):
    rec = state["recipes"][fmt]
    if not rec["history"]:
        return False
    rewards = [v["reward"] for v in state["videos"] if v.get("format") == fmt and v.get("reward") is not None]
    w = policy["rollback_window"]
    last_promo = rec["history"][-1]["scored_at_promotion"]
    after = rewards[last_promo:]
    before = rewards[max(0, last_promo - w):last_promo]
    if len(after) < w or len(before) < w:
        return False
    if statistics.mean(after[-w:]) < statistics.mean(before) * (1 - policy["rollback_drop"]):
        prev = rec["history"].pop()
        _event(state, "rollback", format=fmt, restored=prev["champion"], from_version=rec["version"])
        rec["champion"] = dict(prev["champion"])
        rec["version"] += 1
        # forget arm statistics that justified the bad promotion
        state["arms"][fmt] = {}
        return True
    return False


# ---------------------------------------------------------------- domains

def domain_multipliers(state: dict[str, Any], policy: dict[str, Any], domains: list[str]) -> dict[str, float]:
    lo, hi = policy["weight_multiplier_bounds"]
    rows = [v for v in state["videos"] if v.get("reward") is not None and v.get("domain")]
    if not rows:
        return {d: 1.0 for d in domains}
    overall = statistics.mean(v["reward"] for v in rows)
    out = {}
    for d in domains:
        vals = [v["reward"] for v in rows if v["domain"] == d][-10:]
        if len(vals) < policy["domain_min_samples"] or not overall:
            out[d] = 1.0
        else:
            ratio = statistics.mean(vals) / overall
            out[d] = round(max(lo, min(hi, 1.0 + 0.5 * (ratio - 1.0))), 3)
    return out


def apply_weight_multipliers(domains_cfg: dict[str, Any], mult: dict[str, float]) -> dict[str, Any]:
    """Return a copy of the domain config with renormalised weights (sum 100)."""
    cfg = copy.deepcopy(domains_cfg)
    raw = {k: d["weight"] * mult.get(k, 1.0) for k, d in cfg["domains"].items()}
    total = sum(raw.values()) or 1.0
    for k, d in cfg["domains"].items():
        d["weight"] = round(100.0 * raw[k] / total, 3)
    return cfg


# ---------------------------------------------------------------- state ops

def record_publication(state: dict[str, Any], *, video_id: str, fmt: str, domain: str, topic: str,
                       recipe: dict[str, Any], experiment: dict[str, Any] | None,
                       published_at: str) -> None:
    if any(v["video_id"] == video_id for v in state["videos"]):
        return
    state["videos"].append({"video_id": video_id, "format": fmt, "domain": domain, "topic": topic,
                            "recipe": recipe, "experiment": experiment, "published_at": published_at,
                            "metrics": {}, "reward": None, "scored_at": None, "diagnosis": []})


def ingest_metrics(state: dict[str, Any], video_id: str, metrics: dict[str, Any]) -> None:
    for v in state["videos"]:
        if v["video_id"] == video_id:
            v["metrics"] = {**v.get("metrics", {}), **{k: x for k, x in metrics.items() if x is not None}}


def run_cycle(state: dict[str, Any], policy: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Score newly mature videos, diagnose, promote winners, roll back regressions."""
    now = now or datetime.now(timezone.utc)
    report = {"scored": [], "promoted": {}, "rolled_back": [], "diagnoses": {}}
    for v in state["videos"]:
        if v.get("scored_at"):
            continue
        age = (now - datetime.fromisoformat(v["published_at"])).total_seconds() / 3600
        if age < policy["maturity_hours"] or not v.get("metrics"):
            continue
        v["metrics"]["age_hours"] = age
        base = baseline(state["videos"], v["format"], exclude_id=v["video_id"])
        rew = reward(v, base, policy)
        v["diagnosis"] = diagnose(v, base, policy) if any(x is not None for x in base.values()) else []
        v["scored_at"] = now.isoformat(timespec="seconds")
        if rew is None:
            # first videos have no baseline: keep them as baseline material
            v["reward"] = 1.0
        else:
            v["reward"] = rew
            _update_arms(state, v, rew)
        report["scored"].append(v["video_id"])
        report["diagnoses"][v["video_id"]] = [i["code"] for i in v["diagnosis"]]
    for fmt in state["recipes"]:
        if _maybe_rollback(state, fmt, policy):
            report["rolled_back"].append(fmt)
        elif scored_count(state, fmt) >= policy.get("promote_min_scored", policy["min_scored_for_baseline"]):
            changed = _maybe_promote(state, fmt, policy)
            if changed:
                report["promoted"][fmt] = {d: list(c) for d, c in changed.items()}
    return report


# ---------------------------------------------------------------- YouTube API

class YouTubeStats:
    """Thin client for YouTube Data + Analytics APIs. `http` is injectable for tests.

    Needs OAuth scopes youtube.readonly (or youtube) for views/likes/comments and
    yt-analytics.readonly for retention/CTR. Without the analytics scope the loop
    still works from views/likes/comments (velocity + engagement only).
    """
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    DATA_URL = "https://www.googleapis.com/youtube/v3/videos"
    ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"

    def __init__(self, client_id, client_secret, refresh_token, http=None):
        import requests
        self.http = http or requests
        self.creds = (client_id, client_secret, refresh_token)
        self.token = None

    def _auth(self):
        if self.token is None:
            cid, secret, refresh = self.creds
            r = self.http.post(self.TOKEN_URL, data={"client_id": cid, "client_secret": secret,
                                                     "refresh_token": refresh, "grant_type": "refresh_token"}, timeout=30)
            r.raise_for_status()
            self.token = r.json()["access_token"]
        return {"Authorization": f"Bearer {self.token}"}

    def data_stats(self, video_ids: list[str]) -> dict[str, dict[str, Any]]:
        out = {}
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i + 50]
            r = self.http.get(self.DATA_URL, headers=self._auth(), timeout=30,
                              params={"part": "statistics", "id": ",".join(chunk)})
            r.raise_for_status()
            for item in r.json().get("items", []):
                s = item.get("statistics", {})
                out[item["id"]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                                   "comments": int(s.get("commentCount", 0))}
        return out

    def analytics(self, video_id: str, start: str, end: str) -> dict[str, Any]:
        base = {"ids": "channel==MINE", "startDate": start, "endDate": end,
                "filters": f"video=={video_id}"}
        attempts = [
            "views,averageViewDuration,averageViewPercentage,videoThumbnailImpressions,videoThumbnailImpressionsClickRate",
            "views,averageViewDuration,averageViewPercentage",
        ]
        for metrics in attempts:
            r = self.http.get(self.ANALYTICS_URL, headers=self._auth(), timeout=30, params={**base, "metrics": metrics})
            if getattr(r, "status_code", 200) >= 400:
                continue
            data = r.json()
            names = [h["name"] for h in data.get("columnHeaders", [])]
            rows = data.get("rows") or []
            if not rows:
                return {}
            row = dict(zip(names, rows[0]))
            ctr = row.get("videoThumbnailImpressionsClickRate")
            return {"avg_view_seconds": row.get("averageViewDuration"),
                    "avg_view_pct": row.get("averageViewPercentage"),
                    "ctr": (ctr * 100.0 if ctr is not None and ctr <= 1 else ctr)}
        return {}


def collect(state: dict[str, Any], stats: YouTubeStats, now: datetime | None = None) -> int:
    """Pull fresh stats for every unscored video. Returns number of videos updated."""
    now = now or datetime.now(timezone.utc)
    pending = [v for v in state["videos"] if not v.get("scored_at")]
    if not pending:
        return 0
    data = stats.data_stats([v["video_id"] for v in pending])
    n = 0
    for v in pending:
        d = data.get(v["video_id"])
        if not d:
            continue
        pub = datetime.fromisoformat(v["published_at"])
        extra = {}
        try:
            extra = stats.analytics(v["video_id"], pub.date().isoformat(), now.date().isoformat())
        except Exception:  # analytics scope missing is not fatal
            extra = {}
        ingest_metrics(state, v["video_id"], {**d, **extra,
                                              "age_hours": (now - pub).total_seconds() / 3600})
        n += 1
    return n


def save_state(state: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_state(path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return new_state(policy)
