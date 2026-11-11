# Z.ai / GLM gateway setup

This repository already supports an OpenAI-compatible LLM gateway through `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. Z.ai does not need a new Python dependency for this path.

## Important cost limitation

The public Z.ai chat website is not the same thing as API access. Do not assume a free chat account includes a free, unlimited API. Z.ai's coding plans are paid after any eligible trial/allowance, and availability can change. The workflow below only verifies API access if you already have an eligible API key; it does not create one or bypass quotas.

## Configure GitHub (only if Z.ai grants you usable API quota)

In the repository, open **Settings → Secrets and variables → Actions**.

Create a repository secret:
- `ZAI_API_KEY`: the API key from your Z.ai account. Never commit it to a file.

Create repository variables:
- `LLM_BASE_URL`: `https://api.z.ai/api/paas/v4` for standard API-key access.
- `LLM_MODEL`: the exact model ID enabled for your account (check the current Z.ai console; do not assume every model is enabled).

The existing daily workflow reads `LLM_BASE_URL` from a repository variable and `LLM_API_KEY` from a repository secret. To use this gateway in that workflow, either set `LLM_API_KEY` to the same key or use the workflow's current secret name. Do not put the key in a repository variable, YAML, README, or commit.

For a Z.ai **Coding Plan**, use only the endpoint and model documented for that plan in your current Z.ai account; its coding endpoint may differ from the standard API endpoint. A paid coding-plan endpoint is not evidence of a free API allowance.

## Preflight

The manual workflow `Z.ai GLM API preflight` checks whether the configured API key and model can answer a minimal request. It does not print the key, edit source code, upload videos, or publish to YouTube.

## Limits

- No API key or no eligible free quota means there is no dependable unattended GLM call.
- A successful preflight proves API connectivity only; it does not prove the full video pipeline works.
- The repository's existing daily workflow still has its own YouTube OAuth, Pexels, GitHub Actions quota, and content-quality requirements.
