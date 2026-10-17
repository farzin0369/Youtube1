#!/usr/bin/env python3
"""Create vertical clip candidates from a locally available, authorized video."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from app.clip_automation import build_clips


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Local source video file")
    parser.add_argument("--output", default=Path("output/clip-automation"), type=Path)
    parser.add_argument("--clip-seconds", type=float, default=30.0)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--rights-confirmed", action="store_true", help="Confirm you own or are licensed to use the source")
    args = parser.parse_args()
    result = build_clips(args.input, args.output, clip_seconds=args.clip_seconds,
                         count=args.count, rights_confirmed=args.rights_confirmed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
