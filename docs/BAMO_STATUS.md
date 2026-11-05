# BAMO status (honest)

## Proven on GitHub Actions (CPU, free)

- Three-domain procedural MP4 with quality patches: **success**
  - Run: https://github.com/farzin0369/Youtube1/actions/runs/41931613255
  - Artifact: https://github.com/farzin0369/Youtube1/actions/runs/41931613255/artifacts/13374799528
  - Profile: 24 samples, ~40% resolution, OIDN, edge-tts, ~12MB MP4, ~56 minutes
- 48 samples without sharding: **timeout** (~3675s on first scene)

## Continuous profile (locked)

`bamo_autopilot_continuous.yml` uses the proven 24-sample path + `BAMO_FORCE_PROCEDURAL=1` + `apply_quality_patches.py`. Publish remains off.

## Not complete

- Studio-grade motion quality (noise, materials, typography layer, camera language)
- Full 11-agent autonomy with live research/YouTube learning
- Frame sharding for higher samples
- Public YouTube upload (intentionally gated until brain+QA = 100)

## Factory entry

```bash
PYTHONPATH=. python scripts/bamo_factory_run.py --topic "..."
PYTHONPATH=. python scripts/bamo_factory_run.py --topic "..." --render  # slow
```
