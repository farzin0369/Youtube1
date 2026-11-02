# BAMO Neon Motion Engine (CPU prototype)

## Purpose
This specialist renderer recreates the visual language of the supplied BAMO mathematics reference: tall luminous geometry, orbiting colored particles, accumulating light trails, connected geometric webs, layered bloom, a restrained vignette, and a gradual climax. It is a separate engine; it does not replace the existing production renderer.

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

The workflow:
1. installs CPU-only dependencies;
2. runs unit tests;
3. renders the 32-second, four-stage mathematics reference project;
4. probes the resulting MP4 dimensions, frame rate, duration, and size;
5. uploads the MP4 artifact for visual review.

A green workflow proves the renderer can execute and produce a valid MP4 on GitHub Actions CPU. It does not prove that the prototype matches every artistic detail of the supplied reference, nor does it mean the 11-agent production pipeline has been switched to this engine. Production integration and approval remain separate steps.
