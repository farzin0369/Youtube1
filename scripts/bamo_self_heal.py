#!/usr/bin/env python3
"""BAMO self-heal bootstrap with auto-learning rule engine.

Modes:
  --syntax-only  repair + compile critical files (no third-party imports)
  (default)      also import the production path (requires deps installed)
  --learn-from FILE  parse traceback, learn/promote rules, re-heal

Fail-closed: exit 1 if recovery is impossible.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bamo_heal_engine import (  # noqa: E402
    apply_rules_to_tree,
    learn_from_syntax_error,
    learn_from_traceback,
)

CRITICAL = [
    ROOT / "app" / "bamo_ai_director.py",
    ROOT / "app" / "bamo_production_renderer.py",
    ROOT / "app" / "bamo_motion_engine.py",
    ROOT / "app" / "bamo_scene_director.py",
    ROOT / "app" / "spiritual_video.py",
    ROOT / "scripts" / "bamo_blender_scene.py",
    ROOT / "scripts" / "bamo_blender_primitives.py",
    ROOT / "scripts" / "bamo_blender_motifs_a.py",
    ROOT / "scripts" / "bamo_blender_motifs_b.py",
]


def heal(*, syntax_only: bool = False, learn_log: str | None = None) -> int:
    report: list[str] = []
    errors: list[str] = []

    if learn_log:
        promoted = learn_from_traceback(learn_log)
        report.extend(f"learned:{rid}" for rid in promoted)

    applied = apply_rules_to_tree()
    report.extend(f"rule:{rid}" for rid in applied)

    # Second pass: if any critical file still fails compile, try learn_from_syntax_error
    for path in CRITICAL:
        if not path.is_file():
            errors.append(f"missing:{path.relative_to(ROOT)}")
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            report.append(f"compile_ok:{path.relative_to(ROOT)}")
        except SyntaxError as exc:
            promoted = learn_from_syntax_error(path, exc.lineno, exc.msg or "invalid syntax")
            if promoted:
                report.extend(f"learned:{rid}" for rid in promoted)
                try:
                    compile(path.read_text(encoding="utf-8"), str(path), "exec")
                    report.append(f"compile_ok_after_learn:{path.relative_to(ROOT)}")
                    continue
                except SyntaxError as exc2:
                    errors.append(f"syntax:{path.relative_to(ROOT)}:{exc2.lineno}:{exc2.msg}")
            else:
                errors.append(f"syntax:{path.relative_to(ROOT)}:{exc.lineno}:{exc.msg}")

    if not syntax_only:
        sys.path.insert(0, str(ROOT))
        try:
            import app.bamo_ai_director  # noqa: F401
            import app.bamo_motion_engine  # noqa: F401
            import app.bamo_production_renderer  # noqa: F401
            report.append("import_ok:production_path")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"import_fail:{type(exc).__name__}:{exc}")

    print("BAMO_SELF_HEAL_REPORT")
    for line in report:
        print("  +", line)
    if errors:
        print("BAMO_SELF_HEAL_ERRORS")
        for line in errors:
            print("  !", line)
        return 1
    print("BAMO_SELF_HEAL_OK", "syntax_only" if syntax_only else "full")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--syntax-only", action="store_true")
    parser.add_argument("--learn-from", type=str, default=None, help="traceback file or -")
    args = parser.parse_args()
    log_text = None
    if args.learn_from:
        if args.learn_from == "-":
            log_text = sys.stdin.read()
        else:
            log_text = Path(args.learn_from).read_text(encoding="utf-8")
    raise SystemExit(heal(syntax_only=args.syntax_only, learn_log=log_text))
