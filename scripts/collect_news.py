"""Collect and validate current news RSS items before allocating GPU resources."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.research import fetch_news, rank_stories


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    stories = rank_stories(fetch_news(), limit=5)
    if len(stories) < 3:
        raise RuntimeError(f"Only {len(stories)} source-linked stories were collected; at least three are required.")
    for story in stories:
        if not str(story.get("url") or "").startswith(("https://", "http://")):
            raise RuntimeError("A selected story has no valid source URL; refusing to pass it to production.")
    payload = {
        "brand": "TT خبر",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "stories": stories,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Collected {len(stories)} source-linked stories across {len({x.get('category') for x in stories})} categories.")
    print(f"Research JSON saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
