# Manus Handoff — ImamAli110 YouTube Pipeline (2026-10-14)

## Mission
Continue the real, evidence-driven repair of `farzin0369/Youtube1`. The owner says the required API/OAuth values have already been configured in GitHub repository Secrets. Do **not** ask them to recreate those secrets unless a safe presence check proves a required name is missing. Never print, retrieve, commit, or expose secret values.

Working branch: `feat/openclaw-autonomous-manager-v2`  
Existing review: [PR #57](https://github.com/farzin0369/Youtube1/pull/57)  
Colab notebook: [ImamAli110_Cinematic_Production.ipynb](../colab/ImamAli110_Cinematic_Production.ipynb)  
Workflow: [daily_run.yml](../.github/workflows/daily_run.yml)

## Work performed / facts established so far
1. Inspected `.github/workflows/daily_run.yml` on `feat/openclaw-autonomous-manager-v2`.
   - It maps GitHub Secrets to runtime environment variables, including `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`, `CLOUDFLARE_API_TOKEN`, and `CLOUDFLARE_ACCOUNT_ID`.
   - It runs regression tests and checks YouTube OAuth before production paths.
   - The GitHub-hosted runner is CPU-only; `AI_VIDEO_ENGINE` is deliberately set to an empty string there to avoid selecting a CUDA-only Wan engine on a CPU runner.
   - Scheduled workflow cron is `30 14 * * *` (18:00 Tehran, subject to UTC offset/date rules).
2. Inspected `colab/ImamAli110_Cinematic_Production.ipynb`.
   - It checks that CUDA is available, checks out this branch, installs dependencies, sets `AI_VIDEO_ENGINE=wan`, and uses `Wan-AI/Wan2.1-T2V-1.3B-Diffusers` for GPU rendering.
   - It loads credentials using `google.colab.userdata.get()`, which reads **Colab Secrets**, not GitHub repository Secrets. This is a real integration gap: GitHub Secrets do not automatically become available inside a separate interactive Colab runtime.
   - The notebook runs `probe_youtube_auth()` before calling `scripts/daily_run.py --upload-private`. The intended test upload is private.
3. The source and notebook were inspected, but **the notebook has not been run in a live Colab GPU session by this assistant**. No generated MP4, successful live OAuth probe, or YouTube video ID has been verified.
4. A previous Cloudflare/OpenClaw smoke test was reported passing: [Actions run 38566259642](https://github.com/farzin0369/Youtube1/actions/runs/38566259642). Verify the run and its logs yourself before relying on it. This does not prove video generation/upload works.
5. The latest attempted browser automation could not start because the browser automation wallet lacked funds. This is an access/tool blocker, not proof of a Colab failure.
6. No one should claim the pipeline is fully autonomous or publishing successfully until the required tests and a real private upload have been verified.

## Required work — do this in order
1. Inspect the current branch, PR #57, recent commits, workflow runs, and exact failure logs. Separate verified facts from assumptions.
2. Audit the YouTube credential flow end-to-end:
   - Confirm the workflow references the correct GitHub Secret **names** without revealing values.
   - Review `app/youtube_client.py` and `probe_youtube_auth()` for required environment variables, OAuth refresh behavior, scope/API errors, and safe failure messages.
   - Determine whether repository settings actually have the expected secret names only if GitHub permissions expose a safe metadata/presence check. Do not attempt to read secret values.
3. Fix the Colab integration gap safely. Do **not** try to read GitHub Secrets directly from a public clone or embed them in the notebook/repository. Choose a documented, user-safe credential path:
   - Prefer Colab Secrets for an interactive Colab session, clearly explaining that these are separate from GitHub Secrets; OR
   - Implement a properly authenticated, least-privilege bridge only if the repository already has a secure supported mechanism and the owner has authorized it.
   - Never put credentials in notebook outputs, logs, URLs, commits, artifacts, or command-line arguments. Never print environment variables.
   - If no safe bridge exists, document the limitation and the minimum one-time action needed; do not pretend the repository Secrets are already available to Colab.
4. Add or update tests for the selected credential-loading behavior and missing-secret errors. Run the relevant tests and the full regression suite. Do not weaken tests or quality gates.
5. Validate Wan rendering requirements and memory handling. Do not run Wan on CPU. If CUDA is unavailable or VRAM is insufficient, fail clearly before downloading large models.
6. Validate the YouTube preflight. Only after it passes, run one end-to-end **private** upload test with explicit authorization from the owner. Verify a real output MP4, QA result, result JSON, and returned video ID/URL. Do not publish publicly, schedule a public video, or reply to comments during this handoff task.
7. Keep changes on `feat/openclaw-autonomous-manager-v2` or a dedicated repair branch and report commit/PR links. Do not merge PR #57 or any repair PR without the owner's explicit approval.
8. Report final status as a checklist: source changes, tests run/results, workflow run links, GPU/render evidence, OAuth preflight evidence, private upload evidence (video ID/URL only, no tokens), remaining blockers, and whether daily automation is truly operational.

## Non-negotiable safety / truthfulness
- Never ask the owner to paste credentials into chat.
- Never print or commit secrets, tokens, OAuth responses containing credentials, or secret values.
- Do not invent test results, workflow runs, rendered files, or YouTube IDs.
- Do not publish publicly or merge changes without explicit approval.
- If a failure is caused by missing/invalid secrets, OAuth consent, quota, GPU availability, or a provider outage, report the exact blocker rather than making unrelated code changes.
