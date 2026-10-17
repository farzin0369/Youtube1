# ImamAli110 Video Studio — implementation plan

## Goal
Build a free/open-source, self-hostable browser-based workflow inspired by VideoGen's user experience, without copying its proprietary code or claiming access to paid models.

## Base selected
- Upstream: https://github.com/itsPremkumar/Automated-Video-Generator
- License: MIT (verified from upstream repository metadata).
- Why: existing web UI/server, script-to-scenes workflow, voiceover, captions, media retrieval, and FFmpeg/Remotion rendering. This is a closer fit for a usable browser studio than starting another renderer from scratch.

## First integration checkpoint
- A Colab notebook in this repository clones the upstream source into the current Colab runtime, installs its dependencies, checks GPU availability, and attempts to expose its web UI through Colab's port proxy.
- This is an isolated experiment: it does not alter main, existing OpenClaw/Money Printer Turbo/Azita code, schedules, secrets, or YouTube publishing.
- The notebook does not imply GPU acceleration is wired into every upstream stage. GPU detection is only a diagnostic.

## Non-negotiable quality requirements
- Persian-first UI/content and readable RTL overlays.
- Per-scene visual relevance must be checked; a filename/title keyword match is not sufficient proof of semantic relevance.
- Keep a strict quality gate; never turn a failed QC run into a pass.
- No automatic YouTube upload until a real output passes audio, subtitle, aspect-ratio, scene relevance, and render checks.
- No weak local LLM fallback presented as high quality.
- Preserve attribution and MIT license when adapting upstream code.

## Honest cost boundary
Open-source code is free, but cloud GPU time, storage, and high-end generative video inference are not guaranteed free or unlimited. The initial version uses free/open-source software and free media/TTS defaults where available; generated cinematic video models may require separate compute or service access.

## Next engineering steps
1. Run the notebook in the user's actual Colab session and record whether install/startup succeeds.
2. If successful, pin an upstream commit and vendor/fork only the required components on a dedicated branch.
3. Add Persian RTL presets, spiritual-story templates, a 9:16/16:9 selector, and a scene-by-scene approval/quality report.
4. Integrate the existing channel pipeline only after tests pass; keep YouTube publishing disabled until explicitly validated.
