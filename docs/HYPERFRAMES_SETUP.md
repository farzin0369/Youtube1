# HyperFrames — Primary Motion Engine for BAMO

**Official:** https://github.com/heygen-com/hyperframes  
**License:** Apache 2.0  
**Brand:** BAMO · @12bamo

## Install into this repo

```bash
bash scripts/setup_hyperframes.sh
```

Or:

```bash
git clone --depth 1 https://github.com/heygen-com/hyperframes.git vendor/hyperframes
cd vendor/hyperframes
npm install   # requires Node.js 22+
```

## What you get

- Write ordinary HTML/CSS (and GSAP/Lottie/Three if needed)
- Render deterministic vertical MP4 (1080×1920)
- No paid render API
- Agent-friendly skills included upstream

## BAMO workflow (target)

1. Idea bank → English script + scene list
2. Edge-TTS narration (free)
3. HyperFrames composition (motion + text + diagrams)
4. Mux audio + burn captions
5. QC → private upload

## Requirements

- Node.js 22+
- FFmpeg
- Optional: GPU only if you later add local generative assets
