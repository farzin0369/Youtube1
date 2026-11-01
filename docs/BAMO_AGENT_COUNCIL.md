# BAMO independent agent council

The production pipeline now runs eleven independent specialist reviews after rendering and media QA and before any upload.

## What independence means

- Each specialist has a separate role prompt and a separate bounded memory file under `state/agent_memory/`.
- All specialists receive the same immutable production package.
- Reviews run in parallel (default maximum concurrency: 4).
- Reviewers do not receive other reviewers' outputs.
- The report records the provider/model identity actually used for every reviewer.
- The system never claims that eleven agents means eleven different foundation models.

## Optional per-agent model routing

To route specialists to different OpenAI-compatible providers/models, add a GitHub Actions repository secret named `BAMO_AGENT_PROVIDER_CONFIG`. Its value is a JSON object keyed by agent ID. Each entry requires `base_url`, `api_key`, and `model`; `provider` is an optional display label.

Example (replace every placeholder with a real provider endpoint, model ID, and secret key; do not commit credentials):

```json
{
  "trend_researcher": {
    "provider": "provider-a",
    "base_url": "https://provider-a.example/v1",
    "api_key": "REPLACE_WITH_SECRET",
    "model": "MODEL_ID_A"
  },
  "fact_checker": {
    "provider": "provider-b",
    "base_url": "https://provider-b.example/v1",
    "api_key": "REPLACE_WITH_SECRET",
    "model": "MODEL_ID_B"
  }
}
```

The supported agent IDs are:

- `trend_researcher`
- `fact_checker`
- `growth_strategist`
- `scriptwriter`
- `story_director`
- `3d_motion_director`
- `audio_director`
- `editor`
- `youtube_seo`
- `retention_analyst`
- `independent_critic`

Only configured agents use their dedicated endpoint. Unconfigured agents use the existing provider fallback chain. If a dedicated endpoint fails, that agent falls back and the report records the actual fallback identity. A free quota is not guaranteed by any provider.

## Publication gate

Publication is blocked unless all eleven reviews complete, at least nine approve, the mean score is at least 85/100, and no reviewer reports a critical issue. Deterministic media/editorial gates remain in place and cannot be overridden by the council.

The council does not promise a viral result or a specific view count. Its purpose is to improve the odds through stronger editorial selection and repeatable quality control.
