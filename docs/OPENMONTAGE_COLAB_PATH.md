# OpenMontage on Colab GPU — BAMO English Shorts

**Primary production engine: OpenMontage**  
**Brand:** BAMO · **Handle:** @12bamo  
**Format:** English vertical 9:16 Shorts (20–30s)

## Why this document exists

Previous Colab GPU workflow used Wan 2.1 (`colab_wan_real_short.py`).  
That path is **deprecated as primary** on this experimental branch.  
OpenMontage is the single central production system going forward.

## Architecture (target)

```
Idea Bank (data/ideas/ideas.jsonl)
        ↓
Content Intelligence (app/content_intelligence.py)
        ↓
BAMO OpenMontage Adapter (scripts/bamo_openmontage_adapter.py)
        ↓
OpenMontage project + pipeline artifacts
        ↓
Colab GPU session (submodule init + tools + free/local providers)
        ↓
Vertical 1080×1920 MP4 + English narration + captions
        ↓
Quality gates → private/unlisted upload (when approved)
```

## What is ready now

| Component | Status |
|-----------|--------|
| OpenMontage submodule (`vendor/openmontage`) | Pinned |
| English channel config | Done |
| Idea bank + Content Intelligence skeleton | Started |
| Adapter script | This commit |
| Colab notebook for OpenMontage | This commit |
| Full autonomous OpenMontage runner (zero human gates) | In progress |
| Real professional OpenMontage render on Colab | Not yet proven |

## Colab usage (manual first)

1. Open the notebook: `colab/BAMO_OpenMontage_English_Short.ipynb`
2. Select GPU runtime (T4 or better)
3. Run cells in order:
   - Clone this branch
   - Init OpenMontage submodule
   - Install dependencies (CPU + GPU extras)
   - Load selected idea from idea bank
   - Run adapter → prepare project
   - Execute available free/local OpenMontage tools + FFmpeg compose
4. Download the resulting MP4

## Autonomous path (next)

A headless runner that:
- Selects idea
- Writes OpenMontage-compatible artifacts
- Forces autonomous checkpoint policy (no human approval for experimental runs)
- Prefers free tools (Piper, open stock, HyperFrames/Remotion local, FFmpeg)
- Fails closed if quality gates fail

## Important constraints

- OpenMontage is **agent-instruction driven**. Full cinematic quality in the official demos often uses paid generation providers.
- On free Colab we prioritize: local/open tools, Piper or edge-tts, FFmpeg, stock/open footage, HyperFrames/Remotion where installable.
- Do not claim a video is “OpenMontage full production” until the pipeline artifacts and stage skills have actually been executed and a real MP4 inspected.

## Deprecated for primary production on this branch

- `scripts/colab_wan_real_short.py` (Wan 2.1 Persian path)
- Any ImamAli110 / Persian spiritual content path

These files may remain for reference until migration is complete; they are not the production path.
