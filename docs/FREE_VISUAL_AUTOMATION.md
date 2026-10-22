# Free YouTube visual automation — draft-only starter

This folder adds an **inactive n8n import file** and an offline validator. It does not install a server, connect accounts, render videos, upload to YouTube, or publish anything.

## What is included
- `automation/n8n/youtube-draft-intake.json`: importable draft-only workflow. Manual Trigger → validation/deduplication → review-ready/rejected output. It has no credentials, external calls, upload node, schedule, or webhook. It is explicitly inactive.
- `scripts/check_n8n_draft_workflow.py`: standard-library structural checks and fixtures for valid, invalid, historical duplicate, duplicate video ID, and duplicate-in-batch inputs.
- `.github/workflows/check-n8n-draft.yml`: runs only those checks on pushes/PRs affecting these files. It never runs the video pipeline or uploads.

## Free-first architecture
1. **Visual editor:** try Activepieces Cloud's free tier at https://cloud.activepieces.com/ . Check current limits before relying on it. Alternatively import the JSON into a self-hosted n8n instance; n8n Community is free software, but a continuously running host is not included.
2. **Video rendering:** reuse this repository's existing pipeline through GitHub Actions where available, or Colab for manual GPU sessions. GitHub-hosted runner minutes, GPU access, free AI services, and Colab GPUs are limited/not guaranteed.
3. **YouTube:** use YouTube Data API OAuth only after separately configuring credentials. Never place tokens in workflow JSON or source code.
4. **Approval gate:** first create metadata/drafts and QC reports only. Add upload as a separate workflow only after explicit approval; keep videos private until manually reviewed.

## Import on Android
1. Open your chosen n8n editor in the browser.
2. Create a workflow and choose **Import from File** (or paste the JSON through the editor's import option). The file is at `automation/n8n/youtube-draft-intake.json`.
3. Keep the workflow inactive. The current starter uses Manual Trigger only and does not upload.
4. Run tests locally only if you have Python; otherwise GitHub Actions can run the validator after the branch files are committed.

## Important repository safety note
The existing `.github/workflows/daily_run.yml` and current `main` configuration are not modified by this starter. The repository README describes an existing daily pipeline that may publicly schedule videos when its publish path and secrets are enabled. This branch does **not** disable or change that pre-existing workflow. Before enabling any new automation, review the current Actions schedules and secrets and decide whether the existing public-publishing schedule should be paused. No new schedule is enabled by these files.
