#!/usr/bin/env python3
"""Restore app/bamo_ai_director.py from known-good full commit, then harden.

Never leave PLACEHOLDER. Always rewrite the whole module from a complete source.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "app" / "bamo_ai_director.py"
GOOD = (
    "https://raw.githubusercontent.com/farzin0369/Youtube1/"
    "7e81232706188da502b839fccd3547bcd8ab5e0e/app/bamo_ai_director.py"
)


def _apply_harden(text: str) -> str:
    needle = '"spin": "rotate", "spinning": "rotate", "yaw": "rotate",'
    if "rotate_y" not in text and needle in text:
        text = text.replace(
            needle,
            '"spin": "rotate", "spinning": "rotate", "yaw": "rotate",\n'
            '    "rotate_y": "rotate", "rotate_x": "rotate", "rotate_z": "rotate",\n'
            '    "turn": "rotate", "turn_y": "rotate",',
            1,
        )

    # Timeout / provider failure → procedural domain
    if "using procedural domain author" not in text:
        start_marker = "    response, provider = generate_text(\n        SYSTEM, prompt, max_tokens="
        start = text.find(start_marker)
        if start >= 0:
            end = text.find("\n    try:\n        plan = _load_plan(response)", start)
            if end > start:
                replacement = (
                    "    try:\n"
                    "        response, provider = generate_text(\n"
                    "            SYSTEM, prompt, max_tokens=900, temperature=0.2, json_mode=True, timeout=None,\n"
                    "        )\n"
                    "    except Exception as llm_exc:\n"
                    "        from app.bamo_procedural_domains import try_procedural_domain\n"
                    "        procedural = try_procedural_domain(\n"
                    "            narration=narration,\n"
                    "            visual_brief=visual_brief,\n"
                    "            overlay=overlay,\n"
                    "            duration_seconds=float(duration_seconds),\n"
                    "        )\n"
                    "        if procedural is None:\n"
                    "            raise\n"
                    "        LOGGER.warning(\n"
                    "            \"LLM unavailable (%s); using procedural domain author\", type(llm_exc).__name__\n"
                    "        )\n"
                    "        plan = validate_scene_graph(normalize_scene_graph(procedural))\n"
                    "        plan[\"matched_by\"] = \"procedural_domain_author\"\n"
                    "        plan[\"provider\"] = procedural.get(\"provider\", \"procedural\")\n"
                    "        plan[\"semantic_review_score\"] = int(procedural.get(\"semantic_review_score\") or 90)\n"
                    "        plan[\"narration_exact\"] = narration\n"
                    "        plan[\"visual_brief\"] = visual_brief\n"
                    "        plan[\"overlay\"] = overlay\n"
                    "        plan[\"duration_seconds\"] = float(duration_seconds)\n"
                    "        plan[\"critic_provider\"] = \"skipped:procedural_domain\"\n"
                    "        return plan\n"
                )
                text = text[:start] + replacement + text[end:]

    # Invalid repaired graph → procedural domain
    if "Falling back to procedural domain author after invalid LLM graph" not in text:
        marker = "AI director repair was still not executable"
        idx = text.find(marker)
        if idx >= 0:
            raise_idx = text.find("            raise\n", idx)
            if raise_idx >= 0:
                insert = (
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
                text = text[:raise_idx] + insert + text[raise_idx + len("            raise\n") :]
    return text


def main() -> int:
    text = urllib.request.urlopen(GOOD, timeout=60).read().decode("utf-8")
    if "def direct_scene" not in text or len(text) < 20000:
        raise SystemExit(f"bad source director len={len(text)}")
    text = _apply_harden(text)
    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("restored", TARGET, "bytes", len(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
