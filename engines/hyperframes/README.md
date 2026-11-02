# BAMO HyperFrames Neon Engine

This is the new candidate renderer for BAMO's neon mathematical / scientific motion graphics. It uses the upstream [HyperFrames](https://github.com/heygen-com/hyperframes) engine (Apache-2.0), with HTML/SVG, GSAP timelines, SVG filter bloom and FFmpeg output.

## Why this engine
- Deterministic frame seeking in headless Chromium (not screen recording).
- Native HTML/SVG and custom shader-capable content; supports GSAP, CSS, Lottie and Three.js.
- CLI rendering and audio mixing, suitable for GitHub Actions CPU runners.
- No paid API, hosted render credit or GPU is required. Rendering cost is CPU time.
- The example is an authored neon-geometry scene, not a static image slideshow.

## Local render
Requirements: Node.js 22+, FFmpeg. Chromium is managed by HyperFrames.

```bash
cd engines/hyperframes
npm install
npx hyperframes doctor
npx hyperframes lint ./index.html --json
npx hyperframes render -c ./index.html -o ./output/BAMO-neon-reference.mp4
```

## Production integration status
This branch introduces the engine as a separately testable candidate. It does **not** silently replace the existing Python pipeline yet. Promotion requires:
1. CI render succeeds and produces a non-trivial MP4.
2. Visual QA confirms the sample's orbit/chord/bloom progression at 9:16.
3. A second unrelated topic uses a different visual grammar (e.g. wave/interference or atom/molecule), not a recycled ellipse scene.
4. Persian narration and captions are attached to the same scene clock and duration.
5. Only after those checks should the pipeline select HyperFrames as its production renderer.

This keeps a failed experiment from breaking the current upload pipeline.
