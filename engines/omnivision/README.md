# BAMO OMNIVISION Engine

A new, isolated foundation for a text-to-cinematic-video system. This branch does not replace the current production pipeline.

## What exists in v0.1

- A deterministic script-to-scene compiler with topic routing for astronomy, physics, mathematics, chemistry, history, comedy and a general fallback.
- Scene manifests bind each visual intent to its exact narration segment.
- Per-scene shot language, camera choreography, lighting intent, motion intent and transition cues.
- Weighted scene timecodes and machine-checkable planning tests.
- No paid API, GPU, or third-party runtime is required for the planning layer.

## Important limitation

This is the **planning/compiler foundation**, not yet a complete generative renderer. The current fallback topic classifier is lexical, not an LLM; music/SFX fields are integration contracts, not generated audio. A real production system still needs:
1. A pluggable semantic planner (local model first; hosted providers optional).
2. Asset and procedural-geometry generators with provenance/licensing checks.
3. A renderer adapter (Three.js/WebGL for procedural 3D; optional Blender for offline CPU rendering).
4. Persian TTS, phoneme/word alignment, subtitle layout and audio mixing.
5. Automated visual QA using sampled frames, black-frame/duplicate-shot checks and script-to-shot review.
6. Human approval gates until quality is demonstrated across unrelated topics.

## Run

```bash
cd engines/omnivision
npm test
echo "سیاه‌چاله نور را خم می‌کند. زمان نزدیک افق رویداد کندتر می‌گذرد." | npm run plan
```

The CLI writes a JSON scene manifest to stdout. Set `BAMO_PLAN_OUT` to save it.

## Architecture contract

Input script -> semantic analysis -> story beats -> scene graph manifest -> renderer -> voice and audio alignment -> compositing -> quality gates -> export.

Every scene carries its own narration, visual intent, world, subject, camera move, timing and transition. Renderers must reject missing scene subjects and must not silently substitute a generic loop/background.
