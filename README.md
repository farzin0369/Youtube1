# BAMO — Autonomous English YouTube Shorts Factory

**Brand:** BAMO · **Handle:** [@12bamo](https://www.youtube.com/@12bamo) · **Language:** English

This repository runs a **daily, fully automated** pipeline that:

1. Picks **one idea** from a multi-domain idea bank (science, physics, math, history, psychology, space, philosophy, art, success, humor, …)
2. Renders a vertical Short with **HyperFrames 0.9.19** using the **official `kinetic-type` template** (+ registry blocks such as `cosmic-orb`)
3. Publishes **publicly** to YouTube with title, description, tags, and hashtags
4. Replies to a small number of safe recent comments in English

## Sole production engine

```yaml
# config/engine.yaml
primary: hyperframes
version: "0.9.19"
template: kinetic-type
```

Deprecated (do not use for daily production):
OpenMontage, MoneyPrinterTurbo, Persian spiritual pipeline, Manim/Blender CPU demos, Wan/CogVideo experiments.

## Daily loop

| Step | Component |
|------|-----------|
| Idea selection | `scripts/bamo_brain.py` |
| Idea bank (up to 10k) | `data/ideas/ideas.jsonl` + `scripts/expand_idea_bank.py` |
| Render | `scripts/bamo_hyperframes_factory.py` |
| Orchestration | `scripts/bamo_daily_run.py` |
| Schedule | `.github/workflows/bamo_daily_english.yml` (17:00 UTC ≈ 12:00 ET) |
| Upload | `app/youtube_client.py` |
| Comments | `app/channel_ops.py` |

### Manual run

```bash
# expand / refresh idea bank
python scripts/expand_idea_bank.py --target 10000

# dry-run (select idea + metadata only)
python scripts/bamo_daily_run.py --dry-run

# full render + public upload (requires YouTube secrets)
python scripts/bamo_daily_run.py --publish --privacy public
```

### GitHub Actions

Workflow: **BAMO Daily English HyperFrames**

- Cron: every day 17:00 UTC
- `workflow_dispatch` with `publish` + `privacy` inputs

Required Secrets:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

See `scripts/README_TOKEN.md` for OAuth setup.

## Content rules

- English only
- Factual claims need reputable sources
- No medical / financial / legal advice
- No Persian spiritual / ImamAli branding
- Fail closed: no upload if render fails

## Channel config

`config/channel.yaml` — brand BAMO, education category, public daily cadence.
