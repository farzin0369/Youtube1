# Ssemble-style clip automation prototype

This is an **isolated prototype** on branch `feat/ssemble-style-clip-automation-prototype`. It does not change the existing ImamAli110 spiritual pipeline and does not publish to YouTube.

## What it does

- Takes a local video file that you own or are licensed to process.
- Uses FFmpeg scene-change timestamps to rank candidate windows. This is a simple, inspectable heuristic, **not** AI virality prediction.
- Renders non-overlapping 9:16 candidate clips at 1080x1920 (H.264/AAC).
- Writes `manifest.json` with timestamps and the selection method.
- Requires explicit rights confirmation in the CLI.

## Run

```bash
python scripts/run_clip_automation.py --input /path/to/authorized-video.mp4 --rights-confirmed --clip-seconds 30 --count 3
```

Outputs go to `output/clip-automation/` by default. FFmpeg and ffprobe must be installed. This first prototype does not download YouTube videos, translate speech, synthesize Persian narration, add subtitles, estimate real retention, or upload automatically. Those should be added only after validating the rendered clips and the rights/source workflow.

## Safety and quality notes

- Use original, licensed, or explicitly authorized source media; public availability is not permission to reuse it.
- Center-cropping can cut off important action. Human review is required before publishing.
- The scene-change heuristic is only a baseline. It must not be presented as a true virality score.
- The production workflow in `.github/workflows/daily_run.yml` remains untouched.
