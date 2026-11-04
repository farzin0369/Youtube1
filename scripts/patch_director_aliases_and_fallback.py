#!/usr/bin/env python3
"""Harden director: action aliases + procedural fallback after LLM validation failure."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "app" / "bamo_ai_director.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    changed = False

    # Expand action aliases so qwen outputs like rotate_y survive normalize.
    if '"rotate_y": "rotate"' not in text:
        needle = '"spin": "rotate", "spinning": "rotate", "yaw": "rotate",'
        if needle in text:
            text = text.replace(
                needle,
                '"spin": "rotate", "spinning": "rotate", "yaw": "rotate",
'
                '    "rotate_y": "rotate", "rotate_x": "rotate", "rotate_z": "rotate",
'
                '    "turn": "rotate", "turn_y": "rotate",',
                1,
            )
            changed = True

    # After repair failure, use procedural domain instead of hard raise.
    old_raise = '''        try:
            plan = _load_plan(repaired)
        except (ValueError, TypeError, json.JSONDecodeError) as repair_error:
            LOGGER.warning(
                "AI director repair was still not executable (%s). Excerpt: %s",
                repair_error, str(repaired)[:600].replace("\n", " "),
            )
            raise
'''
    new_raise = '''        try:
            plan = _load_plan(repaired)
        except (ValueError, TypeError, json.JSONDecodeError) as repair_error:
            LOGGER.warning(
                "AI director repair was still not executable (%s). Excerpt: %s",
                repair_error, str(repaired)[:600].replace("\n", " "),
            )
            from app.bamo_procedural_domains import try_procedural_domain
            procedural = try_procedural_domain(
                narration=narration,
                visual_brief=visual_brief,
                overlay=overlay,
                duration_seconds=float(duration_seconds),
            )
            if procedural is None:
                raise
            LOGGER.warning("Falling back to procedural domain author after invalid LLM graph")
            plan = validate_scene_graph(normalize_scene_graph(procedural))
            plan["matched_by"] = "procedural_domain_author"
            plan["provider"] = procedural.get("provider", "procedural")
            plan["semantic_review_score"] = int(procedural.get("semantic_review_score") or 90)
            plan["narration_exact"] = narration
            plan["visual_brief"] = visual_brief
            plan["overlay"] = overlay
            plan["duration_seconds"] = float(duration_seconds)
            plan["critic_provider"] = "skipped:procedural_domain"
            return plan
'''
    if "Falling back to procedural domain author after invalid LLM graph" not in text:
        if old_raise not in text:
            raise SystemExit("repair-failure block not found")
        text = text.replace(old_raise, new_raise, 1)
        changed = True

    if changed:
        TARGET.write_text(text, encoding="utf-8")
    compile(TARGET.read_text(encoding="utf-8"), str(TARGET), "exec")
    print("director aliases/fallback ok", "changed" if changed else "already")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
