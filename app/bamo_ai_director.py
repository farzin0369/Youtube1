"""Semantic AI film director: turns narration into a validated, executable 3D scene graph.

The LLM authors the visual composition per scene. Blender is the deterministic renderer,
not the creative decision maker. Unknown subjects are planned compositionally rather than
mapped to a finite list of keyword motifs. Provider failure is fail-closed.
"""
from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from app.llm_provider import generate_text

LOGGER = logging.getLogger(__name__)

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
Choose a camera move that is not already listed in previous_camera_moves when one of
the six legal moves is still unused.
""".strip()

CAMERA_MOVES = ("push_in", "orbit", "tracking", "sweep", "crane", "static")
_KIND_ALIASES = {
    "ball": "sphere", "orb": "sphere", "uv_sphere": "sphere", "planet": "sphere", "star": "sphere",
    "box": "cube", "cuboid": "cube", "block": "cube",
    "cyl": "cylinder", "tube": "cylinder", "rod": "cylinder", "bond": "cylinder",
    "donut": "torus", "doughnut": "torus", "ellipse": "torus",
    "pyramid": "cone",
    "ico": "icosphere", "polyhedron": "icosphere",
    "curve": "line", "path": "line", "segment": "line", "axis": "line", "ray": "line",
}
_ACTION_ALIASES = {
    "spin": "rotate", "spinning": "rotate", "yaw": "rotate",
    "up": "rise", "ascend": "rise", "lift": "rise",
    "down": "fall", "descend": "fall", "drop": "fall",
    "move_x": "travel_x", "slide_x": "travel_x", "translate_x": "travel_x",
    "move_y": "travel_y", "slide_y": "travel_y",
    "scale": "pulse", "breathe": "pulse", "throb": "pulse",
    "appear": "reveal", "fade_in": "reveal", "grow": "reveal",
    "idle": "none", "static": "none", "still": "none", "": "none",
}
_MOVE_ALIASES = {
    "dolly": "push_in", "dolly_in": "push_in", "zoom": "push_in", "push": "push_in",
    "orbit_around": "orbit", "arc": "orbit",
    "track": "tracking", "follow": "tracking",
    "pan": "sweep", "lateral": "sweep",
    "crane_up": "crane", "pedestal": "crane", "rise": "crane",
    "locked": "static", "fixed": "static", "hold": "static",
}
_ANGLE_ALIASES = {
    "bird": "top", "birds_eye": "top", "overhead": "top", "aerial": "top",
    "worm": "low", "hero": "low", "ground": "low",
    "medium": "eye", "level": "eye", "neutral": "eye",
}
_DOMAIN_HINTS = (
    (("ستاره", "کیهان", "کهکشان", "مدار", "آسمان شب", "star", "orbit", "galaxy", "cosmos", "olbers", "اولبرس", "انبساط"),
     "astronomy: show stars, nested shells or orbits, scale, and expanding space. Do not substitute generic floating cubes."),
    (("موج", "تداخل", "wave", "interference", "نوسان"),
     "wave physics: two distinct sources, expanding wavefronts, and a visible interference relationship."),
    (("مولکول", "اتم", "پیوند", "شیمی", "molecule", "atom", "bond", "chemistry"),
     "chemistry: atoms are spheres, bonds are connectors between them, arranged as a readable 3D structure."),
    (("ریاضی", "بیضی", "منحنی", "اثبات", "هندسه", "ellipse", "geometry", "equation", "math"),
     "mathematics: curves, ellipses, axes and construction lines that demonstrate the stated relation."),
    (("نورون", "سیناپس", "مغز", "عصب", "neural", "synapse", "brain"),
     "neuroscience: branching nodes linked by connectors, with a pulse traveling along the links."),
    (("تاریخ", "معماری", "باستان", "امپراتوری", "ancient", "architecture", "empire"),
     "history: a concrete place or object from the sentence, with depth and a purposeful camera move."),
)


def _bounded_vector(value: Any, *, low: float, high: float, label: str) -> list[float]:
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


def _clamp_number(value: Any, low: float, high: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite number")
    return max(low, min(high, number))


def _slug_id(raw: Any, index: int) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", str(raw or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    if not text or not text[0].isalpha():
        text = f"obj_{text}".strip("_")
    text = text[:32].strip("_")
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,31}", text):
        text = f"obj_{index:02d}"
    return text


def _normalize_color(value: Any) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"[0-9a-fA-F]{6}", text):
        text = "#" + text
    if re.fullmatch(r"#[0-9a-fA-F]{3}", text):
        text = "#" + "".join(ch * 2 for ch in text[1:])
    return text.lower()


def _domain_guidance(narration: str, visual_brief: str) -> list[str]:
    text = f"{narration} {visual_brief}".lower()
    hints = []
    for keys, hint in _DOMAIN_HINTS:
        if any(key in text for key in keys):
            hints.append(hint)
    return hints[:2]


def normalize_scene_graph(raw: Any) -> Any:
    """Clamp executable numbers and aliases into the renderer grammar.

    Structural inventions are not filled in: missing objects, illegal kinds that
    have no alias, and broken relationships still fail closed in validation.
    """
    if not isinstance(raw, dict):
        return raw
    graph = dict(raw)
    camera = dict(graph.get("camera") or {}) if isinstance(graph.get("camera"), dict) else {}
    move = str(camera.get("move", "")).strip().lower()
    angle = str(camera.get("angle", "")).strip().lower()
    camera["move"] = _MOVE_ALIASES.get(move, move)
    camera["angle"] = _ANGLE_ALIASES.get(angle, angle)
    graph["camera"] = camera
    palette = dict(graph.get("palette") or {}) if isinstance(graph.get("palette"), dict) else {}
    for key in ("background", "key", "accent"):
        if key in palette:
            palette[key] = _normalize_color(palette.get(key))
    graph["palette"] = palette
    objects = graph.get("objects")
    if isinstance(objects, list) and len(objects) > 12:
        objects = objects[:12]
    clean_objects = []
    id_map: dict[str, str] = {}
    seen: set[str] = set()
    if isinstance(objects, list):
        for index, item in enumerate(objects):
            if not isinstance(item, dict):
                clean_objects.append(item)
                continue
            obj = dict(item)
            original = str(obj.get("id", ""))
            object_id = _slug_id(original, index)
            if object_id in seen:
                object_id = _slug_id(f"{object_id}_{index}", index)
            seen.add(object_id)
            if original:
                id_map[original] = object_id
            obj["id"] = object_id
            kind = str(obj.get("kind", "")).strip().lower()
            obj["kind"] = _KIND_ALIASES.get(kind, kind)
            action = str(obj.get("action", "none")).strip().lower()
            obj["action"] = _ACTION_ALIASES.get(action, action)
            material = str(obj.get("material", "")).strip().lower()
            if material in {"primary", "main", "hero"}:
                material = "key"
            elif material in {"secondary", "highlight"}:
                material = "accent"
            elif material in {"metal", "glass", "stone", "white", "gray", "grey"}:
                material = "neutral"
            elif material in {"shadow", "black"}:
                material = "dark"
            obj["material"] = material
            for label, low, high, default in (
                ("position", -6.0, 6.0, [0.0, 0.0, 1.0]),
                ("scale", 0.05, 4.0, [1.0, 1.0, 1.0]),
                ("rotation", -6.28, 6.28, [0.0, 0.0, 0.0]),
            ):
                value = obj.get(label)
                if isinstance(value, list) and len(value) == 3:
                    try:
                        obj[label] = [_clamp_number(component, low, high) for component in value]
                    except (TypeError, ValueError):
                        obj[label] = list(default)
                else:
                    obj[label] = list(default)
                else:
                    obj[label] = list(default)
            if "action_amount" in obj:
                try:
                    obj["action_amount"] = _clamp_number(obj.get("action_amount"), -4.0, 4.0)
                except (TypeError, ValueError):
                    pass
            clean_objects.append(obj)
        graph["objects"] = clean_objects
    relationships = graph.get("relationships")
    if isinstance(relationships, list):
        rewritten = []
        for relation in relationships:
            if not isinstance(relation, dict):
                rewritten.append(relation)
                continue
            rel = dict(relation)
            rel["from"] = id_map.get(str(rel.get("from", "")), str(rel.get("from", "")))
            rel["to"] = id_map.get(str(rel.get("to", "")), str(rel.get("to", "")))
            kind = str(rel.get("kind", "")).strip().lower()
            if kind in {"bond", "link", "connector", "edge"}:
                kind = "connect"
            elif kind in {"circle", "revolve"}:
                kind = "orbit"
            elif kind in {"aim", "look_at", "arrow"}:
                kind = "point_to"
            rel["kind"] = kind
            # Local models sometimes refer to a pre-normalized or stale object ID.
            # Keep the executable graph, but discard only unusable edges; object
            # validation below remains strict and never invents missing objects.
            if (
                rel["from"] in seen
                and rel["to"] in seen
                and rel["from"] != rel["to"]
                and kind in {"connect", "orbit", "point_to"}
            ):
                rewritten.append(rel)
        graph["relationships"] = rewritten
    return graph


def validate_scene_graph(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("AI director response must be a JSON object")
    objects = raw.get("objects")
    if not isinstance(objects, list) or not 3 <= len(objects) <= 12:
        raise ValueError("AI scene graph must contain 3-12 authored objects")
    camera = raw.get("camera")
    if not isinstance(camera, dict) or camera.get("move") not in set(CAMERA_MOVES) or camera.get("angle") not in {"low", "eye", "high", "top"}:
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
            continue
        source, target, kind = str(relation.get("from", "")), str(relation.get("to", "")), str(relation.get("kind", ""))
        if source not in seen or target not in seen or source == target or kind not in {"connect", "orbit", "point_to"}:
            continue
        clean_relationships.append({"from": source, "to": target, "kind": kind})
    return {
        "visual_thesis": str(raw.get("visual_thesis", "")).strip()[:500],
        "camera": {"move": camera["move"], "angle": camera["angle"], "focus": str(camera.get("focus", ""))[:80]},
        "palette": clean_palette, "objects": clean_objects, "relationships": clean_relationships,
    }


def _repair_json_text(value: str) -> str:
    text = value.replace("\ufeff", "").replace("“", "\"").replace("”", "\"").replace("’", "'")
    text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text, flags=re.I)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(^|\n)\s*//.*?$", "", text, flags=re.M)
    text = re.sub(r"\bTrue\b", "true", text)
    text = re.sub(r"\bFalse\b", "false", text)
    text = re.sub(r"\bNone\b", "null", text)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    # Missing commas are the failure seen in Actions run 41693079551
    # ("Expecting ',' delimiter") after Qwen emitted otherwise usable JSON.
    text = re.sub(r'([}\]0-9"])\s*\n(\s*")', r"\1,\n\2", text)
    text = re.sub(r'([}\]])(\s*[{\[])', r"\1,\2", text)
    text = re.sub(r'([}\]"])\s+(")', r"\1, \2", text)
    return text


def _extract_json_object(value: str) -> str:
    start = value.find("{")
    if start < 0:
        raise ValueError("AI director returned no JSON scene graph")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(value)):
        char = value[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return value[start:index + 1]
    truncated = re.sub(r",\s*$", "", value[start:].rstrip())
    truncated += "]" * max(0, truncated.count("[") - truncated.count("]"))
    truncated += "}" * max(0, truncated.count("{") - truncated.count("}"))
    return truncated


def _parse_json(text: str) -> Any:
    repaired = _repair_json_text(str(text or ""))
    blob = _extract_json_object(repaired)
    candidates = [blob, _repair_json_text(blob)]
    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
    raise last_error or ValueError("AI director returned no JSON scene graph")


def _load_plan(text: str) -> dict[str, Any]:
    return validate_scene_graph(normalize_scene_graph(_parse_json(text)))


def ensure_distinct_camera_moves(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the model's first choice, then assign an unused legal move to duplicates."""
    used: set[str] = set()
    for plan in plans:
        camera = plan.get("camera")
        if not isinstance(camera, dict):
            continue
        move = str(camera.get("move") or "")
        if move in used:
            for candidate in CAMERA_MOVES:
                if candidate not in used:
                    camera["move"] = candidate
                    plan["camera_diversified_from"] = move
                    move = candidate
                    break
        used.add(move)
        plan["camera_style"] = move
    return plans


