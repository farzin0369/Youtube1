# BAMO repository audit (2026-11-05)

Scope: static reading of code and workflows via the GitHub API. Nothing was executed and no output video was inspected, so runtime claims below are unverified.

## Findings
1. Default-branch README describes the ImamAli110 spiritual channel (one 18:00 Tehran slot), not BAMO's six-slot multi-domain plan.
2. About 100 branches. Current BAMO work lives on `fix/bamo-cpu-render-recovery-20261104` and `feat/bamo-visual-review-and-scene-fidelity`.
3. `app/bamo_motion_engine.py` (Pillow software 3D): every scene shares one cube, three spheres and two rings; `bamo_scene_director.py` maps ~8 keyword motifs. This is the repeated-template pattern the owner forbids.
4. `app/bamo_ai_director.py`: LLM authors a validated scene graph (3-12 primitives, camera, palette) with a semantic critic; Blender renders it. Better direction, but the grammar is primitives only (sphere, cube, cylinder, torus, cone, icosphere, ring, line), so characters, buildings and people cannot be depicted literally.
5. `app/bamo_agent_council.py`: the "11 agents" are 11 independent reviewers, each pinned to a distinct model ID with its own API key (`config/bamo_agent_models.json`). Production roles (research, script, TTS, render, SEO) are not agents. This conflicts with the no-paid-API requirement unless every pinned model is free.
6. `bamo_autopilot_continuous.yml` runs every 6 hours, applies patches via `scripts/apply_quality_patches.py` and pushes directly to a feature branch; most steps end with `|| true`. This violates test-before-merge and rollback rules.
7. Per workflow comments (unverified): a Blender proof run took about 56 minutes at 40% resolution, 24 samples, 2 threads, ~12 MB.
8. Duplicate protection (`app/youtube_history.py`) is solid and is reused by the new planner.

## Added in this branch
- `config/bamo_domains.json`: eight domains, weights, balance and similarity rules, per-domain narrative, visual grammar and verification policy.
- `config/bamo_schedule.json`: six Tehran slots. The long/short split is a default awaiting owner confirmation.
- `config/bamo_topic_bank.json`: seed ideas, offline fallback only.
- `app/bamo_topic_planner.py`, `scripts/bamo_plan_day.py`, `tests/test_bamo_topic_planner.py`.

## Not done yet
Scene grammar extension, agent-to-pipeline wiring, free CPU Persian TTS evaluation, scheduled workflow, and the three proof videos.
