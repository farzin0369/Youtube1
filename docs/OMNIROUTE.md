# OmniRoute integration for Youtube1

This repository already supports OmniRoute through its OpenAI-compatible gateway in `app/llm_provider.py`. The workflow does **not** launch a fresh OmniRoute server by itself: a server started inside a disposable GitHub Actions runner would have no configured provider accounts or persistent OAuth state, so it would not magically unlock free quotas.

## Connect an OmniRoute endpoint

1. Deploy OmniRoute somewhere that stays online (or use an already-running trusted instance). Follow the upstream setup guide: https://github.com/Gmagl/omniroute
2. In OmniRoute, connect providers you are legitimately entitled to use, test them, then create an endpoint/API key and choose a working model or fallback combo.
3. In this repository, open **Settings → Secrets and variables → Actions**.
4. Add repository **Secret** `LLM_API_KEY` with the OmniRoute endpoint key. Never commit the key or put it in a public variable.
5. Add repository **Variables**:
   - `LLM_BASE_URL`: the OmniRoute OpenAI-compatible API base URL ending in `/v1` (for example, `https://YOUR-OWN-HOST/v1`; do not use this example literally).
   - `LLM_MODEL`: the exact model/route identifier shown by your OmniRoute endpoint.
6. Run **Actions → Persian spiritual channel — daily Shorts → Run workflow** with both `publish` and `upload_private` set to `false`. Inspect the logs for `openai-compatible:<model>` and verify that the full QA and render stages pass before enabling publishing.

## Provider fallback order

The application tries configured Groq first, then the configured OpenAI-compatible endpoint (OmniRoute fits here), then the local Ollama model. If Groq is absent or fails, OmniRoute is attempted before local Ollama. Transient HTTP errors are retried and secrets are not logged.

## Important limitations

- The upstream project's advertised monthly free-token total is an aggregate of provider free tiers, **not a guaranteed allocation for this channel**. Individual providers can impose account, region, model, request-rate, and daily/monthly limits or change their terms.
- OmniRoute is a router, not a video-generation engine. It can improve script/metadata generation and provide provider failover; footage availability, narration, rendering, and the project's quality gates remain separate dependencies.
- A public GitHub-hosted runner cannot reach `localhost` on your phone or your own computer. The endpoint must be reachable from GitHub Actions over HTTPS, or be deployed as part of the workflow with provider credentials/configuration deliberately supplied. Do not expose an unauthenticated OmniRoute dashboard/API to the public internet.
- This integration does not add a paid service, store API keys in source, change YouTube publishing defaults, or bypass provider terms/rate limits.
