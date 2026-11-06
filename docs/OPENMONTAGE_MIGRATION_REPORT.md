# BAMO Autonomous Shorts Studio — migration audit

Audit date: 2026-11-07
Repository: `farzin0369/Youtube1`
Protected baseline: `main` @ `c9e090cdb9f003e3a90ee9767f86c8b37562d192`
Work branch: `feat/bamo-openmontage-autonomous-studio`
Current branch head at this report: `a371b4e698def8beb3ff9ecb5fad4a334f22d96c`

## 1. Safety and Git state

- GitHub repository metadata confirms push/admin permission for the connected identity.
- The requested feature branch already existed before this work. It was based directly on the current `main` commit and contained one migration-baseline report commit.
- `main` was not modified.
- No existing engine, workflow, secret, or production setting was deleted or changed.
- The branch now contains a pinned OpenMontage submodule reference. This is a Git submodule pointer, not a copied subtree; consumers must clone with submodules enabled.

## 2. OpenMontage source identity and license

- The requested `Open-Montage-app/OpenMontage` URL returned 404 from the current GitHub API and browser fetch. Search-index snippets for it appear stale/inconsistent and are not a safe source identity.
- The matching current upstream is `https://github.com/calesthio/OpenMontage`, default branch `main`.
- Pinned upstream commit: `d21f5d4eaa08422b09c7091757a05affcbabb35b`.
- Upstream license file identifies GNU AGPL version 3. Commercial use is permitted by AGPL, but distribution of covered/modified software and making a modified version available over a network can trigger source-code and notice obligations. This is not legal advice; review the exact deployment and combination model before monetizing a hosted service.
- The code license does not grant rights to every third-party generated asset, stock clip, music track, voice, or provider output. Those rights need per-asset/provider review.

## 3. Change made on the feature branch

- Added root `.gitmodules` entry for `vendor/openmontage`.
- Added a Git gitlink at `vendor/openmontage` pinned to the upstream commit above.
- Commit: `a371b4e698def8beb3ff9ecb5fad4a334f22d96c` — `build: pin OpenMontage upstream as a submodule`.
- This records the upstream dependency but does not yet prove that GitHub Actions or Colab have fetched, installed, or executed it.

## 4. OpenMontage architecture findings

- OpenMontage is instruction- and agent-driven. Its own `AGENT_GUIDE.md` says the AI coding assistant is the orchestrator; Python provides tools and persistence, while manifests and skills define creative decisions, stages, review, and checkpoints.
- Its animation pipeline defaults to a guided checkpoint policy and has human-approval defaults for proposal, script, scene plan, and assets. That conflicts with BAMO's unattended daily production goal unless a dedicated autonomous policy/runner is implemented and validated.
- The upstream provides pipeline manifests, stage-director skills, a dynamic tool registry, provider scoring, project checkpoints, Remotion composition, HyperFrames composition, and FFmpeg post-production.
- A zero-API-key route exists for offline narration via Piper and for selected open-footage/archive workflows. Piper is explicitly marked experimental and not best-in-class for expressive voice; actual English audio must be rendered and listened to before selecting it.
- The upstream Remotion `Explainer` composition currently declares 1920×1080 landscape output. A 9:16 BAMO composition/profile is still required; do not assume the upstream demo is already Shorts-ready.
- Several upstream video/image providers require API keys and may incur costs. Those providers must remain disabled unless explicitly budgeted and authorized.

## 5. BAMO baseline findings

- The repository contains an existing Python app, multiple render paths, old engines under `engine/`, `vendor/openclaw`, and several historical import/workflow paths. No cleanup has been performed.
- Existing BAMO renderer code has a text-lock and four-scene expectation, but it is not yet wired to OpenMontage.
- The current `config/channel.yaml` describes Persian content and `fa-IR` narration, not the requested English-first channel configuration.
- The existing `daily_run.yml` contains six Tehran cron expressions (07:00, 10:00, 12:00, 15:00, 18:00, 21:00), but scheduled production is gated by `BAMO_PRODUCTION_VISUALS_APPROVED == 'true'`; its current steps are safe dry-run only, and the YouTube OAuth step is disabled with `if: false`. Therefore public daily publishing is NOT active.
- The Colab CLI workflow references a separate Wan 2.1 path and does not initialize submodules. A Colab notebook and CLI workflow exist, but live Colab session availability, GPU allocation, and credentials were not verified.
- YouTube secrets are not readable through the repository-content API. No OAuth token validity or channel identity has been proven in this audit.

## 6. Workflow evidence

- The migration-baseline self-test on the branch completed successfully, but it only validates the baseline/documentation commit. It is not evidence of a rendered video.
- No OpenMontage production render, TTS sample, audio/visual synchronization review, YouTube upload, or Analytics feedback loop has been verified.
- No 10,000-idea bank has been generated or validated. The actual count remains zero.

## 7. Remaining work / release gates

1. Update relevant checkout workflows to fetch submodules recursively; add a dedicated OpenMontage preflight job.
2. Implement a BAMO adapter/runner that translates English idea records into OpenMontage pipeline artifacts, enforces an autonomous approval policy, and only calls tools proven available and free/local by preflight.
3. Add an explicit vertical 1080×1920 composition path and topic-specific scene grammars; validate real motion rather than static-image zooms.
4. Test Piper English voice output against alternatives and listen to the rendered sample. Do not label it natural/native-level until verified.
5. Build the research-backed 10,000-record idea bank with source URLs, deduplication, validation, and used-state tracking. Do not count templates or placeholders as completed ideas.
6. Implement content scoring, research/source verification, technical and semantic QC, resumable checkpoints, and redacted logs.
7. Verify YouTube OAuth using a non-publishing preflight; test private/unlisted upload before any public publishing.
8. Research target-audience timing from channel Analytics where available; only then enable one evidence-based daily schedule.
9. Produce and inspect a real English 20–30s vertical MP4 with narration, moving visuals, synchronized captions, and passing ffprobe/QC.
10. Remove legacy renderers only after the above gates pass and the migration is approved.

## Current status

**Source pinned on the feature branch: YES.**
**OpenMontage installed/executed: NOT YET VERIFIED.**
**BAMO adapter/production runner: NOT YET IMPLEMENTED.**
**10,000 validated ideas: 0.**
**English TTS quality: NOT TESTED.**
**9:16 production render: NOT TESTED.**
**YouTube OAuth/upload: NOT TESTED; publishing remains paused.**
**Daily unattended publishing: NOT ACTIVE.**
**Legacy engines: PRESERVED.**
**Main branch: UNCHANGED.**
