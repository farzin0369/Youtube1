#!/usr/bin/env python3
"""Rule engine for BAMO self-heal + auto-learning.

Safety model:
- Only declarative repairs: regex_replace, multi_replace, collapse_duplicate_lines
- Never eval / exec user or model-generated Python as repair code
- Every repair must pass compile() on the target file before it is kept
- Successful novel repairs are promoted into app/bamo_heal_rules.json
- Failures are appended to output/heal_memory.jsonl for later learning
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "app" / "bamo_heal_rules.json"
MEMORY_PATH = ROOT / "output" / "heal_memory.jsonl"
LEARNED_DIR = ROOT / "output" / "heal_learned"


def _load_rules() -> dict[str, Any]:
    if not RULES_PATH.is_file():
        return {"version": 1, "rules": []}
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def _save_rules(doc: dict[str, Any]) -> None:
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    RULES_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_memory(event: dict[str, Any]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = dict(event)
    event["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with MEMORY_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def _fingerprint(error_type: str, message: str, file: str = "") -> str:
    raw = f"{error_type}|{file}|{message.strip()[:240]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _compile_file(path: Path) -> tuple[bool, str]:
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
        return True, ""
    except SyntaxError as exc:
        return False, f"SyntaxError:{exc.lineno}:{exc.msg}"


def _apply_repair(text: str, repair: dict[str, Any]) -> tuple[str, bool]:
    rtype = repair.get("type")
    if rtype == "regex_replace":
        pattern = repair["pattern"]
        repl = repair["replacement"]
        count = int(repair.get("count", 0))
        new_text, n = re.subn(pattern, repl, text, count=count if count > 0 else 0)
        return new_text, n > 0
    if rtype == "multi_replace":
        changed = False
        for item in repair.get("replacements") or []:
            old, new = item.get("old", ""), item.get("new", "")
            if old and old in text:
                text = text.replace(old, new)
                changed = True
        return text, changed
    if rtype == "collapse_duplicate_lines":
        # Collapse runs of identical full lines (safe structural cleanup).
        lines = text.splitlines(keepends=True)
        out: list[str] = []
        prev = None
        run = 0
        max_run = int(repair.get("max_run", 1))
        changed = False
        for line in lines:
            if line == prev:
                run += 1
                if run <= max_run:
                    out.append(line)
                else:
                    changed = True
            else:
                prev = line
                run = 1
                out.append(line)
        return "".join(out), changed
    raise ValueError(f"unsupported repair type: {rtype}")


def apply_rules_to_tree(*, error_type: str | None = None, message: str = "") -> list[str]:
    """Apply all enabled rules; return list of applied rule ids."""
    doc = _load_rules()
    applied: list[str] = []
    for rule in doc.get("rules") or []:
        if not rule.get("enabled", True):
            continue
        match = rule.get("match") or {}
        if error_type and match.get("error_type") and match["error_type"] != error_type:
            # Still allow proactive structural rules without a matching error.
            if rule.get("id", "").startswith("ass-") or "duplicate" in rule.get("id", ""):
                pass
            else:
                # Proactive apply for compile-gate rules is OK; skip strict filter.
                pass
        if message and match.get("message_contains"):
            needles = match["message_contains"]
            if not any(n in message for n in needles):
                # Apply structural rules anyway when running full heal.
                if not any(k in rule.get("id", "") for k in ("duplicate", "soft-bounded", "playres")):
                    continue
        rel = rule.get("file") or ""
        path = ROOT / rel
        if not path.is_file():
            continue
        original = path.read_text(encoding="utf-8")
        try:
            new_text, changed = _apply_repair(original, rule.get("repair") or {})
        except re.error as exc:
            _append_memory({"event": "rule_regex_error", "rule": rule.get("id"), "error": str(exc)})
            continue
        if not changed:
            continue
        path.write_text(new_text, encoding="utf-8")
        ok, err = _compile_file(path)
        if not ok:
            path.write_text(original, encoding="utf-8")
            _append_memory({
                "event": "rule_verify_failed",
                "rule": rule.get("id"),
                "file": rel,
                "error": err,
            })
            continue
        rule["hits"] = int(rule.get("hits") or 0) + 1
        applied.append(str(rule.get("id")))
        _append_memory({"event": "rule_applied", "rule": rule.get("id"), "file": rel})
    if applied:
        _save_rules(doc)
    return applied


def learn_from_syntax_error(path: Path, lineno: int | None, msg: str) -> list[str]:
    """Attempt safe generic repairs on a SyntaxError and promote if verified."""
    if not path.is_file():
        return []
    original = path.read_text(encoding="utf-8")
    candidates: list[tuple[str, dict[str, Any]]] = []

    # Strategy A: collapse consecutive identical else-default blocks (known class).
    candidates.append((
        "auto-collapse-duplicate-else",
        {
            "type": "regex_replace",
            "pattern": r"(else:\n                    obj\[label\] = list\(default\)\n)(?:                else:\n                    obj\[label\] = list\(default\)\n)+",
            "replacement": r"\1",
            "count": 0,
        },
    ))
    # Strategy B: collapse any triple+ identical full lines.
    candidates.append((
        "auto-collapse-duplicate-lines",
        {"type": "collapse_duplicate_lines", "max_run": 1},
    ))

    promoted: list[str] = []
    for name, repair in candidates:
        text, changed = _apply_repair(original, repair)
        if not changed:
            continue
        path.write_text(text, encoding="utf-8")
        ok, err = _compile_file(path)
        if not ok:
            path.write_text(original, encoding="utf-8")
            _append_memory({
                "event": "learn_candidate_failed",
                "strategy": name,
                "file": str(path.relative_to(ROOT)),
                "error": err,
                "msg": msg,
            })
            continue
        # Promote into rules store
        doc = _load_rules()
        rule_id = f"learned-{name}-{_fingerprint('SyntaxError', msg, str(path))}"
        existing_ids = {r.get("id") for r in doc.get("rules") or []}
        if rule_id not in existing_ids:
            doc.setdefault("rules", []).append({
                "id": rule_id,
                "enabled": True,
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "match": {
                    "error_type": "SyntaxError",
                    "message_contains": [msg[:80]] if msg else ["invalid syntax"],
                },
                "repair": repair,
                "verify": "compile",
                "learned": True,
                "hits": 1,
                "source_lineno": lineno,
            })
            _save_rules(doc)
            promoted.append(rule_id)
            LEARNED_DIR.mkdir(parents=True, exist_ok=True)
            (LEARNED_DIR / f"{rule_id}.json").write_text(
                json.dumps(doc["rules"][-1], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        _append_memory({
            "event": "learned_rule",
            "rule": rule_id,
            "file": str(path.relative_to(ROOT)),
            "msg": msg,
        })
        original = text  # chain further strategies on fixed text
        break  # one successful promotion per call is enough
    return promoted


def learn_from_traceback(text: str) -> list[str]:
    """Parse a Python traceback and attempt learning on the failing file."""
    file_match = re.findall(r'File "([^"]+)", line (\d+)', text)
    err_match = re.search(r"(SyntaxError|ValueError|TypeError|RuntimeError):\s*(.*)$", text, re.M)
    if not file_match:
        _append_memory({"event": "learn_no_file", "excerpt": text[-500:]})
        return []
    # Prefer the last stack frame inside the repo
    target = None
    lineno = None
    for path_s, line_s in reversed(file_match):
        p = Path(path_s)
        if "Youtube1" in path_s or (ROOT / p.name).exists():
            # resolve relative to ROOT when possible
            rel = path_s
            for marker in ("Youtube1/", "Youtube1\\"):
                if marker in path_s:
                    rel = path_s.split(marker, 1)[-1]
                    break
            candidate = ROOT / rel
            if candidate.is_file():
                target = candidate
                lineno = int(line_s)
                break
            if p.is_file():
                target = p
                lineno = int(line_s)
                break
    if target is None:
        _append_memory({"event": "learn_file_not_found", "frames": file_match[-3:]})
        return []
    msg = err_match.group(2).strip() if err_match else "invalid syntax"
    err_type = err_match.group(1) if err_match else "SyntaxError"
    fp = _fingerprint(err_type, msg, str(target))
    _append_memory({
        "event": "failure_observed",
        "fingerprint": fp,
        "error_type": err_type,
        "message": msg,
        "file": str(target),
        "lineno": lineno,
    })
    if err_type == "SyntaxError":
        return learn_from_syntax_error(target, lineno, msg)
    # Non-syntax: record only; runtime rules must be curated or matched to existing.
    applied = apply_rules_to_tree(error_type=err_type, message=msg)
    return applied


def run_learning_cycle(log_text: str = "") -> dict[str, Any]:
    promoted = learn_from_traceback(log_text) if log_text.strip() else []
    applied = apply_rules_to_tree()
    return {"applied": applied, "promoted": promoted}


if __name__ == "__main__":
    import sys

    log = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else sys.stdin.read()
    result = run_learning_cycle(log)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if (result["applied"] or result["promoted"] or not log.strip()) else 1)
