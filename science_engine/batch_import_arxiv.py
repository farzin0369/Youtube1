"""Resumable arXiv harvest for a large science research-candidate bank.

arXiv is queried conservatively; the bank is saved after every topic.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from science_engine.cli import BANK, fetch_arxiv, load_records, merge_records, save_records

TOPICS_PATH = Path(__file__).resolve().parent / "topics.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a bounded batch of arXiv research candidates.")
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--topics-per-run", type=int, default=5)
    parser.add_argument("--limit-per-topic", type=int, default=50)
    parser.add_argument("--delay-seconds", type=float, default=3.0)
    args = parser.parse_args()
    if args.start_index < 0 or args.topics_per_run < 1:
        parser.error("start-index must be >= 0 and topics-per-run must be >= 1.")
    limit = max(1, min(args.limit_per_topic, 100))
    delay = max(3.0, min(args.delay_seconds, 10.0))
    topics = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
    end = min(len(topics), args.start_index + args.topics_per_run)
    if args.start_index >= len(topics):
        parser.error(f"start-index must be less than {len(topics)} topics.")

    records = load_records()
    added_total = 0
    for index in range(args.start_index, end):
        query = str(topics[index]).strip()
        if not query:
            continue
        try:
            incoming = fetch_arxiv(query, limit)
            records, added = merge_records(records, incoming)
            save_records(records)
            added_total += added
            print(json.dumps({
                "topic_index": index,
                "topic": query,
                "fetched": len(incoming),
                "added": added,
                "duplicates_skipped": len(incoming) - added,
                "bank_total": len(records),
            }, ensure_ascii=False), flush=True)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"Stopped at topic {index} ({query!r}); completed batches were saved. Error: {exc}", file=sys.stderr)
            return 2
        if index + 1 < end:
            time.sleep(delay)
    print(json.dumps({
        "batch_start": args.start_index,
        "batch_end_exclusive": end,
        "topics_processed": end - args.start_index,
        "new_records_added": added_total,
        "total_bank_records": len(records),
        "next_start_index": end if end < len(topics) else None,
        "note": "arXiv records can be preprints; verify publication status and claims before scripting.",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
