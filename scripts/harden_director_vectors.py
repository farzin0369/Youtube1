#!/usr/bin/env python3
"""Harden app/bamo_ai_director.py vector parsing for truncated local-LLM JSON.

Safe to run repeatedly. Commits are left to the caller.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "app" / "bamo_ai_director.py"

OLD_BOUNDED = '''def _bounded_vector(value: Any, *, low: float, high: float, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must be a three-number vector")
    result = [float(v) for v in value]
    if not all(math.isfinite(v) and low <= v <= high for v in result):
        raise ValueError(f"{label} contains an out-of-range value")
    return result
'''

NEW_BOUNDED = '''def _bounded_vector(value: Any, *, low: float, high: float, label: str) -> list[float]:
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

# Only match when an else is NOT already present after the try/except.
OLD_NORM = '''                value = obj.get(label)
                if isinstance(value, list) and len(value) == 3:
                    try:
                        obj[label] = [_clamp_number(component, low, high) for component in value]
                    except (TypeError, ValueError):
                        obj[label] = list(default)
            if "action_amount" in obj:
'''

NEW_NORM = '''                value = obj.get(label)
                if isinstance(value, list) and len(value) == 3:
                    try:
                        obj[label] = [_clamp_number(component, low, high) for component in value]
                    except (TypeError, ValueError):
                        obj[label] = list(default)
                else:
                    obj[label] = list(default)
            if "action_amount" in obj:
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    changed = False
    if OLD_BOUNDED in text:
        text = text.replace(OLD_BOUNDED, NEW_BOUNDED, 1)
        changed = True
        print("applied soft _bounded_vector defaults")
    elif "defaults = {" in text and '"position": [0.0, 0.0, 1.0]' in text:
        print("_bounded_vector already hardened")
    else:
        print("WARNING: _bounded_vector pattern not found")
    if OLD_NORM in text:
        text = text.replace(OLD_NORM, NEW_NORM, 1)
        changed = True
        print("applied normalize else-default for vectors")
    elif "else:\n                    obj[label] = list(default)" in text:
        print("normalize vector defaults already present")
    else:
        print("WARNING: normalize vector pattern not found")
    TARGET.write_text(text, encoding="utf-8")
    compile(text, str(TARGET), "exec")
    print("director size", len(text), "changed", changed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
