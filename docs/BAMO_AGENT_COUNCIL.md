# BAMO independent 11-model council

The eleven specialist reviewers have eleven different base model IDs pinned in `config/bamo_agent_models.json`. The registry is checked at runtime: every role must exist, every model ID must be unique, and no reviewer may silently fall back to a shared model.

## Model assignment

| Specialist | Provider | Pinned model |
|---|---|---|
| Trend researcher | Groq | `openai/gpt-oss-120b` |
| Fact checker | Groq | `qwen/qwen3.8-27b` |
| Growth strategist | Groq | `openai/gpt-oss-20b` |
| Scriptwriter | OpenRouter | `google/gemma-4-26b-a4b-it:free` |
| Story director | OpenRouter | `nvidia/nemotron-3-super-120b-a12b:free` |
| 3D motion director | OpenRouter | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` |
| Audio director | OpenRouter | `nvidia/nemotron-3-nano-30b-a3b:free` |
| Editor | OpenRouter | `nvidia/nemotron-nano-9b-v2:free` |
| YouTube SEO | OpenRouter | `xingchen-agi/xing4.0-29b-a4b:free` |
| Retention analyst | OpenRouter | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| Independent safety/integrity critic | Groq | `openai/gpt-oss-safeguard-20b` |

The model IDs are pinned for reproducibility, but providers can change free availability, limits, or model access. A free listing is not a guarantee of permanent free inference.

## Required GitHub Actions secrets

- `GROQ_API_KEY`: used by four specialists.
- `OPENROUTER_API_KEY`: used by seven specialists.

Add `OPENROUTER_API_KEY` in the repository's GitHub Settings → Secrets and variables → Actions. Never put API keys in source files, workflow values, commits, or logs. The existing `GROQ_API_KEY`, if already configured, can be reused. The OpenRouter key is an additional required credential; the GitHub connection used for repository edits cannot create or inspect repository secrets.

## Free-tier capacity and privacy

The seven OpenRouter assignments use `:free` variants. OpenRouter currently documents a limit of 20 requests/minute and 50 requests/day for free variants on accounts without a qualifying credit purchase. At six BAMO production runs per day, the seven OpenRouter reviewers consume 42 calls/day, leaving only eight calls of headroom. Failed requests can also count toward limits, so this is a tight free-tier budget. OpenRouter calls are single-attempt; if an endpoint is unavailable, the council blocks publication rather than silently switching models. Groq model limits vary by model and account; check the account's current Limits page.

Some free endpoints may log prompts or use them to improve provider services. Do not send personal, confidential, or private account data through these models. Public video scripts and production metadata are the intended review payload.

## Independence and publication gate

Each specialist has a separate role prompt and bounded private memory file. All reviewers receive the same production package and cannot see other reviewers' verdicts. The report records the actual provider and model ID used.

Publishing is blocked unless all eleven reviews complete, at least nine approve, the mean score is at least 85/100, and no reviewer reports a critical issue. A missing API key, unavailable model, invalid response, or rate limit blocks the run. This system improves editorial quality; it cannot guarantee a viral video or a specific number of views.
