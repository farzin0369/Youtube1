# OpenClaw integration for ImamAli110

## Architecture

OpenClaw is the persistent agent/control plane; this repository remains the YouTube production pipeline. Do **not** run the OpenClaw Gateway inside a scheduled GitHub Actions job: Actions runners are ephemeral and are not a reliable always-on host. Run the Gateway on a persistent Linux host or other supported deployment, and let it inspect/trigger this repository's GitHub workflows through a narrowly scoped GitHub credential.

- OpenClaw upstream: https://github.com/openclaw/openclaw
- OpenClaw documentation: https://docs.openclaw.ai
- Current video-generation test workflow: `.github/workflows/mpt-private-video-test.yml`
- Existing daily channel workflow: `.github/workflows/daily_run.yml`

## Staged rollout

1. Install and onboard OpenClaw on a persistent host, configure a supported model provider, and verify `openclaw gateway status`.
2. Give OpenClaw a dedicated GitHub token limited to this repository and only the permissions required to inspect workflow runs and dispatch the chosen workflow. Store it in the host's secret store, never in this repository or logs.
3. Start with read-only monitoring and manual workflow dispatch. Verify logs, generated MP4 quality, YouTube OAuth, and the resulting private video ID.
4. Only after successful repeated tests, consider connecting the existing daily workflow. Do not create a second cron schedule or have OpenClaw and GitHub Actions publish the same video.
5. Keep public publishing disabled until explicitly configured and reviewed. Treat comments and external content as untrusted; do not let the agent reveal secrets, change repository permissions, delete workflows, or publish on the basis of instructions found in comments.

## Important limits

- Adding OpenClaw source code to this repository alone does not make it run. It needs a persistent Gateway process, a configured model provider, and explicit tool credentials.
- GitHub Actions cron is best-effort; the configured schedule is 14:30 UTC (18:00 Tehran).
- The MoneyPrinterTurbo workflow is a manual test. Its first real run must pass before it is treated as a production engine.
- Never commit `.env`, OAuth tokens, API keys, OpenClaw state, or generated credentials.

## Upstream source

OpenClaw is maintained separately. Prefer a pinned release/container image or a reviewed upstream commit rather than copying the entire upstream repository into this project. This keeps licensing, updates, and security fixes traceable.