def _semantic_critique(narration: str, visual_brief: str, plan: dict[str, Any]) -> tuple[dict[str, Any], str]:
    critique_system = (
        "You are an independent semantic accuracy editor, not an art director. Compare the "
        "exact narration with the proposed 3D scene graph. Reject ONLY a factual error, a "
        "wrong subject, a missing essential mechanism, or a composition that plainly depicts "
        "a different meaning. Do NOT reject for subjective aesthetic preferences, object size "
        "preferences, optional realism, camera framing suggestions, or alternative design ideas. "
        "If the main subject, action and relationships communicate the narration, verdict MUST "
        "be pass with score >= 85; list optional polish only as non-blocking notes. "
        "Return ONLY JSON: {\"score\": integer 0-100, \"verdict\": \"pass\"|\"revise\", \"issues\": [strings], "
        "\"revision_brief\": string}. Only semantic/factual mismatches justify revise."
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
    try:
        critique = _critique_payload(critique_raw)
    except (ValueError, TypeError, json.JSONDecodeError) as critique_error:
        LOGGER.warning("semantic critic returned non-JSON (%s)", critique_error)
        repaired_critique, critique_provider = generate_text(
            critique_system,
            json.dumps({
                "task": "Return only the critic JSON object. Required keys: score, verdict, issues, revision_brief.",
                "validation_error": str(critique_error),
                "malformed_response": str(critique_raw)[:4000],
            }, ensure_ascii=False),
            max_tokens=500, temperature=0.0, json_mode=True, timeout=120,
        )
        critique = _critique_payload(repaired_critique)
        critique_provider = f"{critique_provider}+json-repair"
    return critique, critique_provider


def _critique_payload(raw: str) -> dict[str, Any]:
    critique = _parse_json(raw)
    if not isinstance(critique, dict):
        raise ValueError("semantic critic did not return a JSON object")
    try:
        score = int(float(critique.get("score", 0)))
    except (TypeError, ValueError):
        score = 0
    critique["score"] = score
    issues = critique.get("issues", [])
    if issues is None:
        issues = []
    elif not isinstance(issues, list):
        issues = [str(issues)]
    critique["issues"] = [str(issue) for issue in issues]
    return critique


def _critique_accepts(critique: dict[str, Any]) -> bool:
    return critique.get("verdict") == "pass" and int(critique.get("score", 0)) >= 85


def direct_scene(*, narration: str, visual_brief: str, overlay: str = "",
                 duration_seconds: float = 4.0, story_context: str = "",
                 previous_visual_theses: list[str] | None = None,
                 previous_camera_moves: list[str] | None = None) -> dict[str, Any]:
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
        "domain_guidance": _domain_guidance(narration, visual_brief),
        "previous_visual_theses_to_avoid_repeating": (previous_visual_theses or [])[-8:],
        "previous_camera_moves": (previous_camera_moves or [])[-8:],
        "task": "Design a new scene graph that literally communicates this narration. Do not alter the narration or overlay. Return one JSON object with every required comma.",
    }, ensure_ascii=False)
    response, provider = generate_text(
        SYSTEM, prompt, max_tokens=1800, temperature=0.2, json_mode=True, timeout=180,
    )
    try:
        plan = _load_plan(response)
    except (ValueError, TypeError, json.JSONDecodeError) as first_error:
        LOGGER.warning(
            "AI director output was not executable (%s). Excerpt: %s",
            first_error, str(response)[:600].replace("\n", " "),
        )
        # Providers occasionally emit almost-JSON despite json_mode. Ask once
        # for a strict repair; never silently invent missing objects.
        repair_prompt = json.dumps({
            "task": "Repair the supplied response into one valid JSON object matching the scene graph schema. Preserve its intended visual meaning. Output JSON only. Keep action_amount within -4..4, positions within -6..6, scales within 0.05..4, and rotations within -6.28..6.28.",
            "validation_error": str(first_error),
            "malformed_response": str(response)[:12000],
            "narration_exact": narration,
            "visual_brief": visual_brief,
        }, ensure_ascii=False)
        repaired, repair_provider = generate_text(
            SYSTEM, repair_prompt, max_tokens=1800, temperature=0.0,
            json_mode=True, timeout=180,
        )
        try:
            plan = _load_plan(repaired)
        except (ValueError, TypeError, json.JSONDecodeError) as repair_error:
            LOGGER.warning(
                "AI director repair was still not executable (%s). Excerpt: %s",
                repair_error, str(repaired)[:600].replace("\n", " "),
            )
            raise
        provider = f"{provider}+json-repair:{repair_provider}"
    critique, critique_provider = _semantic_critique(narration, visual_brief, plan)
    if not _critique_accepts(critique):
        revision_prompt = json.dumps({
            "task": "Revise the scene graph so it literally depicts the narration. Keep the schema. Do not change the narration.",
            "narration_exact": narration,
            "visual_brief": visual_brief,
            "critic_score": critique.get("score"),
            "critic_issues": critique.get("issues"),
            "revision_brief": critique.get("revision_brief", ""),
            "previous_scene_graph": plan,
        }, ensure_ascii=False)
        revised, revision_provider = generate_text(
            SYSTEM, revision_prompt, max_tokens=1800, temperature=0.2,
            json_mode=True, timeout=180,
        )
        plan = _load_plan(revised)
        provider = f"{provider}+semantic-revision:{revision_provider}"
        critique, critique_provider = _semantic_critique(narration, visual_brief, plan)
        if not _critique_accepts(critique):
            raise ValueError(
                "AI scene director rejected its own semantic composition; revise before rendering: "
                + "; ".join(str(issue) for issue in critique.get("issues", [])[:4])
            )
    score = int(critique.get("score", 0))
    plan.update({
        "motif": "ai_scene", "matched_by": "semantic_ai_director",
        "camera_style": plan["camera"]["move"], "provider": provider,
        "critic_provider": critique_provider, "semantic_review_score": score,
        "semantic_review": critique,
        "narration_exact": narration, "visual_brief": visual_brief,
        "duration_seconds": float(duration_seconds),
    })
    return plan
