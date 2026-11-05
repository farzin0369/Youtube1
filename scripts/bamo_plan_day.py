"""Print the balanced 6-slot BAMO plan for a date. Read-only: never renders or publishes."""
from __future__ import annotations
import argparse, json, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.bamo_topic_planner import plan_day  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--history", default="state/bamo_topic_history.json",
                    help="JSON list of {topic,title,domain}; missing file means empty history")
    args = ap.parse_args()
    hp = Path(args.history)
    history = json.loads(hp.read_text(encoding="utf-8")) if hp.is_file() else []
    plan = plan_day(date.fromisoformat(args.date), history)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0 if plan["diversity_ok"] and all(s["status"] == "planned" for s in plan["slots"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
