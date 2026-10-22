# Free YouTube visual automation — draft-only starter

This branch prepares a **manual-only, draft-first** path. It does not activate n8n, connect accounts, render or upload a video automatically, or publish anything by itself.

## What is included
- `automation/n8n/youtube-draft-intake.json`: importable n8n workflow, explicitly inactive. Manual Trigger → validation/deduplication → review-ready/rejected output. No credentials, external calls, upload node, schedule, or webhook.
- `scripts/check_n8n_draft_workflow.py`: standard-library structural checks and fixtures for valid, invalid, historical duplicate, duplicate video ID, and duplicate-in-batch inputs. It also guards against a scheduled publishing trigger in the production workflow on this branch.
- `.github/workflows/check-n8n-draft.yml`: runs only validator tests on matching pushes/PRs. It never runs the video pipeline or uploads.
- `.github/workflows/daily_run.yml`: on this branch only, the automatic daily schedule has been removed. Manual dispatch remains, with both publishing and private upload defaulting to false. This is a proposed safety change and does not affect `main` until merged.

## Free-first architecture
1. **Visual editor:** try Activepieces Cloud at https://cloud.activepieces.com/ and check current free-tier limits. Alternatively import the JSON into self-hosted n8n Community; the software is free, but an always-on host is not included.
2. **Video rendering:** reuse this repository's existing pipeline through GitHub Actions where available, or Colab for manual GPU sessions. Runner minutes, GPU access, free AI services, and Colab availability are limited/not guaranteed.
3. **YouTube:** use YouTube Data API OAuth only after separately configuring credentials. Never place tokens in workflow JSON or source code.
4. **Approval gate:** begin with metadata and QC reports only. Upload/public scheduling remains an explicit manual choice in GitHub Actions and is never enabled by the n8n draft workflow.

## Import on Android
1. Open your n8n editor in the browser.
2. Import `automation/n8n/youtube-draft-intake.json`.
3. Keep it inactive. It only validates incoming title/topic metadata; it is a safe starter, not yet a full renderer/uploader.
4. GitHub Actions can run the validator after branch pushes. Do not merge the branch until you have reviewed its changes.

## Critical note about main
I inspected `.github/workflows/daily_run.yml` on `main`. It contains a daily cron trigger and its scheduled path calls `python scripts/daily_run.py --publish`, which can publicly schedule a video if required credentials are configured. This branch removes that automatic schedule as a proposed change, but **main remains unchanged until you merge it**. If you want to prevent the existing schedule immediately, the main workflow itself must be disabled or changed in GitHub; I have not changed main or merged this branch.
