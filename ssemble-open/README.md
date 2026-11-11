# Ssemble-Open (CPU-only prototype)

An isolated prototype in a dedicated branch; the existing app files are not changed.

## What it does
- Downloads a video URL with yt-dlp only when you have permission to download and reuse it.
- Cuts a chosen time range.
- Produces a 9:16 MP4 with blurred background fill using FFmpeg.
- Saves the MP4 as a GitHub Actions artifact.

## Limits
- No GPU required.
- GitHub Actions is temporary, not an always-on server; artifacts expire after 3 days.
- Does not automatically publish to YouTube.
- Downloading does not grant copyright or reuse rights. Reused content may be ineligible for monetization.
- It does not bypass logins, paywalls, DRM, or access controls.

## Run
After this workflow is merged to the default branch, open Actions → Ssemble-Open CPU clipper → Run workflow. Provide a video URL, start time, duration (1–90 seconds), and choose yes only if you have rights to reuse it. Download the ssemble-open-clip artifact.

Local use (Python 3.11+, yt-dlp, FFmpeg):
    python ssemble-open/clipper.py --url "VIDEO_URL" --start 30 --duration 30 --output clip.mp4
