"""Independent 11-agent editorial council for BAMO.

Each specialist receives the same immutable production package, a role-specific
system prompt, and its own bounded memory namespace. Reviews run independently;
no reviewer sees another review before submitting its verdict.
"""
from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.llm_provider import _chat_completions

LOGGER = logging.getLogger(__name__)

AGENTS: tuple[tuple[str, str], ...] = (
    ("trend_researcher", "Assess topic freshness, audience demand, whether the idea has a compelling reason to exist now, and whether it repeats or paraphrases a prior channel topic."),
    ("fact_checker", "Check factual, scientific, historical, and religious claims for accuracy, evidence, and unsupported certainty. Flag claims that need sources."),
    ("growth_strategist", "Assess audience fit, differentiation, shareability, and a credible path to strong organic reach."),
    ("scriptwriter", "Assess the opening hook, clarity, emotional arc, curiosity gaps, pacing, and payoff."),
    ("story_director", "Assess whether every scene advances the narration and whether the visual story is understandable without audio."),
    ("3d_motion_director", "Assess whether the scenes justify advanced 3D motion graphics, camera movement, depth, transitions, and visual variety."),
    ("audio_director", "Assess narration clarity, sound design, music balance, timing, and audio-to-scene synchronization."),
    ("editor", "Assess exact narration/on-screen-text/visual alignment, subtitle readability, pacing, and technical continuity."),
    ("youtube_seo", "Assess title, description, tags, hashtags, thumbnail text, search intent, and honest packaging."),
    ("retention_analyst", "Assess likely viewer drop-off points, first-second impact, rewatch value, and retention improvements."),
    ("independent_critic", "Act as an independent safety and integrity auditor. Compare the candidate with prior channel topics and scripts; block semantic duplicates and paraphrases. Find the strongest reason not to publish, especially unsafe, misleading, fabricated, copied, or policy-violating material."),
)

_REQUIRED = {"score", "verdict", "critical_issues", "major_issues", "minor_issues", "evidence", "suggestions", "confidence"}


