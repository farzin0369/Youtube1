"""Transparent editorial ranking heuristics; never a guarantee of audience performance."""
from __future__ import annotations

import re
from typing import Any

QUESTION_WORDS = {"why", "how", "what", "could", "can", "does", "is", "are", "would", "when"}
VISUAL_WORDS = {"space", "black hole", "quantum", "molecule", "orbit", "vector", "time", "light", "atom", "infinity", "planet", "wave", "energy", "dna"}
TRUSTED_SOURCE_NAMES = {"openalex", "arxiv", "wikidata", "nasa", "cern", "nature", "science"}


def rank_idea(record: dict[str, Any]) -> dict[str, Any]:
    """Return an explainable 0-100 editorial priority score with component reasons."""
    title = str(record.get("title", "")).strip()
    hook = str(record.get("hook", "")).strip()
    plain = str(record.get("plain_explanation", "")).strip()
    tags = record.get("tags", [])
    tags = [str(t).casefold() for t in tags] if isinstance(tags, list) else []
    sources = record.get("sources", [])
    sources = [s for s in sources if isinstance(s, dict)] if isinstance(sources, list) else []
    blob = (title + " " + hook + " " + " ".join(tags)).casefold()

    components: dict[str, int] = {}
    components["question_appeal"] = 20 if title.endswith("?") else (12 if any(title.casefold().startswith(w + " ") for w in QUESTION_WORDS) else 6)
    components["hook"] = 15 if len(hook) >= 45 and ("?" in hook or any(w in hook.casefold() for w in ("imagine", "what if", "meet", "remove"))) else (8 if hook else 0)
    components["visual_potential"] = min(20, 5 + 5 * sum(1 for term in VISUAL_WORDS if term in blob))
    components["two_layer_explanation"] = 10 if plain and record.get("deeper_angle") else (5 if plain or record.get("deeper_angle") else 0)
    credible = sum(1 for source in sources if any(name in str(source.get("provider", source.get("source_name", ""))).casefold() for name in TRUSTED_SOURCE_NAMES) or source.get("doi") or source.get("url"))
    components["source_trail"] = min(15, credible * 5)
    evidence = str(record.get("evidence_status", "")).casefold()
    components["evidence_clarity"] = 10 if evidence and evidence not in {"unknown", "unverified"} else 4
    components["production_readiness"] = 10 if record.get("visual_plan") and sources and record.get("workflow_status") in {"reviewed", "seed_reviewed", "ready_for_script"} else 4
    total = min(100, sum(components.values()))
    return {
        "id": record.get("id"),
        "title": title,
        "priority_score": total,
        "components": components,
        "review_required": evidence not in {"established_science", "established_science_with_interpretive_nuance", "established_science_with_nuance"},
        "note": "Editorial triage score only; not a prediction of views or scientific correctness.",
    }


def rank_ideas(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((rank_idea(record) for record in records), key=lambda item: (-item["priority_score"], item["title"]))
