# Primary Engine: HyperFrames

**Brand:** BAMO · **Handle:** @12bamo  
**Branch:** `feat/bamo-openmontage-autonomous-studio`

## Decision

| Role | Engine |
|------|--------|
| **Primary production** | **HyperFrames** (https://github.com/heygen-com/hyperframes) |
| Optional research | OpenMontage (submodule only) |
| Rejected for daily path | MoneyPrinterTurbo, plain FFmpeg text cards as final |

HyperFrames is Apache-2.0, free to render locally, no paid video API required for motion graphics.

## Project in this repo

```
productions/bamo-time-dilation/
  index.html          # 9:16 GSAP composition (Time Dilation Short)
  assets/narration.*  # English Edge-TTS voice
  package.json        # npm run render / preview / check
  hyperframes.json
```

## Render (on your machine or Colab with Node 22+)

```bash
cd productions/bamo-time-dilation
npm install   # or use npx
npx hyperframes preview
npx hyperframes render -o ../../outputs/BAMO_TimeDilation.mp4
```

Requirements: Node.js ≥ 22, FFmpeg, Chromium (pulled by HyperFrames).

## Why this is the main path

- Real motion graphics (GSAP timelines, seekable frames)
- Vertical 1080×1920 Shorts-ready
- Deterministic MP4 output
- Works with AI agents via HyperFrames skills
- No Kling/Veo API required for this style of educational Short
