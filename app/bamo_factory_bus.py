"""Shared job bus for the BAMO content factory (11 operational agents).

Agents exchange structured jobs via state/factory/queue.jsonl and
state/factory/jobs/<id>.json. This is real coordination state, not decorative
class names.

Agent IDs:
  research, trend, editorial, fact_checker, scriptwriter, art_director,
  motion_director, voice_audio, video_production, quality_assurance, operations
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT / "state" / "factory"
JOBS = FACTORY / "jobs"
QUEUE = FACTORY / "queue.jsonl"
HISTORY = FACTORY / "content_history.json"

AGENT_IDS = (
    "research",
    "trend",
    "editorial",
    "fact_checker",
    "scriptwriter",
    "art_director",
    "motion_director",
    "voice_audio",
    "video_production",
    "quality_assurance",
    "operations",
)


def _ensure() -> None:
    JOBS.mkdir(parents=True, exist_ok=True)
    FACTORY.mkdir(parents=True, exist_ok=True)
    if not HISTORY.is_file():
        HISTORY.write_text(json.dumps({"items": []}, ensure_ascii=False, indent=2), encoding="utf-8")


def new_job(topic_seed: str = "") -> dict[str, Any]:
    _ensure()
    job_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    job = {
        "id": job_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "created",
        "topic_seed": topic_seed,
        "topic": None,
        "script": None,
        "scenes": [],
        "scene_graphs": [],
        "audio_path": None,
        "video_path": None,
        "qa_score": None,
        "qa_breakdown": {},
        "agent_log": [],
        "errors": [],
        "publish": {"allowed": False, "youtube_id": None},
    }
    _save_job(job)
    with QUEUE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": job_id, "status": "created"}, ensure_ascii=False) + "\n")
    return job


def _save_job(job: dict[str, Any]) -> None:
    _ensure()
    path = JOBS / f"{job['id']}.json"
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")


def load_job(job_id: str) -> dict[str, Any]:
    path = JOBS / f"{job_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def agent_note(job: dict[str, Any], agent_id: str, message: str, **extra: Any) -> dict[str, Any]:
    if agent_id not in AGENT_IDS:
        raise ValueError(f"unknown agent: {agent_id}")
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "agent": agent_id,
        "message": message,
        **extra,
    }
    job.setdefault("agent_log", []).append(entry)
    _save_job(job)
    return job


def set_status(job: dict[str, Any], status: str) -> dict[str, Any]:
    job["status"] = status
    job["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _save_job(job)
    with QUEUE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": job["id"], "status": status}, ensure_ascii=False) + "\n")
    return job


def content_history() -> list[dict[str, Any]]:
    _ensure()
    data = json.loads(HISTORY.read_text(encoding="utf-8"))
    return list(data.get("items") or [])


def remember_content(item: dict[str, Any]) -> None:
    _ensure()
    data = json.loads(HISTORY.read_text(encoding="utf-8"))
    items = list(data.get("items") or [])
    items.append({**item, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    data["items"] = items[-500:]
    HISTORY.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_duplicate_topic(topic: str, threshold_tokens: int = 3) -> bool:
    tokens = {t for t in topic.lower().split() if len(t) > 2}
    if not tokens:
        return False
    for row in content_history():
        prev = str(row.get("topic") or row.get("title") or "")
        prev_tokens = {t for t in prev.lower().split() if len(t) > 2}
        if len(tokens & prev_tokens) >= threshold_tokens:
            return True
    return False
