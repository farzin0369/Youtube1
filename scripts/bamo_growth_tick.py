#!/usr/bin/env python3
"""Daily growth tick: fetch real stats, score mature videos, diagnose, tune the recipe.

Reads/writes state/bamo_growth_state.json (versioned recipe, arms, events). Writes
state/bamo_growth_report.json and state/bamo_domain_multipliers.json for the planner.
Never publishes. Without YouTube credentials it still scores whatever stats exist.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import bamo_growth_loop as g  # noqa: E402
from app.bamo_topic_planner import load_json  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default="state")
    args = ap.parse_args()
    sd = Path(args.state_dir)
    policy = g.load_policy()
    state_path = sd / "bamo_growth_state.json"
    state = g.load_state(state_path, policy)
    now = datetime.now(timezone.utc)

    fetched, fetch_note = 0, "no_credentials"
    cid, secret, refresh = (os.getenv(k) for k in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"))
    if cid and secret and refresh:
        try:
            fetched = g.collect(state, g.YouTubeStats(cid, secret, refresh), now)
            fetch_note = "ok"
        except Exception as exc:  # network/API problems must not corrupt state
            fetch_note = f"fetch_failed: {type(exc).__name__}: {exc}"[:300]

    report = g.run_cycle(state, policy, now)
    names = list(load_json("bamo_domains.json")["domains"])
    mult = g.domain_multipliers(state, policy, names)
    report.update({"at": now.isoformat(timespec="seconds"), "fetched": fetched, "fetch": fetch_note,
                   "videos_tracked": len(state["videos"]),
                   "recipes": {f: r["champion"] | {"_version": r["version"]} for f, r in state["recipes"].items()}})
    g.save_state(state, state_path)
    (sd / "bamo_growth_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (sd / "bamo_domain_multipliers.json").write_text(json.dumps(mult, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
