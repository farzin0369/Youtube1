# Science Idea Engine (isolated pilot)

This folder is an **additive, isolated** science-content subsystem. It does not import or modify the existing spiritual/OpenClaw/MoneyPrinterTurbo pipelines and it never uploads to YouTube.

## Goals
- Build a searchable, deduplicated idea bank that can grow toward 10,000+ records.
- Keep a public, evidence-oriented source trail for research ideas.
- Separate established science, open questions, hypotheses, and philosophical speculation.
- Design every idea for two audience layers: a plain-language explanation and an optional deeper layer.
- Keep generation and rendering separate: this pilot manages ideas and research metadata only.

## Quick start (Python 3.10+; standard library only)

From the repository root:

```bash
python -m science_engine.cli stats
python -m science_engine.cli search "black hole"
python -m science_engine.cli import-openalex --query "quantum entanglement" --limit 10
python -m science_engine.cli import-arxiv --query "quantum entanglement" --limit 10
python -m science_engine.cli rank --limit 20
python -m science_engine.batch_import --start-index 0 --topics-per-run 5 --limit-per-topic 50
```

Imported records are appended to `science_engine/ideas.jsonl`. Existing records are preserved. Deduplication uses DOI where available and normalized title otherwise. OpenAlex basic API usage is free to start; set `OPENALEX_API_KEY` as an environment variable for a higher quota. Never commit API keys.

## Growing the bank toward 10,000 candidates
`topics.json` contains 100 cross-disciplinary research queries. `batch_import.py` runs a small, resumable batch and saves after each topic, so a network or rate-limit failure does not discard completed work. Example: `python -m science_engine.batch_import --start-index 0 --topics-per-run 5 --limit-per-topic 50`. After the summary reports `next_start_index`, use that number for the next batch. Reaching 10,000 distinct records is a target, not a guarantee: API results overlap, some queries return fewer records, and source quality still needs review. Do not run a huge batch in GitHub Actions; run controlled batches in Colab or another session with network access.

## Current safeguards and limits
- OpenAlex and arXiv imports add **research candidates**, not finished scripts or verified conclusions.
- Ranking is an explainable editorial triage score (hook, question appeal, visual potential, source trail, evidence status, readiness); it is not a prediction of views.
- The arXiv API may return preprints; read the paper, check publication status and limitations before presenting claims as established.
- Run unit tests with `python -m unittest discover -s tests -p "test_science_engine.py"`.
- The Manim render workflow is manual-only to avoid repeatedly consuming hosted runner minutes. It does not publish to YouTube.

## Record fields
Each JSONL line contains a stable ID, question/title, subject tags, hook, accessible explanation, deeper angle, visual plan, source URLs, evidence status, and workflow status. Imported scholarly records are marked `research_candidate`; they are **not** automatically treated as video-ready facts.

## Quality and safety rules
1. A paper's existence is not proof that its claims are correct.
2. Distinguish peer-reviewed findings from preprints and philosophical arguments.
3. Don't describe metaphysics as experimentally established physics.
4. Verify claims against the cited source before scripting; preserve uncertainty.
5. No automatic publishing, no secret access, no changes to existing workflows.
6. This is a starter bank, not 10,000 finished scripts. Grow it in controlled, deduplicated batches and review quality before rendering.

## Next stage
Add source adapters (arXiv/Wikidata), a ranking/review queue, then a separate Manim/Blender pilot. Render a short local preview and inspect it before any upload workflow is considered.

## Persian visual pilot
The Persian prototype files are in `renderers/vector_pilot_fa.py`, `pilots/vector_addition_fa.txt`, and `pilots/vector_addition_fa.srt`. The isolated render workflow can create a Persian narrated preview using Manim and Edge TTS. This output is a prototype, not yet a validated final episode; check RTL shaping, narration/subtitle timing, and the actual MP4 before production.
