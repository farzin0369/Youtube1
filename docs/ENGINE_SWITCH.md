# Engine Switch — MoneyPrinterTurbo as Primary Free Shorts Engine

**Date:** 2026-11-07  
**Branch:** `feat/bamo-openmontage-autonomous-studio`  
**Brand:** BAMO · **Handle:** @12bamo

## Decision

OpenMontage remains in the repo as a research / agent-orchestration reference, but it is **no longer the primary production engine** for daily English Shorts.

### Why the switch

| Requirement | OpenMontage | MoneyPrinterTurbo |
|-------------|-------------|-------------------|
| Real motion footage (not text-on-color) | Needs paid gen or complex agent loop | Built-in stock footage matching |
| English Shorts pipeline | Agent-driven, heavy setup | Purpose-built short video factory |
| Free / low-key path | Possible but hard | Edge-TTS free + free Pexels tier |
| Practical daily output | Not proven on this branch | Designed for one-click HD shorts |
| License | AGPL-3.0 | MIT |

**Chosen primary engine:** [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) (MIT, ~140k stars)

## What MoneyPrinterTurbo provides

- Topic → script → stock footage → voice → subtitles → HD short
- Vertical 9:16 support
- Edge-TTS (no paid voice key required)
- WebUI + API + CLI
- Colab notebook available upstream

## Honest limits

- Free Pexels API key is usually needed for stock video (free tier).
- LLM for script generation can use free tiers (Groq, etc.) or local Ollama.
- Quality depends on stock match quality — not Kling/Veo-level generative motion.
- This is still **not** fully zero-key in all paths, but far more practical than OpenMontage for faceless English Shorts.

## Integration plan on this branch

1. Add MoneyPrinterTurbo as `vendor/moneyprinterturbo` (submodule or vendored clone).
2. Wire BAMO idea bank + English channel config into it.
3. Produce a real sample with footage + English narration + captions.
4. Keep OpenMontage submodule only as optional advanced path.

## Status

- Decision documented: YES
- Submodule/clone: in progress
- First real footage sample: pending after vendor land
