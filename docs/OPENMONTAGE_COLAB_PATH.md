# OpenMontage on Colab GPU — BAMO English Shorts

**Primary production engine: OpenMontage**  
**Brand:** BAMO · **Handle:** @12bamo  
**Format:** English vertical 9:16 Shorts (20–30s)

## Status (updated)

| Component | Status |
|-----------|--------|
| OpenMontage submodule | Pinned |
| English channel config | Done |
| Idea bank + Content Intelligence | Started |
| Adapter (`scripts/bamo_openmontage_adapter.py`) | Ready |
| Autonomous runner v0 (`scripts/bamo_openmontage_runner.py`) | Ready |
| Colab notebook | Ready |
| Full OpenMontage stage-director execution | Pending |
| Professional cinematic OpenMontage render | Not yet |

## How to run on Colab GPU

1. Open `colab/BAMO_OpenMontage_English_Short.ipynb`
2. Runtime → GPU (T4+)
3. Run all cells
4. Download `output/bamo_om_runs/<id>/final_short.mp4`

## Local / CI path

```bash
python scripts/bamo_openmontage_runner.py
```

## Architecture

```
Idea Bank
  → Content Intelligence
  → Adapter (OpenMontage project brief)
  → Runner stages: TTS → compose → QC
  → final_short.mp4 (9:16 English)
```

## Deprecated as primary

- `scripts/colab_wan_real_short.py` (Wan path)
- Persian / ImamAli110 content pipelines on this branch

## Next hardening

1. Drive real OpenMontage stage skills (research, proposal, scene, asset, compose)
2. Prefer HyperFrames / Remotion / open stock over pure kinetic text
3. Piper English voice evaluation
4. Checkpoint resume + daily schedule after quality is proven
