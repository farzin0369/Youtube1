# MoneyPrinterTurbo integration evaluation

## Decision

Evaluate MoneyPrinterTurbo as a replacement for the current rendering/content-generation stage, but do not replace the production pipeline until an end-to-end test creates a valid Persian MP4. Keep the existing YouTube Data API uploader and Tehran scheduling logic unchanged.

Upstream: https://github.com/harry0703/MoneyPrinterTurbo

## Why this candidate

The upstream README documents a Python API and web UI, vertical 9:16 output, script generation, stock footage, TTS, subtitles, and background music. It documents English and Chinese copy support, but does not establish Persian quality. A Persian voice and right-to-left subtitle test is therefore mandatory.

The upstream project's README and publishing options have changed over time. Do not assume its publishing feature uses YouTube Data API directly; the current README should be checked before enabling any cross-platform publishing. For this repository, use only the existing official YouTube API uploader.

## Required acceptance test

1. Run on Python 3.11 in a disposable GitHub Actions job, not in the scheduled production workflow.
2. Configure an LLM provider and a stock-footage provider through GitHub Secrets; never print credentials.
3. Generate one 9:16 Persian spiritual-growth Short using the configured Persian TTS voice.
4. Verify the output exists and is a playable MP4, 1080x1920 (or document any supported lower-resolution test), with nonzero duration and audio.
5. Verify Persian captions render right-to-left and remain legible.
6. Upload the generated MP4 as a **private** video using the existing `app.youtube_client` only after the render checks pass and only in an explicitly dispatched test run.
7. Confirm the returned YouTube video ID and private visibility. Never publish publicly as part of this acceptance test.
8. Keep the current scheduled workflow unchanged until every step passes.

## Current blockers / risks

- The last observed production run failed script validation: the model generated 20 words when the Shorts gate required 28–44. That is a content-generation failure before video rendering, not evidence that the video renderer or uploader works.
- MoneyPrinterTurbo's documented copy-language support does not guarantee natural Persian narration.
- A GitHub-hosted runner is ephemeral. Local UI sessions and local configuration cannot be assumed to persist between daily runs.
- Third-party stock-footage and LLM providers may require API keys and may incur costs. Edge TTS may be available without a provider key, but voice availability and quality must be tested.
- Do not commit `config.toml`, OAuth files, refresh tokens, or any API keys.

## Rollback

This evaluation is isolated on a branch. Do not modify `.github/workflows/daily_run.yml`, `app/spiritual_pipeline.py`, or the current YouTube upload code until the acceptance test passes. If the candidate fails Persian TTS, subtitles, runtime, or reliability checks, retain the existing pipeline and fix the specific failing stage instead.
