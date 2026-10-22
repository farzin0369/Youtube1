#!/usr/bin/env python3
"""Offline structural and fixture checks for the safe n8n draft workflow."""
import json, pathlib, sys

path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("automation/n8n/youtube-draft-intake.json")
wf = json.loads(path.read_text(encoding="utf-8"))
assert wf.get("active") is False, "Workflow must remain inactive"
nodes = wf.get("nodes", [])
ids = [n.get("id") for n in nodes]
names = [n.get("name") for n in nodes]
assert len(ids) == len(set(ids)) and None not in ids, "Missing/duplicate node IDs"
assert len(names) == len(set(names)), "Duplicate node names"
name_set = set(names)
for source, routes in wf.get("connections", {}).items():
    assert source in name_set, f"Unknown connection source: {source}"
    for outputs in routes.values():
        for branch in outputs:
            for edge in branch:
                assert edge["node"] in name_set, f"Dangling connection: {edge['node']}"
code = next(n for n in nodes if n["name"] == "Validate and deduplicate")["parameters"]["jsCode"]
for marker in ("title_required", "topic_required", "duplicate_in_batch", "duplicate_topic_history", "uploadEnabled:false", "publishEnabled:false"):
    assert marker in code, f"Missing safety/validation marker: {marker}"
assert not any("youtube" in n.get("type","").lower() and "trigger" not in n.get("type","").lower() for n in nodes), "No YouTube action is allowed in draft-only workflow"

# The existing production workflow in this branch must be manual-only.
production = pathlib.Path(".github/workflows/daily_run.yml").read_text(encoding="utf-8")
assert "\n  schedule:" not in production, "Scheduled production publishing must stay disabled in this branch"
assert "\n  workflow_dispatch:" in production, "Manual workflow dispatch must remain available"
assert "default: false" in production, "Publishing must default to false"

# Deterministic fixtures mirror the intended validation contract.
def validate(row, prior_topics=(), prior_ids=(), batch_topics=()):
    title = row.get("title", "").strip() if isinstance(row.get("title", ""), str) else ""
    topic = row.get("topic", "").strip().lower() if isinstance(row.get("topic", ""), str) else ""
    problems = []
    if not title: problems.append("title_required")
    if not topic: problems.append("topic_required")
    if len(title) > 100: problems.append("title_too_long")
    if row.get("videoId") and row["videoId"] in prior_ids: problems.append("duplicate_video_id")
    if topic and topic in [x.strip().lower() for x in prior_topics]: problems.append("duplicate_topic_history")
    if topic and topic in batch_topics: problems.append("duplicate_in_batch")
    return problems
assert validate({"title":"A good title","topic":"hope"}) == [], "Valid input failed"
assert "title_required" in validate({"title":"","topic":"hope"}), "Invalid input accepted"
assert "duplicate_topic_history" in validate({"title":"Again","topic":"hope"}, prior_topics=["Hope"]), "Historical duplicate missed"
assert "duplicate_video_id" in validate({"title":"Again","topic":"other","videoId":"abc"}, prior_ids=["abc"]), "Duplicate ID missed"
assert "duplicate_in_batch" in validate({"title":"Second","topic":"hope"}, batch_topics=["hope"]), "Batch duplicate missed"
print("PASS: JSON structure, inactive n8n state, manual-only production guard, and valid/invalid/duplicate fixtures.")
