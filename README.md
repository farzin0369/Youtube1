# YouTube Automation Faith

Automation scaffold for the Persian channel [imam ali](https://www.youtube.com/@imamali.110).

## Schedule (Asia/Tehran)
- 06:00: one Short
- 20:30: one long-form video

## Safety mode
The initial workflow generates assets and uploads them as **private/unlisted**. Public publishing is intentionally disabled until the owner reviews quality, source citations, copyright status, and comment behavior.

## Pipeline
1. Research from approved, traceable sources.
2. Draft Persian script and source list.
3. Generate male narration or avatar voice.
4. Render video, captions, thumbnail, title and description.
5. Upload privately/unlisted through the YouTube Data API.
6. Fetch comments and draft context-aware replies; sensitive or uncertain comments remain pending review.
7. Store an audit record and metrics for iteration.

## Required GitHub Actions secrets
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`
- `OPENAI_API_KEY` (or compatible API endpoint)
- `TTS_API_KEY` (provider-specific)

No secret belongs in Git. See `config/channel.yaml` and `.env.example`.

## Important limitation
This scaffold does not promise subscriber growth or automatically make public claims. It is designed for quality-controlled experimentation, source attribution, and gradual optimization.
