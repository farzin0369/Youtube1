# Engine Switch Log — BAMO English Shorts

**Branch:** `feat/bamo-openmontage-autonomous-studio`  
**Brand:** BAMO · **Handle:** @12bamo

## Rejected / demoted engines

| Engine | Reason |
|--------|--------|
| OpenMontage | Agent-heavy; free path did not deliver real motion footage on this branch |
| MoneyPrinterTurbo | Stock-footage factory; user rejected as not good enough |
| FFmpeg text-on-color | Not professional motion graphics |

## Current primary engine: **HyperFrames**

| Field | Value |
|-------|--------|
| Repo | https://github.com/heygen-com/hyperframes |
| Stars | ~80k |
| License | **Apache 2.0** |
| Cost | Free (no per-render fee, no API required for core render) |
| What it is | HTML + CSS + GSAP / Lottie / Three.js → deterministic MP4 |
| Why better for you | Real **motion graphics**, not stock montage and not plain text cards |
| Needs GPU API? | No for rendering |
| Needs paid video model? | No |

HyperFrames is what OpenMontage itself uses as one of its composition engines. Using it directly gives professional motion without the AGPL agent stack or paid Kling/Veo paths.

## Honest limits

- You still need to **author or generate** the HTML composition (scenes, timing, assets).
- It does not invent cinematic AI video by itself; it **renders** motion graphics you define.
- For voice: pair with free Edge-TTS / Piper (no paid key).
- For images inside scenes: free local or free image sources, not required for pure motion/text/diagram styles.

## Integration on this branch

- Setup script: `scripts/setup_hyperframes.sh`
- Docs: `docs/HYPERFRAMES_SETUP.md`
- Vendor path: `vendor/hyperframes`

Next concrete step after clone: one vertical 9:16 English science Short composition with BAMO branding and Edge-TTS audio.
