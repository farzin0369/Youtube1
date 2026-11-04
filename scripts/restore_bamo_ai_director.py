#!/usr/bin/env python3
"""Restore app/bamo_ai_director.py from known-good commit and apply harden patches."""
from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "app" / "bamo_ai_director.py"
GOOD = "https://raw.githubusercontent.com/farzin0369/Youtube1/7e81232706188da502b839fccd3547bcd8ab5e0e/app/bamo_ai_director.py"


def main() -> int:
    text = urllib.request.urlopen(GOOD, timeout=60).read().decode("utf-8")
    if "def direct_scene" not in text or len(text) < 20000:
        raise SystemExit("downloaded director looks truncated")

    old_act = '''_ACTION_ALIASES = {
    "spin": "rotate", "spinning": "rotate", "yaw": "rotate",
    "up": "rise", "ascend": "rise", "lift": "rise",
    "down": "fall", "descend": "fall", "drop": "fall",
    "move_x": "travel_x", "slide_x": "travel_x", "translate_x": "travel_x",
    "move_y": "travel_y", "slide_y": "travel_y",
    "scale": "pulse", "breathe": "pulse", "throb": "pulse",
    "appear": "reveal", "fade_in": "reveal", "grow": "reveal",
    "idle": "none", "static": "none", "still": "none", "": "none",
}'''
    new_act = '''_ACTION_ALIASES = {
    "spin": "rotate", "spinning": "rotate", "yaw": "rotate",
    "rotate_y": "rotate", "rotate_x": "rotate", "rotate_z": "rotate",
    "turn": "rotate", "turn_y": "rotate",
    "up": "rise", "ascend": "rise", "lift": "rise",
    "down": "fall", "descend": "fall", "drop": "fall",
    "move_x": "travel_x", "slide_x": "travel_x", "translate_x": "travel_x",
    "move_y": "travel_y", "slide_y": "travel_y",
    "scale": "pulse", "breathe": "pulse", "throb": "pulse", "scale_up": "reveal",
    "appear": "reveal", "fade_in": "reveal", "grow": "reveal",
    "idle": "none", "static": "none", "still": "none", "": "none",
}'''
    if old_act in text:
        text = text.replace(old_act, new_act, 1)

    old_gen = '''    response, provider = generate_text(
        SYSTEM, prompt, max_tokens=1800, temperature=0.2, json_mode=True, timeout=180,
    )
'''
    new_gen = '''    try:
        response, provider = generate_text(
            SYSTEM, prompt, max_tokens=900, temperature=0.2, json_mode=True, timeout=None,
        )
    except Exception as llm_exc:
        from app.bamo_procedural_domains import try_procedural_domain
        procedural = try_procedural_domain(
            narration=narration,
            visual_brief=visual_brief,
            overlay=overlay,
            duration_seconds=float(duration_seconds),
        )
        if procedural is None:
            raise
        LOGGER.warning("LLM unavailable (%s); using procedural domain author", type(llm_exc).__name__)
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
    if "using procedural domain author" not in text and old_gen in text:
        text = text.replace(old_gen, new_gen, 1)

    old_rep = '''        try:
            plan = _load_plan(repaired)
        except (ValueError, TypeError, json.JSONDecodeError) as repair_error:
            LOGGER.warning(
                "AI director repair was still not executable (%s). Excerpt: %s",
                repair_error, str(repaired)[:600].replace("\\n", " "),
            )
            raise
'''
    # Note: file uses real newlines in strings; match actual source form
    old_rep2 = (
        "        try:\n"
        "            plan = _load_plan(repaired)\n"
        "        except (ValueError, TypeError, json.JSONDecodeError) as repair_error:\n"
        "            LOGGER.warning(\n"
        "                \"AI director repair was still not executable (%s). Excerpt: %s\",\n"
        "                repair_error, str(repaired)[:600].replace(\"\\n\", \" \"),\n"
        "            )\n"
        "            raise\n"
    )
    new_rep2 = (
        "        try:\n"
        "            plan = _load_plan(repaired)\n"
        "        except (ValueError, TypeError, json.JSONDecodeError) as repair_error:\n"
        "            LOGGER.warning(\n"
        "                \"AI director repair was still not executable (%s). Excerpt: %s\",\n"
        "                repair_error, str(repaired)[:600].replace(\"\\n\", \" \"),\n"
        "            )\n"
        "            from app.bamo_procedural_domains import try_procedural_domain\n"
        "            procedural = try_procedural_domain(\n"
        "                narration=narration,\n"
        "                visual_brief=visual_brief,\n"
        "                overlay=overlay,\n"
        "                duration_seconds=float(duration_seconds),\n"
        "            )\n"
        "            if procedural is None:\n"
        "                raise\n"
        "            LOGGER.warning(\"Falling back to procedural domain author after invalid LLM graph\")\n"
        "            plan = validate_scene_graph(normalize_scene_graph(procedural))\n"
        "            plan[\"matched_by\"] = \"procedural_domain_author\"\n"
        "            plan[\"provider\"] = procedural.get(\"provider\", \"procedural\")\n"
        "            plan[\"semantic_review_score\"] = int(procedural.get(\"semantic_review_score\") or 90)\n"
        "            plan[\"narration_exact\"] = narration\n"
        "            plan[\"visual_brief\"] = visual_brief\n"
        "            plan[\"overlay\"] = overlay\n"
        "            plan[\"duration_seconds\"] = float(duration_seconds)\n"
        "            plan[\"critic_provider\"] = \"skipped:procedural_domain\"\n"
        "            return plan\n"
    )
    if "Falling back to procedural domain author after invalid LLM graph" not in text:
        if old_rep2 in text:
            text = text.replace(old_rep2, new_rep2, 1)

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("restored", TARGET, "bytes", len(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
