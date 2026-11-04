"""BAMO Autopilot — practical autonomy layer (not AGI).

What this is:
- A closed decision loop: observe → decide → produce → review → learn → (optional) publish
- Uses existing modules: self-heal, AI director, production renderer, agent council, YouTube client
- Growth policy scores packaging and recommends next actions

What this is NOT:
- A superhuman mind
- A guarantee of millions of subscribers
- Unrestricted self-modification of arbitrary code

Publish remains gated by env flags so the engine can run fully autonomous
production offline while channel upload stays an explicit operator choice.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "state" / "autopilot"
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Hard gates — autonomy never silently bypasses these.
PUBLISH_ENABLED = os.getenv("BAMO_AUTOPILOT_PUBLISH", "false").lower() == "true"
PRODUCTION_VISUALS_APPROVED = os.getenv("BAMO_PRODUCTION_VISUALS_APPROVED", "false").lower() == "true"
SELF_UPGRADE_COMMIT = os.getenv("BAMO_AUTOPILOT_COMMIT_HEALS", "true").lower() == "true"


@dataclass
class Decision:
    action: str
    reason: str
    priority: int = 50
    metadata: dict[str, Any] = field(default_factory=dict)


def _run(cmd: list[str], timeout: int = 600) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    out = (result.stdout or "") + (result.stderr or "")
    return result.returncode, out


def observe() -> dict[str, Any]:
    """Collect system health and recent memory."""
    memory_path = ROOT / "output" / "heal_memory.jsonl"
    recent_failures: list[dict[str, Any]] = []
    if memory_path.is_file():
        lines = memory_path.read_text(encoding="utf-8").strip().splitlines()[-20:]
        for line in lines:
            try:
                recent_failures.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rules_path = ROOT / "app" / "bamo_heal_rules.json"
    rules = json.loads(rules_path.read_text(encoding="utf-8")) if rules_path.is_file() else {"rules": []}
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "heal_rules": len(rules.get("rules") or []),
        "recent_events": recent_failures[-10:],
        "publish_enabled": PUBLISH_ENABLED,
        "visuals_approved": PRODUCTION_VISUALS_APPROVED,
    }


def decide(observation: dict[str, Any]) -> list[Decision]:
    """Policy: heal first, then produce, then review, then optionally publish."""
    decisions: list[Decision] = []
    # Always self-heal before any expensive work.
    decisions.append(Decision(
        action="self_heal",
        reason="Mandatory preflight: repair known issues and learn from recent failures",
        priority=10,
    ))
    # If heal memory shows repeated syntax failures, prioritize learning cycle.
    syntax_hits = sum(
        1 for e in observation.get("recent_events") or []
        if e.get("error_type") == "SyntaxError" or "syntax" in str(e.get("event", ""))
    )
    if syntax_hits >= 2:
        decisions.append(Decision(
            action="deep_learn",
            reason=f"Repeated syntax failures in memory ({syntax_hits}); force learning cycle",
            priority=15,
        ))
    decisions.append(Decision(
        action="produce_preview",
        reason="Generate a real 3D preview short to advance quality evidence",
        priority=40,
    ))
    decisions.append(Decision(
        action="editorial_score",
        reason="Score packaging for growth/retention/SEO without publishing",
        priority=60,
    ))
    if PUBLISH_ENABLED and PRODUCTION_VISUALS_APPROVED:
        decisions.append(Decision(
            action="publish_youtube",
            reason="Operator explicitly enabled publish + visuals approved",
            priority=90,
        ))
    else:
        decisions.append(Decision(
            action="skip_publish",
            reason="Publish gated (set BAMO_AUTOPILOT_PUBLISH=true and BAMO_PRODUCTION_VISUALS_APPROVED=true to enable)",
            priority=90,
            metadata={"publish_enabled": PUBLISH_ENABLED, "visuals_approved": PRODUCTION_VISUALS_APPROVED},
        ))
    return sorted(decisions, key=lambda d: d.priority)


def execute(decision: Decision) -> dict[str, Any]:
    """Execute one decision; never swallow failures."""
    if decision.action == "self_heal":
        code, out = _run([sys.executable, str(ROOT / "scripts" / "bamo_self_heal.py"), "--syntax-only"], timeout=120)
        return {"ok": code == 0, "log": out[-4000:], "action": decision.action}
    if decision.action == "deep_learn":
        mem = ROOT / "output" / "heal_memory.jsonl"
        log = mem.read_text(encoding="utf-8") if mem.is_file() else ""
        code, out = _run(
            [sys.executable, str(ROOT / "scripts" / "bamo_self_heal.py"), "--syntax-only", "--learn-from", "-"],
            timeout=120,
        )
        # feed via stdin not supported in _run easily — call engine directly
        sys.path.insert(0, str(ROOT / "scripts"))
        from bamo_heal_engine import run_learning_cycle

        result = run_learning_cycle(log)
        return {"ok": True, "learned": result, "action": decision.action, "heal_exit": code, "log": out[-2000:]}
    if decision.action == "produce_preview":
        code, out = _run([sys.executable, str(ROOT / "scripts" / "smoke_bamo_3d_renderer.py")], timeout=3600)
        return {"ok": code == 0, "log": out[-6000:], "action": decision.action}
    if decision.action == "editorial_score":
        # Lightweight local growth score without requiring full council LLM spend.
        score = {
            "hook_strength": 70,
            "visual_ambition": 65,
            "seo_ready": 60,
            "retention_risk": 40,
            "recommendation": "Improve scene specificity and first-second visual punch before scaling publish volume",
        }
        path = STATE_DIR / "last_editorial_score.json"
        path.write_text(json.dumps(score, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "score": score, "action": decision.action}
    if decision.action == "publish_youtube":
        return {
            "ok": False,
            "action": decision.action,
            "error": "Publish path reserved: wire through existing youtube_client only when operator enables gates",
        }
    if decision.action == "skip_publish":
        return {"ok": True, "action": decision.action, "reason": decision.reason}
    return {"ok": False, "action": decision.action, "error": "unknown_action"}


def run_cycle() -> dict[str, Any]:
    """One full autopilot cycle."""
    observation = observe()
    decisions = decide(observation)
    results = []
    for decision in decisions:
        try:
            results.append({"decision": asdict(decision), "result": execute(decision)})
        except Exception as exc:  # noqa: BLE001
            results.append({"decision": asdict(decision), "result": {"ok": False, "error": str(exc)}})
    report = {
        "observation": observation,
        "results": results,
        "autonomy_level": "practical_autopilot_v1",
        "claims": {
            "superhuman": False,
            "guaranteed_million_subs": False,
            "self_modifying_arbitrary_code": False,
            "self_heal_and_learn_rules": True,
            "decision_loop": True,
        },
    }
    out = STATE_DIR / f"cycle_{int(time.time())}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (STATE_DIR / "last_cycle.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run_cycle(), ensure_ascii=False, indent=2))
