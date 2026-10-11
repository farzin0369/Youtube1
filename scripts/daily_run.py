#!/usr/bin/env python3
"""Generate a Persian spiritual video; publishing requires explicit --publish."""
from __future__ import annotations

import argparse

from app.spiritual_pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily Persian spiritual video pipeline")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--publish", action="store_true", help="upload and schedule for the next safe 18:00 Tehran slot")
    mode.add_argument("--dry-run", action="store_true", help="render the video but do not upload (default)")
    args = parser.parse_args()
    run(dry_run=not args.publish)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Production failed ({type(exc).__name__}); see the redacted stage log in logs/.")
        raise SystemExit(1)
