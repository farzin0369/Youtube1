# TT خبر — Production architecture and rollout

## Production pipeline

1. app/research.py fetches public RSS headlines and summaries across world, politics, technology, business, science, sports, entertainment and health.
2. Stories are deduplicated and selected with category diversity. The original publisher, story URL and publication time are retained.
3. app/script_gen.py uses the local Ollama model to write a 3–5 minute Persian bulletin grounded only in fetched source data. The quality gate rejects missing source URLs and undersized/oversized scripts.
4. app/tts.py generates Persian narration; Edge TTS is primary and local Piper can be configured as fallback.
5. app/local_video_engine.py uses CogVideoX on a CUDA GPU and category-specific illustrative news B-roll prompts. AI-generated scenes must never be presented as authentic footage of a specific real event.
6. FFmpeg muxes narration and subtitles, then app/media_qa.py verifies the media package before YouTube upload.
7. YouTube upload must confirm a video ID. Scheduled publication is rejected when the requested publish time is too close or past.
8. Comment automation is bounded and idempotent. Sensitive or uncertain cases remain pending for human review.

## Schedules

- Global-news production workflow: scheduled every four hours (UTC) with a six-hour publish buffer.
- Health, analytics and comment review: every six hours.
- OAuth preflight: manual only; it validates authentication and the channel without publishing.
- CPU smoke tests validate structure and media assembly only. They do not prove CogVideoX GPU production or a real YouTube upload.

## Failure handling

- No usable RSS sources: fail closed; do not invent a bulletin.
- Local model unavailable or malformed output: stop publication rather than publish unsupported fallback news.
- Fewer than three source URLs, URLs absent from the description, or script length outside the 300–750-word guard: stop publication.
- Missing GPU, model download failure, media QA failure, or rejected YouTube OAuth: report the failure and preserve run artifacts when available.
- OAuth credentials must never be printed, even as prefixes or lengths.

## Known external dependencies

- Google News RSS endpoints and publisher links are external and can be unavailable or rate-limited.
- Google Colab controls GPU allocation and quotas.
- Google OAuth consent settings and the three YouTube OAuth secrets must remain valid.
- A free T4 can be too slow or memory-constrained for 3–5 minutes of generated video every four hours. The schedule is configured, but throughput and queue behavior must be measured from real runs before claiming the target cadence is met.
- config/channel.yaml holds the current channel URL. After the owner changes the YouTube channel handle to TT خبر, update this URL to the new handle.

## Safety and rollout

No self-modifying code is deployed automatically. Repairs must be isolated, tested, reviewed, and merged. Public uploads and comment replies are external side effects; only a run with confirmed upload metadata counts as a successful production run.
