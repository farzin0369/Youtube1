#!/usr/bin/env python3
"""BAMO self-heal bootstrap — runs before any production/smoke render.

Modes:
  --syntax-only  repair + compile critical files (no third-party imports)
  (default)      also import the production path (requires deps installed)

Fail-closed: exit 1 if recovery is impossible.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def _repair_director_duplicate_else(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    fixed = re.sub(
        r"(else:\n                    obj\[label\] = list\(default\)\n)(?:                else:\n                    obj\[label\] = list\(default\)\n)+",
        r"\1",
        text,
    )
    if fixed != text:
        notes.append("removed_duplicate_else_blocks")
        text = fixed
    hard = '''def _bounded_vector(value: Any, *, low: float, high: float, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must be a three-number vector")
    result = [float(v) for v in value]
    if not all(math.isfinite(v) and low <= v <= high for v in result):
        raise ValueError(f"{label} contains an out-of-range value")
    return result
'''
    soft = '''def _bounded_vector(value: Any, *, low: float, high: float, label: str) -> list[float]:
    defaults = {
        "position": [0.0, 0.0, 1.0],
        "scale": [1.0, 1.0, 1.0],
        "rotation": [0.0, 0.0, 0.0],
    }
    if not isinstance(value, list) or len(value) != 3:
        return list(defaults.get(label, [0.0, 0.0, 0.0]))
    try:
        result = [float(v) for v in value]
    except (TypeError, ValueError):
        return list(defaults.get(label, [0.0, 0.0, 0.0]))
    if not all(math.isfinite(v) for v in result):
        return list(defaults.get(label, [0.0, 0.0, 0.0]))
    return [max(low, min(high, v)) for v in result]
'''
    if hard in text:
        text = text.replace(hard, soft, 1)
        notes.append("softened_bounded_vector")
    if "else:\n                    obj[label] = list(default)" not in text:
        needle = '''                value = obj.get(label)
                if isinstance(value, list) and len(value) == 3:
                    try:
                        obj[label] = [_clamp_number(component, low, high) for component in value]
                    except (TypeError, ValueError):
                        obj[label] = list(default)
            if "action_amount" in obj:
'''
        repl = '''                value = obj.get(label)
                if isinstance(value, list) and len(value) == 3:
                    try:
                        obj[label] = [_clamp_number(component, low, high) for component in value]
                    except (TypeError, ValueError):
                        obj[label] = list(default)
                else:
                    obj[label] = list(default)
            if "action_amount" in obj:
'''
        if needle in text:
            text = text.replace(needle, repl, 1)
            notes.append("added_normalize_else_default")
    return text, notes


def _repair_ass_playres(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if "PlayResX: 720" in text and "PlayResY: 1280" in text:
        text = text.replace("PlayResX: 720", "PlayResX: 1080", 1)
        text = text.replace("PlayResY: 1280", "PlayResY: 1920", 1)
        notes.append("ass_playres_1080x1920")
    return text, notes


def heal(*, syntax_only: bool = False) -> int:
    report: list[str] = []
    errors: list[str] = []

    director = ROOT / "app" / "bamo_ai_director.py"
    if director.is_file():
        raw = director.read_text(encoding="utf-8")
        fixed, notes = _repair_director_duplicate_else(raw)
        if notes:
            director.write_text(fixed, encoding="utf-8")
            report.extend(f"director:{n}" for n in notes)

    spiritual = ROOT / "app" / "spiritual_video.py"
    if spiritual.is_file():
        raw = spiritual.read_text(encoding="utf-8")
        fixed, notes = _repair_ass_playres(raw)
        if notes:
            spiritual.write_text(fixed, encoding="utf-8")
            report.extend(f"spiritual:{n}" for n in notes)

    for path in CRITICAL:
        if not path.is_file():
            errors.append(f"missing:{path.relative_to(ROOT)}")
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            report.append(f"compile_ok:{path.relative_to(ROOT)}")
        except SyntaxError as exc:
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
    args = parser.parse_args()
    raise SystemExit(heal(syntax_only=args.syntax_only))
