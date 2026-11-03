"""Semantic AI film director: turns narration into a validated, executable 3D scene graph.

The LLM authors the visual composition per scene. Blender is the deterministic renderer,
not the creative decision maker. Unknown subjects are planned compositionally rather than
mapped to a finite list of keyword motifs. Provider failure is fail-closed.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

from app.llm_provider import generate_text

SYSTEM = """You are BAMO's autonomous film director and 3D cinematography designer.
Understand the meaning of the supplied narration and design a visually literal, cinematic,
original scene that communicates that exact meaning without generic filler.
Return ONLY valid JSON. Do not merely repeat a visual search query. Design a coherent shot:
objects, spatial relationships, action, camera movement, depth, composition and lighting intent.
Use only the executable scene grammar below; never invent unsupported commands.
Scene graph schema:
{
 "visual_thesis":"one sentence explaining what the viewer should understand",
 "camera":{"move":"push_in|orbit|tracking|sweep|crane|static","angle":"low|eye|high|top","focus":"short object name"},
 "palette":{"background":"#RRGGBB","key":"#RRGGBB","accent":"#RRGGBB"},
 "objects":[
  {"id":"unique_snake_case","kind":"sphere|cube|cylinder|torus|cone|icosphere|ring|line",
   "role":"what this object means in the narration",
   "position":[x,y,z],"scale":[x,y,z],"rotation":[x,y,z],
   "material":"key|accent|neutral|dark",
   "action":"rise|fall|rotate|orbit|pulse|travel_x|travel_y|reveal|none",
   "action_amount":number}
 ],
 "relationships":[{"from":"object_id","to":"object_id","kind":"connect|orbit|point_to"}]
}
Limits: 3-12 objects, each id unique, positions within -6..6, scales 0.05..4,
rotations within -6.28..6.28, action_amount within -4..4. Use meaningful spatial
relationships. A science explanation must depict the actual mechanism; a story must
depict its actual characters/setting/action; abstract ideas need a concrete metaphor
that preserves the sentence's meaning. No text objects; Persian typography is composited
from the canonical narration timeline by the editor. No arbitrary code, scripts, URLs,
file paths, or external assets. Make every shot composition distinct and appropriate.
""".strip()


def _bounded_vector(value: Any, *, low: float, high: float, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must be a three-number vector")
    result = [float(v) for v in value]
    if not all(math.isfinite(v) and low <= v <= high for v in result):
        raise ValueError(f"{label} contains an out-of-range value")
    return result


def validate_scene_graph(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("AI director response must be a JSON object")
    objects = raw.get("objects")
    if not isinstance(objects, list) or not 3 <= len(objects) <= 12:
        raise ValueError("AI scene graph must contain 3-12 authored objects")
    camera = raw.get("camera")
    if not isinstance(camera, dict) or camera.get("move") not in {
        "push_in", "orbit", "tracking", "sweep", "crane", "static"
    } or camera.get("angle") not in {"low", "eye", "high", "top"}:
        raise ValueError("AI director returned an invalid camera plan")
    palette = raw.get("palette")
    if not isinstance(palette, dict):
        raise ValueError("AI director omitted its scene palette")
    clean_palette = {}
    for key in ("background", "key", "accent"):
        value = str(palette.get(key, ""))
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError(f"AI director returned an invalid {key} color")
        clean_palette[key] = value.lower()
    allowed_kinds = {"sphere", "cube", "cylinder", "torus", "cone", "icosphere", "ring", "line"}
    allowed_actions = {"rise", "fall", "rotate", "orbit", "pulse", "travel_x", "travel_y", "reveal", "none"}
    seen: set[str] = set()
    clean_objects = []
    for index, item in enumerate(objects):
        if not isinstance(item, dict):
            raise ValueError(f"object {index} is not an object")
        object_id = str(item.get("id", "")).strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,31}", object_id) or object_id in seen:
            raise ValueError("AI scene graph object IDs must be unique snake_case identifiers")
        seen.add(object_id)
        kind, action = str(item.get("kind", "")), str(item.get("action", ""))
        if kind not in allowed_kinds or action not in allowed_actions:
            raise ValueError(f"unsupported object kind or action for {object_id}")
        material = str(item.get("material", ""))
        if material not in {"key", "accent", "neutral", "dark"}:
            raise ValueError(f"unsupported material role for {object_id}")
        amount = float(item.get("action_amount", 0))
        if not math.isfinite(amount) or not -4 <= amount <= 4:
            raise ValueError(f"invalid action amount for {object_id}")
        clean_objects.append({
            "id": object_id, "kind": kind,
            "role": str(item.get("role", ""))[:180],
            "position": _bounded_vector(item.get("position"), low=-6, high=6, label="position"),
            "scale": _bounded_vector(item.get("scale"), low=0.05, high=4, label="scale"),
            "rotation": _bounded_vector(item.get("rotation"), low=-6.28, high=6.28, label="rotation"),
            "material": material, "action": action, "action_amount": amount,
        })
    relationships = raw.get("relationships", [])
    if not isinstance(relationships, list) or len(relationships) > 24:
        raise ValueError("invalid scene relationships")
    clean_relationships = []
    for relation in relationships:
        if not isinstance(relation, dict):
            raise ValueError("relationship must be an object")
        source, target, kind = str(relation.get("from", "")), str(relation.get("to", "")), str(relation.get("kind", ""))
        if source not in seen or target not in seen or source == target or kind not in {"connect", "orbit", "point_to"}:
            raise ValueError("relationship references invalid objects")
        clean_relationships.append({"from": source, "to": target, "kind": kind})
    return {
        "visual_thesis": str(raw.get("visual_thesis", "")).strip()[:500],
        "camera": {"move": camera["move"], "angle": camera["angle"], "focus": str(camera.get("focus", ""))[:80]},
        "palette": clean_palette, "objects": clean_objects, "relationships": clean_relationships,
    }


def _parse_json(text: str) -> Any:
    value = text.strip()
    value = re.sub(r"^\x60\x60\x60(?:json)?\s*|\s*\x60\x60\x60$", "", value, flags=re.I)
    start, end = value.find("{"), value.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("AI director returned no JSON scene graph")
    return json.loads(value[start:end + 1])


def direct_scene(*, narration: str, visual_brief: str, overlay: str = "",
                 duration_seconds: float = 4.0, story_context: str = "",
                 previous_visual_theses: list[str] | None = None) -> dict[str, Any]:
    """Ask an LLM to direct one shot and validate every executable instruction."""
    narration = str(narration).strip()
    visual_brief = str(visual_brief).strip()
    if not narration or not visual_brief:
        raise ValueError("AI director requires narration and a specific visual brief")
    if not math.isfinite(float(duration_seconds)) or not 0.5 <= float(duration_seconds) <= 60:
        raise ValueError("invalid scene duration")
    prompt = json.dumps({
        "narration_exact": narration,
        "visual_brief": visual_brief,
        "persian_overlay_exact": overlay,
        "duration_seconds": float(duration_seconds),
        "story_context": str(story_context)[:4000],
        "previous_visual_theses_to_avoid_repeating": (previous_visual_theses or [])[-8:],
        "task": "Design a new scene graph that literally communicates this narration. Do not alter the narration or overlay.",
    }, ensure_ascii=False)
    response, provider = generate_text(
        SYSTEM, prompt, max_tokens=1800, temperature=0.55, json_mode=True, timeout=180,
    )
    try:
        plan = validate_scene_graph(_parse_json(response))
    except (ValueError, TypeError, json.JSONDecodeError) as first_error:
        # Providers occasionally emit almost-JSON despite json_mode. Ask once
        # for a strict repair; never silently guess or render malformed data.
        repair_prompt = json.dumps({
            "task": "Repair the supplied response into one valid JSON object matching the scene graph schema. Preserve its intended visual meaning. Output JSON only, with all commas, quotes, arrays and numbers valid.",
            "validation_error": str(first_error),
            "malformed_response": str(response)[:12000],
            "narration_exact": narration,
            "visual_brief": visual_brief,
        }, ensure_ascii=False)
        repaired, repair_provider = generate_text(
            SYSTEM, repair_prompt, max_tokens=1800, temperature=0.0,
            json_mode=True, timeout=180,
        )
        plan = validate_scene_graph(_parse_json(repaired))
        provider = f"{provider}+json-repair:{repair_provider}"
    # A separate editorial pass checks the authored composition against the
    # literal sentence before any expensive Blender frames are rendered.
    critique_system = (
        "You are an independent semantic accuracy editor, not an art director. Compare the "
        "exact narration with the proposed 3D scene graph. Reject ONLY a factual error, a "
        "wrong subject, a missing essential mechanism, or a composition that plainly depicts "
        "a different meaning. Do NOT reject for subjective aesthetic preferences, object size "
        "preferences, optional realism, camera framing suggestions, or alternative design ideas. "
        "If the main subject, action and relationships communicate the narration, verdict MUST "
        "be pass with score >= 85; list optional polish only as non-blocking notes. "
        "Return ONLY JSON: {score: integer 0-100, verdict: 'pass'|'revise', issues: [strings], "
        "revision_brief: string}. Only semantic/factual mismatches justify revise."
    )
    critique_prompt = json.dumps({
        "narration_exact": narration, "visual_brief": visual_brief,
        "visual_thesis": plan["visual_thesis"], "camera": plan["camera"],
        "objects": plan["objects"], "relationships": plan["relationships"],
    }, ensure_ascii=False)
    critique_raw, critique_provider = generate_text(
        critique_system, critique_prompt, max_tokens=500, temperature=0.1,
        json_mode=True, timeout=120,
    )
    critique = _parse_json(critique_raw)
    score = int(critique.get("score", 0))
    if critique.get("verdict") != "pass" or score < 80 or not isinstance(critique.get("issues"), list):
        raise ValueError(
            "AI scene director rejected its own semantic composition; revise before rendering: "
            + "; ".join(str(issue) for issue in critique.get("issues", [])[:4])
        )
    plan.update({
        "motif": "ai_scene", "matched_by": "semantic_ai_director",
        "camera_style": plan["camera"]["move"], "provider": provider,
        "critic_provider": critique_provider, "semantic_review_score": score,
        "semantic_review": critique,
        "narration_exact": narration, "visual_brief": visual_brief,
        "duration_seconds": float(duration_seconds),
    })
    return plan
