#!/usr/bin/env python3
"""CLI entry for one BAMO Autopilot cycle (with council gates)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.bamo_autopilot import run_cycle


def main() -> int:
    report = run_cycle()
    actions = []
    for row in report.get("results") or []:
        result = row.get("result") or {}
        actions.append({
            "action": row["decision"]["action"],
            "ok": result.get("ok"),
            "gate": result.get("gate"),
            "blocked": result.get("blocked"),
            "reason": row["decision"].get("reason"),
            "error": result.get("error"),
        })
    print(json.dumps({
        "autonomy_level": report.get("autonomy_level"),
        "claims": report.get("claims"),
        "actions": actions,
    }, ensure_ascii=False, indent=2))
    heal_ok = all(
        row["result"].get("ok")
        for row in report.get("results") or []
        if row["decision"]["action"] == "self_heal"
    )
    return 0 if heal_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
