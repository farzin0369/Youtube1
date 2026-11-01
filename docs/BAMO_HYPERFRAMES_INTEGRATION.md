# BAMO HyperFrames renderer integration

## Upstream

- Repository: https://github.com/heygen-com/hyperframes
- Pinned upstream commit: `94849bf1e0b3bdc2d5eb118b82109e310c4215b1`
- License declared by upstream README: Apache-2.0
- Runtime: Node.js >=22; HTML/CSS/seekable animations rendered deterministically to MP4 using the HyperFrames CLI and FFmpeg.

The upstream project is included as a Git submodule at `vendor/hyperframes` so BAMO pins a reproducible version without copying a very large upstream history into this repository. To initialize it in a local clone: `git submodule update --init --recursive`.

## BAMO integration policy

The 11-agent editorial system remains the director and content-quality layer. HyperFrames is a specialist rendering backend, not a replacement for those agents. Use it for motion graphics, typography, charts, captions, overlays, infographic scenes, and HTML/CSS compositing. Keep Manim as the mathematics specialist and retain Blender only as an optional 3D backend; do not make Blender a required dependency for daily CPU runs.

## CPU-first execution

Use Node.js 22 or newer, install the project-local HyperFrames CLI from the pinned submodule/package source, and render with FFmpeg on GitHub-hosted CPU runners. Do not require GPU, cloud credits, API keys, or an external hosted render service. Validate every output with `ffprobe` (codec, dimensions, frame rate, duration, non-zero file size) before it can pass the production gate.

## Safety and delivery

Rendering workflows must write to a review artifact only. No workflow in this integration is authorized to publish or upload to YouTube. Keep secrets out of logs and do not run untrusted generated scripts with elevated permissions.