def _json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^\```(?:json)?\s*|\s*\```$", "", text, flags=re.I)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("agent response did not contain a JSON object")
    value = json.loads(text[start:end + 1])
    if not isinstance(value, dict) or not _REQUIRED.issubset(value):
        raise ValueError("agent response is missing required review fields")
    return value


def _memory_for(agent_id: str, memory_dir: Path) -> str:
    path = memory_dir / f"{agent_id}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return json.dumps(value, ensure_ascii=False)[:2500]
    except (OSError, ValueError, TypeError):
        return "No prior specialist memory."


def _agent_model_registry() -> dict[str, dict[str, str]]:
    path = Path(__file__).resolve().parents[1] / "config" / "bamo_agent_models.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    agents = registry.get("agents")
    if not isinstance(agents, dict) or set(agents) != {agent_id for agent_id, _ in AGENTS}:
        raise RuntimeError("BAMO agent model registry must define exactly all eleven agents")
    model_ids = [item.get("model_id") for item in agents.values() if isinstance(item, dict)]
    if len(model_ids) != len(AGENTS) or len(set(model_ids)) != len(AGENTS):
        raise RuntimeError("BAMO requires eleven distinct, explicitly pinned model IDs")
    return agents


def _agent_completion(agent_id: str, system: str, prompt: str) -> tuple[str, str]:
    """Call the agent's pinned model; never silently fall back to a shared model."""
    registry = _agent_model_registry()
    item = registry[agent_id]
    base_url = str(item["base_url"]).rstrip("/")
    model_id = str(item["model_id"])
    provider = str(item["provider"])
    key_env = str(item["key_env"])
    api_key = (os.getenv(key_env) or "").strip()
    if not api_key:
        raise RuntimeError(f"missing required credential {key_env} for agent {agent_id}")
    raw = _chat_completions(
        base_url, api_key, model_id, system, prompt, max_tokens=900,
        temperature=0.15, json_mode=provider != "openrouter",
        timeout=float(os.getenv("BAMO_AGENT_TIMEOUT_SECONDS", "90")),
        max_attempts=1 if provider == "openrouter" else 3,
    )
    return raw, f"{provider}:{model_id}"


def _review_one(agent_id: str, specialty: str, package: dict[str, Any], memory_dir: Path) -> dict[str, Any]:
    system = (
        "You are an independent specialist on the BAMO YouTube quality council. "
        "Review only the supplied package. Be skeptical, specific, and evidence-led. "
        "Do not invent view predictions, sources, or facts. A million views cannot be guaranteed. "
        "Do not see or infer other reviewers' opinions. Return ONLY valid JSON with keys: "
        "score (integer 0-100), verdict (approve or revise), critical_issues (array), "
        "major_issues (array), minor_issues (array), evidence (array), suggestions (array), "
        "confidence (number 0-1). A critical factual, copyright, safety, or visual/audio mismatch "
        "must be listed as a critical issue and verdict revise."
    )
    prompt = json.dumps({
        "specialist_id": agent_id,
        "specialty": specialty,
        "production_package": package,
        "your_private_memory": _memory_for(agent_id, memory_dir),
        "instruction": "Review the complete package independently. Compare the candidate topic with recent_channel_topics and flag any same-idea paraphrase as a critical issue. Do not rewrite it. Return a reasoned JSON verdict.",
    }, ensure_ascii=False)
    raw, provider = _agent_completion(agent_id, system, prompt)
    result = _json_object(raw)
    score = int(result["score"])
    if not 0 <= score <= 100:
        raise ValueError("agent score must be between 0 and 100")
    verdict = str(result["verdict"]).lower()
    if verdict not in {"approve", "revise"}:
        raise ValueError("agent verdict must be approve or revise")
    for key in ("critical_issues", "major_issues", "minor_issues", "evidence", "suggestions"):
        if not isinstance(result[key], list):
            raise ValueError(f"{key} must be an array")
    confidence = float(result["confidence"])
    if not 0 <= confidence <= 1:
        raise ValueError("agent confidence must be between 0 and 1")
    review = {
        "agent_id": agent_id, "specialty": specialty, "provider_model": provider,
        "score": score, "verdict": verdict, "critical_issues": result["critical_issues"],
        "major_issues": result["major_issues"], "minor_issues": result["minor_issues"],
        "evidence": result["evidence"], "suggestions": result["suggestions"],
        "confidence": confidence,
    }
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / f"{agent_id}.json").write_text(
        json.dumps({"last_score": score, "last_verdict": verdict,
                    "recurring_issues": result["major_issues"][:5],
                    "useful_preferences": result["suggestions"][:5]},
                   ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return review


def review_with_council(
    content: dict[str, Any], *, render: dict[str, Any], media_qa: dict[str, Any],
    memory_dir: Path | None = None, history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run all 11 isolated reviews and fail closed unless the council passes."""
    package = {
        "title": content.get("title"), "topic": content.get("topic"),
        "script": content.get("script"), "description": content.get("description"),
        "tags": content.get("tags"), "thumbnail_text": content.get("thumbnail_text"),
        "scenes": content.get("scenes"),
        "recent_channel_topics": [
            {"title": row.get("title"), "topic": row.get("topic") or row.get("title")}
            for row in (history or []) if isinstance(row, dict)
        ][-200:],
        "render_evidence": {
            key: render.get(key) for key in (
                "visual_source", "visual_scene_count", "duration_seconds",
                "contains_synthetic_visuals", "camera_motion", "scene_visual_alignment_verified",
                "scene_visual_plans", "render_backend", "visual_quality_tier", "production_visuals_approved",
            ) if key in render
        }, "media_qa": media_qa,
    }
    root = memory_dir or Path(os.getenv("BAMO_AGENT_MEMORY_DIR", "state/agent_memory"))
    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    workers = max(1, min(5, int(os.getenv("BAMO_AGENT_CONCURRENCY", "4"))))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="bamo-agent") as pool:
        futures = {
            pool.submit(_review_one, agent_id, specialty, package, root): agent_id
            for agent_id, specialty in AGENTS
        }
        for future in as_completed(futures):
            agent_id = futures[future]
            try:
                results[agent_id] = future.result()
            except Exception as exc:
                errors[agent_id] = type(exc).__name__
                LOGGER.warning("BAMO council agent %s failed (%s)", agent_id, type(exc).__name__)

    ordered = [results[agent_id] for agent_id, _ in AGENTS if agent_id in results]
    critical = [
        {"agent_id": item["agent_id"], "issue": issue}
        for item in ordered for issue in item["critical_issues"]
    ]
    approvals = sum(item["verdict"] == "approve" for item in ordered)
    average_score = round(sum(item["score"] for item in ordered) / len(ordered), 1) if ordered else 0.0
    distinct_models = sorted({item["provider_model"] for item in ordered})
    passed = (
        len(ordered) == len(AGENTS) and not errors and not critical
        and approvals >= 9 and average_score >= 85
    )
    report = {
        "ok": passed, "agents_expected": len(AGENTS), "agents_completed": len(ordered),
        "approvals": approvals, "average_score": average_score,
        "distinct_provider_models_observed": len(distinct_models),
        "distinct_model_ids_observed": len({item["provider_model"].split(":", 1)[-1] for item in ordered}),
        "provider_models_observed": distinct_models,
        "independent_reviews": ordered, "agent_errors": errors,
        "critical_issues": critical,
        "gate": "PASS" if passed else "BLOCKED",
        "gate_policy": "11/11 reviews complete; at least 9 approvals; mean score >=85; zero critical issues",
    }
    if not passed:
        raise RuntimeError(
            "BAMO independent 11-agent council blocked publication "
            f"(completed={len(ordered)}/11, approvals={approvals}, "
            f"average={average_score}, critical={len(critical)}, errors={len(errors)})"
        )
    return report
