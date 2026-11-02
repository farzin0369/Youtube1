# BAMO Neon Motion Engine (CPU prototype)

## Purpose
This specialist renderer recreates the visual language of the supplied BAMO mathematics reference: tall luminous geometry, orbiting colored particles, accumulating light trails, connected geometric webs, layered bloom, a restrained vignette, and a gradual climax. It is the dedicated math-motion path for this reference style.

## Runtime
- Python 3.11+
- Pillow
- FFmpeg / ffprobe
- CPU only; no GPU, model download, or paid API required
- Output: vertical 720x1280 MP4, 24/25/30 fps; horizontal and square formats are also supported

## Render a reference project
```bash
sudo apt-get install -y ffmpeg fonts-noto-core fonts-noto-extra
python -m pip install Pillow
python scripts/render_bamo_neon.py \
  --project examples/bamo_neon_math_reference.json \
  --output output/BAMO-neon-math-reference.mp4
```

Optional narration:
```bash
python scripts/render_bamo_neon.py --project project.json --output output.mp4 --audio narration.wav
```

Scene fields include duration, text, narration, motif, palette, camera, and visual_brief. Supported visual motifs include ellipse_mesh, wave, interference, atom, molecule, radial, burst, and sun. Captions are timed from the same scene durations; optional audio is muxed to the rendered MP4.

## Verification
Workflow: `.github/workflows/bamo_neon_math_engine.yml`

The workflow installs CPU dependencies, runs unit tests, renders the reference project, probes the MP4, and uploads the artifact. A green workflow proves only that the renderer executes and produces a valid MP4; it does not prove full visual equivalence or integration with all 11 agents.
