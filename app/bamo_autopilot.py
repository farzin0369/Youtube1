"""BAMO Autopilot — practical autonomy layer with 11-agent council gates.

Loop: observe → decide → heal → council preflight → produce → council post-render → learn → optional publish

Publish stays gated by env flags AND brain self-score == 100.
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

PUBLISH_ENABLED = os.getenv("BAMO_AUTOPILOT_PUBLISH", "false").lower() == "true"
PRODUCTION_VISUALS_APPROVED = os.getenv("BAMO_PRODUCTION_VISUALS_APPROVED", "false").lower() == "true"
COUNCIL_ENABLED = os.getenv("BAMO_AUTOPILOT_COUNCIL", "true").lower() == "true"
COUNCIL_STRICT = os.getenv("BAMO_AUTOPILOT_COUNCIL_STRICT", "false").lower() == "true"
SKIP_PRODUCE = os.getenv("BAMO_AUTOPILOT_SKIP_PRODUCE", "false").lower() == "true"


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


def _default_candidate_package() -> dict[str, Any]:
    return {
        "title": "یک انتخاب کوچک مسیر فردا را عوض می‌کند",
        "topic": "روان‌شناسی تصمیم و عادت‌های کوچک",
        "script": (
            "گاهی یک انتخاب کوچک، مسیر فردا را عوض می‌کند. "
            "مغز ما با تمرین، مسیرهای تازه می‌سازد. "
            "گام‌به‌گام پیش برو؛ هر پله یک پیشرفت است. "
            "فردا از همین شروع ساده ساخته می‌شود."
        ),
        "description": "موشن‌گرافیک سه‌بعدی درباره قدرت انتخاب‌های کوچک و رشد تدریجی.",
        "tags": ["روانشناسی", "عادت", "انگیزشی", "BAMO", "موشن_گرافیک"],
        "thumbnail_text": "انتخاب کوچک",
        "scenes": [
            {
                "spoken_text": "گاهی یک انتخاب کوچک، مسیر فردا را عوض می‌کند.",
                "visual_query": "two diverging glowing paths with a central choice sphere",
                "on_screen_text": "انتخاب کوچک",
            },
            {
                "spoken_text": "مغز ما با تمرین، مسیرهای تازه می‌سازد.",
                "visual_query": "neural network nodes lighting up in sequence",
                "on_screen_text": "مسیرهای تازه",
            },
            {
                "spoken_text": "گام‌به‌گام پیش برو؛ هر پله یک پیشرفت است.",
                "visual_query": "ascending geometric steps toward a bright peak",
                "on_screen_text": "گام‌به‌گام",
            },
            {
                "spoken_text": "فردا از همین شروع ساده ساخته می‌شود.",
                "visual_query": "sunrise over a calm horizon with rising light",
                "on_screen_text": "شروع ساده",
            },
        ],
    }


def _load_history() -> list[dict[str, Any]]:
    history_path = ROOT / "state" / "youtube_history.json"
    if not history_path.is_file():
        return []
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.get("items") or [])
    except json.JSONDecodeError:
        return []
    return []


def _run_council(
    content: dict[str, Any],
    *,
    render: dict[str, Any] | None = None,
    media_qa: dict[str, Any] | None = None,
    phase: str = "preflight",
) -> dict[str, Any]:
    if not COUNCIL_ENABLED:
        return {
            "ok": True,
            "skipped": True,
            "phase": phase,
            "gate": "SKIPPED",
            "reason": "BAMO_AUTOPILOT_COUNCIL=false",
        }
    try:
        from app.bamo_agent_council import review_with_council
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "phase": phase, "error": f"council_import:{exc}", "gate": "ERROR"}

    memory_dir = STATE_DIR / "council_memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    try:
        report = review_with_council(
            content,
            render=render or {},
            media_qa=media_qa or {},
            memory_dir=memory_dir,
            history=_load_history(),
        )
        report["ok"] = True
        report["phase"] = phase
        out = STATE_DIR / f"council_{phase}_{int(time.time())}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (STATE_DIR / f"last_council_{phase}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report
    except Exception as exc:  # noqa: BLE001
        payload = {
            "ok": False,
            "phase": phase,
            "gate": "BLOCKED",
            "error": str(exc),
        }
        (STATE_DIR / f"last_council_{phase}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if COUNCIL_STRICT:
            raise
        return payload


def observe() -> dict[str, Any]:
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
    last_pre = STATE_DIR / "last_council_preflight.json"
    last_post = STATE_DIR / "last_council_post_render.json"

    def _gate(path: Path) -> str | None:
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("gate")
        except json.JSONDecodeError:
            return None

    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "heal_rules": len(rules.get("rules") or []),
        "recent_events": recent_failures[-10:],
        "publish_enabled": PUBLISH_ENABLED,
        "visuals_approved": PRODUCTION_VISUALS_APPROVED,
        "council_enabled": COUNCIL_ENABLED,
        "council_strict": COUNCIL_STRICT,
        "last_council_preflight_gate": _gate(last_pre),
        "last_council_post_render_gate": _gate(last_post),
    }


def decide(observation: dict[str, Any]) -> list[Decision]:
    decisions: list[Decision] = []
    decisions.append(Decision(
        action="self_heal",
        reason="Mandatory preflight: repair known issues and learn from recent failures",
        priority=10,
    ))
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
        action="council_preflight",
        reason="11-agent council reviews package before heavy render",
        priority=25,
    ))

    if not SKIP_PRODUCE:
        decisions.append(Decision(
            action="produce_preview",
            reason="Generate a real 3D preview short unless strict council preflight blocked",
            priority=40,
            metadata={"depends_on": "council_preflight"},
        ))
        decisions.append(Decision(
            action="council_post_render",
            reason="11-agent council re-evaluates with render evidence",
            priority=55,
            metadata={"depends_on": "produce_preview"},
        ))
    else:
        decisions.append(Decision(
            action="skip_produce",
            reason="BAMO_AUTOPILOT_SKIP_PRODUCE=true",
            priority=40,
        ))

    decisions.append(Decision(
        action="editorial_score",
        reason="Persist growth/retention recommendation from council gates",
        priority=70,
    ))

    if PUBLISH_ENABLED and PRODUCTION_VISUALS_APPROVED:
        decisions.append(Decision(
            action="publish_youtube",
            reason="Operator enabled publish; requires council PASS and brain score 100",
            priority=90,
            metadata={"requires_council_gate": "PASS", "requires_brain_score": 100},
        ))
    else:
        decisions.append(Decision(
            action="skip_publish",
            reason="Publish gated (BAMO_AUTOPILOT_PUBLISH + BAMO_PRODUCTION_VISUALS_APPROVED)",
            priority=90,
        ))
    return sorted(decisions, key=lambda d: d.priority)


def execute(decision: Decision, context: dict[str, Any]) -> dict[str, Any]:
    if decision.action == "self_heal":
        code, out = _run([sys.executable, str(ROOT / "scripts" / "bamo_self_heal.py"), "--syntax-only"], timeout=120)
        return {"ok": code == 0, "log": out[-4000:], "action": decision.action}

    if decision.action == "deep_learn":
        mem = ROOT / "output" / "heal_memory.jsonl"
        log = mem.read_text(encoding="utf-8") if mem.is_file() else ""
        sys.path.insert(0, str(ROOT / "scripts"))
        from bamo_heal_engine import run_learning_cycle

        result = run_learning_cycle(log)
        return {"ok": True, "learned": result, "action": decision.action}

    if decision.action == "council_preflight":
        package = context.setdefault("package", _default_candidate_package())
        report = _run_council(package, render={}, media_qa={}, phase="preflight")
        context["council_preflight"] = report
        blocked = report.get("gate") == "BLOCKED"
        return {
            "ok": not blocked or not COUNCIL_STRICT,
            "blocked": blocked,
            "gate": report.get("gate"),
            "average_score": report.get("average_score"),
            "approvals": report.get("approvals"),
            "critical_issues": report.get("critical_issues"),
            "action": decision.action,
            "error": report.get("error"),
        }

    if decision.action == "produce_preview":
        pre = context.get("council_preflight") or {}
        if COUNCIL_STRICT and pre.get("gate") == "BLOCKED":
            return {
                "ok": False,
                "skipped": True,
                "action": decision.action,
                "reason": "council_preflight_blocked",
            }
        code, out = _run([sys.executable, str(ROOT / "scripts" / "smoke_bamo_3d_renderer.py")], timeout=3600)
        evidence_path = ROOT / "output" / "bamo-3d-smoke" / "smoke-evidence.json"
        render: dict[str, Any] = {}
        if evidence_path.is_file():
            try:
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                render = {
                    "visual_source": "bamo-cpu-3d-motion",
                    "visual_scene_count": len(evidence.get("visual_plans") or []),
                    "scene_visual_plans": evidence.get("visual_plans"),
                    "render_backend": "blender-cycles-cpu",
                    "visual_quality_tier": "blender-cpu-3d-preview",
                    "production_visuals_approved": PRODUCTION_VISUALS_APPROVED,
                    "video_path": evidence.get("video_path"),
                    "video_width": evidence.get("video_width"),
                    "video_height": evidence.get("video_height"),
                }
            except json.JSONDecodeError:
                pass
        context["render"] = render
        context["produce_ok"] = code == 0
        return {"ok": code == 0, "log": out[-6000:], "action": decision.action, "render": render}

    if decision.action == "council_post_render":
        if not context.get("produce_ok"):
            return {
                "ok": False,
                "skipped": True,
                "action": decision.action,
                "reason": "produce_preview_failed",
            }
        package = context.get("package") or _default_candidate_package()
        render = context.get("render") or {}
        report = _run_council(package, render=render, media_qa={"ok": True}, phase="post_render")
        context["council_post_render"] = report
        blocked = report.get("gate") == "BLOCKED"
        return {
            "ok": not blocked or not COUNCIL_STRICT,
            "blocked": blocked,
            "gate": report.get("gate"),
            "average_score": report.get("average_score"),
            "approvals": report.get("approvals"),
            "action": decision.action,
            "error": report.get("error"),
        }

    if decision.action == "editorial_score":
        pre = context.get("council_preflight") or {}
        post = context.get("council_post_render") or {}
        score = {
            "source": "council",
            "preflight_gate": pre.get("gate"),
            "post_render_gate": post.get("gate"),
            "preflight_average": pre.get("average_score"),
            "post_render_average": post.get("average_score"),
            "recommendation": (
                "Council PASS — candidate eligible for human visual review / gated publish"
                if post.get("gate") == "PASS" or pre.get("gate") == "PASS"
                else "Council blocked or incomplete — revise hook, scene specificity, or claims before scaling"
            ),
        }
        path = STATE_DIR / "last_editorial_score.json"
        path.write_text(json.dumps(score, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "score": score, "action": decision.action}

    if decision.action == "publish_youtube":
        post = context.get("council_post_render") or context.get("council_preflight") or {}
        if post.get("gate") != "PASS":
            return {
                "ok": False,
                "action": decision.action,
                "error": "council_gate_not_PASS",
                "gate": post.get("gate"),
            }
        try:
            from app.bamo_brain import assess
            brain = assess()
            context["brain"] = brain
            if not brain.get("publish_ready_by_brain") or float(brain.get("score") or 0) < 100:
                return {
                    "ok": False,
                    "action": decision.action,
                    "error": "brain_score_not_100",
                    "brain_score": brain.get("score"),
                    "publish_ready_by_brain": brain.get("publish_ready_by_brain"),
                }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "action": decision.action, "error": f"brain_assess:{exc}"}
        if not (PUBLISH_ENABLED and PRODUCTION_VISUALS_APPROVED):
            return {"ok": False, "action": decision.action, "error": "publish_gates_closed"}
        return {
            "ok": False,
            "action": decision.action,
            "error": "Publish path reserved: call existing youtube_client only after brain=100, gates open, and human-reviewed MP4 once",
            "brain_score": context.get("brain", {}).get("score"),
        }

    if decision.action in {"skip_publish", "skip_produce"}:
        return {"ok": True, "action": decision.action, "reason": decision.reason}

    return {"ok": False, "action": decision.action, "error": "unknown_action"}


def run_cycle(package: dict[str, Any] | None = None) -> dict[str, Any]:
    observation = observe()
    decisions = decide(observation)
    context: dict[str, Any] = {"package": package or _default_candidate_package()}
    results = []
    for decision in decisions:
        try:
            results.append({"decision": asdict(decision), "result": execute(decision, context)})
        except Exception as exc:  # noqa: BLE001
            results.append({"decision": asdict(decision), "result": {"ok": False, "error": str(exc)}})
            if COUNCIL_STRICT and decision.action.startswith("council_"):
                break
    try:
        from app.bamo_brain import assess, seed_baseline_research
        seed_baseline_research()
        context["brain"] = assess()
    except Exception as exc:  # noqa: BLE001
        context["brain"] = {"error": str(exc), "score": 0}
    report = {
        "observation": observation,
        "results": results,
        "context_keys": sorted(context.keys()),
        "brain": context.get("brain"),
        "autonomy_level": "practical_autopilot_v3_brain",
        "claims": {
            "superhuman": False,
            "guaranteed_million_subs": False,
            "council_connected": True,
            "brain_self_score": True,
            "self_heal_and_learn_rules": True,
            "decision_loop": True,
            "auto_merge_foreign_code": False,
        },
    }
    out = STATE_DIR / f"cycle_{int(time.time())}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (STATE_DIR / "last_cycle.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run_cycle(), ensure_ascii=False, indent=2))
