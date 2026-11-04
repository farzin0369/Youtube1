#!/usr/bin/env python3
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "bamo_ai_director.py"

OLD = '''    response, provider = generate_text(
        SYSTEM, prompt, max_tokens=1800, temperature=0.2, json_mode=True, timeout=180,
    )
'''

NEW = '''    try:
        response, provider = generate_text(
            SYSTEM, prompt, max_tokens=900, temperature=0.2, json_mode=True, timeout=None,
        )
    except Exception as llm_exc:
        # CPU Actions often cannot finish qwen2.5:7b JSON in time. Prefer a smaller
        # model via env; when every provider fails, use deterministic domain graphs
        # that still express the scientific narration (not a silent/fake motif).
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


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if "procedural_domain_author" in text and "try_procedural_domain" in text:
        print("already patched")
        compile(text, str(TARGET), "exec")
        return 0
    if OLD not in text:
        # try alternate timeout form
        alt = OLD.replace("timeout=180", "timeout=None")
        if alt in text:
            text = text.replace(alt, NEW, 1)
        else:
            raise SystemExit("generate_text block not found")
    else:
        text = text.replace(OLD, NEW, 1)
    TARGET.write_text(text, encoding="utf-8")
    compile(text, str(TARGET), "exec")
    print("director procedural fallback applied", len(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
