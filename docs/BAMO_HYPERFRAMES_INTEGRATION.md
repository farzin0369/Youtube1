# BAMO single-engine motion graphics

## Sole renderer

BAMO uses **HyperFrames** as its only video renderer, pinned to CLI version `0.8.225` from https://github.com/heygen-com/hyperframes. The composition uses HTML/CSS 3D scenes and GSAP timelines for camera movement, scene transitions, animated typography and visual motion.

No diffusion video models (including Wan or LTX), CogVideoX, Blender, Manim, Three.js, Motion Canvas or alternate video renderers are selected by this branch. FFmpeg is retained only for final encoding, audio muxing and media probing; it is not a second scene renderer.

## Eleven-agent connection

The eleven BAMO production roles remain the editorial/director layer: discovery, strategy, script/hook, packaging, SEO, production, editing, Shorts, chapters, community and analytics. Their skill definitions live under `.claude/skills/`. The production brief must contain all eleven role hand-offs before rendering starts.

Each authored scene requires its own visible Persian text, visual prompt and duration. The narration must equal the ordered scene texts exactly. The audio builder generates one Persian TTS segment per scene, fits it to that scene's duration, and emits matching VTT subtitles. This prevents the spoken line from drifting into the next visual scene.

## CPU-first workflow

Use Node.js 22+, HyperFrames CLI `0.8.225`, FFmpeg and Edge TTS. The GitHub Actions workflow renders on a CPU runner at 1080x1920 / 30 fps; no GPU, diffusion weights, paid video API or Colab session is required.

The workflow validates all eleven role hand-offs, renders the four-scene review film, adds scene-locked Persian voice and subtitles, and checks the final MP4 dimensions, audio stream, file size and subtitle artifact. The output is a review artifact only.

## Safety

No YouTube upload or public publishing is performed by this render workflow. Keep OAuth credentials and API keys out of source files and logs. A successful workflow run proves the render pipeline executed; visual review is still required before any publication.
