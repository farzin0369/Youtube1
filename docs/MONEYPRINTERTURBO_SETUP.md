# MoneyPrinterTurbo — Primary Free Shorts Engine for BAMO

**Official repo:** https://github.com/harry0703/MoneyPrinterTurbo  
**License:** MIT  
**Stars:** ~140k  
**Brand on this branch:** BAMO · @12bamo

## Why this engine

You asked for something:
- better than OpenMontage for practical Shorts output
- free
- no paid API required for core path
- fully clonable into our repo

MoneyPrinterTurbo is purpose-built for faceless short videos:
- topic → script → **real stock footage** → voice → subtitles → HD MP4
- vertical 9:16
- Edge-TTS (free, no key)
- free Pexels tier for footage
- free LLM tiers (Groq etc.) or local Ollama

This is **not** generative AI cinema (Kling/Veo). It is stock-footage + narration + captions automation — which is what actually produces watchable Shorts without paid video models.

## Install into this repo

```bash
bash scripts/setup_moneyprinterturbo.sh
# or
git submodule update --init vendor/moneyprinterturbo
```

## Minimal config (free path)

1. Get a free Pexels API key: https://www.pexels.com/api/
2. Optional: free Groq key for better scripts, or use Ollama locally
3. Copy `vendor/moneyprinterturbo/config.example.toml` → `config.toml`
4. Set English voice (edge-tts), vertical resolution, BAMO branding in post

## Relation to OpenMontage

| Engine | Role on this branch |
|--------|---------------------|
| **MoneyPrinterTurbo** | Primary daily Shorts production |
| OpenMontage | Optional advanced / agent research path only |

OpenMontage submodule stays for experimentation. Daily production should not depend on it.

## Next steps

1. Run setup script
2. Configure free keys
3. Generate one English Short with real footage
4. Wire idea bank → MoneyPrinterTurbo topic input
5. Add brand lock BAMO / @12bamo in final assemble
