# Free / Open-Source Stack (no paid API)

Goal: approach cinematic Shorts quality without paid keys. When YouTube revenue exists, optional paid APIs can be layered later.

## Already wired in this repo

| Layer | Tool | Cost | Notes |
|-------|------|------|-------|
| Script | Idea bank JSON | Free | Deterministic hooks + 4 scenes |
| TTS (default) | Microsoft Edge neural via `edge-tts` | Free | Online, no key |
| TTS (offline) | **Mana-Persian-Piper** (`app/piper_tts.py`) | Free | MIT-friendly Piper voice; CPU |
| Stock motion | **Mixkit** CDN fetch | Free | No API key |
| Stills fallback | Pollinations / abstract | Free | When stock missing |
| Captions | ASS yellow-box style | Free | Reference-style readability |
| Upload | YouTube Data API OAuth | Free quota | Daily quota limits apply |
| AI video (GPU) | **Wan2.1** in `colab/` | Free Colab GPU | Not on GitHub CPU runners |

## Recommended free upgrades (next)

### Voice (more natural Persian)
1. **Mana-Persian-Piper** — already integrated (`TTS_PROVIDER=piper`).
2. **Colab + pocket-tts / XTTS Persian** — better naturalness; needs free GPU session (not unlimited 24/7).
3. Keep Edge as automatic fallback if Piper model download fails.

### Video (closer to cinematic reference)
1. **Colab notebook** `colab/ImamAli110_Cinematic_Production.ipynb` + Wan engine — scene-matched AI clips.
2. Stronger prompt templates per scene (light, footstep, sacred hall) when Wan is on.
3. Mixkit remains the zero-GPU path.

### Music
- Mixkit / Pixabay music pages (license-check before public upload).
- Existing ambient bed in `spiritual_video.py` (ducked under voice).

## What will NOT match a paid AI demo on CPU-only Actions

- Full emotional acting TTS (studio narrator)
- Kling/Runway-level continuous cinematic AI video

Those need GPU time (Colab free tier) or later paid APIs.

## Principle

Same spirit as [stack-on-a-budget](https://github.com/255kb/stack-on-a-budget): prefer free tiers and open weights; never block the poor path.
