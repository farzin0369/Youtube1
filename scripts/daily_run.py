#!/usr/bin/env python3
"""Produce an ImamAli110 video with LTX-Video; uploads are always private."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.spiritual_pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description="ImamAli110 LTX-Video production pipeline")
    parser.add_argument("--format", choices=["shorts", "long"], default=None,
                        help="Override config content format for this run.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--upload-private", action="store_true",
                      help="Upload the QA-passed result as a private YouTube draft.")
    mode.add_argument("--dry-run", action="store_true",
                      help="Render and run QA but do not upload (default).")
    args = parser.parse_args()
    if args.format:
        os.environ["PRODUCTION_FORMAT"] = args.format
    run(dry_run=not args.upload_private, upload_private=args.upload_private)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Production failed ({type(exc).__name__}); see the redacted stage log in logs/.")
        raise SystemExit(1)
