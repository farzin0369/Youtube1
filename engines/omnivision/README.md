# BAMO OMNIVISION

A CPU-friendly text-to-scene compiler foundation for BAMO. It currently produces a deterministic narration-bound scene plan and a validated 3D scene graph; it is **not yet a finished video renderer or an AI semantic model**.

## Commands

- `npm test` — planner and scene-graph tests.
- `npm run plan -- "متن..." ` — JSON scene plan.
- `node src/graph-cli.mjs "متن..." ` — validated 3D scene graph.
- Pipe Persian narration through stdin when passing long scripts.

## Scene graph contract

Each narration beat carries a verbatim caption, semantic subject intent, environment, material palette, procedural support objects, animated hero transforms, a multi-keyframe camera path, and exact start/end timecodes. Validation rejects timeline gaps, overlaps, missing 3D/camera tracks, and caption mismatches.

## Current boundary

The graph is an intermediate representation. A production renderer still must consume it to generate frames, Persian TTS must provide measured word/phoneme timestamps, and a mux stage must align narration, music, SFX and captions before export. Heuristic topic classification is a fallback, not claimed deep semantic understanding.

## Audio-visual timing layer

`src/timeline.mjs` accepts measured word-boundary events from a TTS provider and maps each word to its authored scene. It creates phrase captions and per-word visual emphasis cues on one shared clock. It rejects non-monotonic timestamps, missing word events, scene/audio duration mismatch, and caption timing errors. This layer consumes measured timing; it does not fabricate phoneme alignment.
