#!/usr/bin/env python3
"""One brain tick: seed research notes, assess score, print publish readiness."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.bamo_brain import assess, seed_baseline_research


def main() -> int:
    seeded = seed_baseline_research()
    report = assess()
    print(json.dumps({"seeded": seeded, "brain": report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
