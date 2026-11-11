# Jarvis + OpenRouter (branch integration)

This branch adds a manual, secret-safe OpenRouter model smoke test to the YouTube1 repository. It does not alter the daily publishing workflow or upload videos.

## Run the model

1. In GitHub, open **Settings → Secrets and variables → Actions** for this repository.
2. Add an Actions repository secret named `OPENROUTER_API_KEY`. Never put the key in a file, commit, workflow input, or chat.
3. Open **Actions → Jarvis OpenRouter model test → Run workflow**.
4. The smoke test defaults to `minimax/minimax-m3.1-flash:free`, which was listed with zero prompt/completion price in OpenRouter's public model catalog on 2026-10-22.
5. Read the response in the run log. The workflow does not print the API key.

## Notes

- OpenRouter model availability, free quotas, and rate limits can change; a `:free` suffix does not guarantee continuous availability.
- Jarvis Chat uses this single free model; it reports model/quota errors and does not silently switch to a paid or local model.
- The workflow uses a manual dispatch only, has a 3-minute job timeout, and does not publish content.
- The existing `app/llm_provider.py` already supports OpenAI-compatible gateways through `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. For the daily pipeline, configure those as repository Actions secrets/variables if you want the provider chain to use OpenRouter. Do not configure the local Ollama fallback as a substitute for the cloud model if high-quality output is required.
