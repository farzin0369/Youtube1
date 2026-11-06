# BAMO → OpenMontage migration: architecture baseline (phase 0)

Branch: `feat/bamo-openmontage-autonomous-studio` (cut from `main` @ c9e090c). `main` is untouched.

## Verified so far
- Repo: `farzin0369/Youtube1`, Python, default branch `main`.
- Existing engines: `engine/` (viral_short.py, stock_short.py, modern_gpu_short.py), `vendor/openclaw`, MoneyPrinterTurbo import workflows, Colab/Kaggle/GPU workflows.
- 24 workflows in `.github/workflows` (daily_run, bamo_autopilot_continuous, colab_*, modern_gpu, youtube-oauth-check, ...).
- Latest main work: text-lock (caption == narrator), edge-tts voice, offline script fallback.

## OpenMontage source identity
- The URL in the mission (`Open-Montage-app/OpenMontage`) was NOT found.
- The upstream project that matched is `calesthio/OpenMontage` (AGPL-3.0, ~77k stars, 12 pipelines, 100+ tools). Others found are forks/mirrors/unrelated (deenojo mirror, charliewwdev, RayCodes, AdCraft).
- License: AGPL-3.0. Vendoring it makes BAMO's combined work subject to AGPL source-offer terms when run as a network service. Repo is public, but this must be a conscious decision.

## Plan (nothing below is done yet)
1. Vendor calesthio/OpenMontage under `vendor/openmontage` (git subtree, pinned commit) from a machine with network access.
2. Adapter `engine/openmontage_adapter.py`: BAMO idea -> OpenMontage brief -> render.
3. Idea bank (JSONL/SQLite) with generator + validator; no unsourced facts.
4. Content-intelligence scorer, QC gate (ffprobe, frame/audio checks), YouTube publish step.
5. Schedule via GitHub Actions; rendering on Actions CPU (Colab optional).
6. Remove old engines only after a real approved video is produced.

## Not verified yet
OAuth token validity, whether credentials are committed to the repo, Actions quota/run status, voice quality, any real render.
